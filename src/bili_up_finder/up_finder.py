import logging
import os

from playwright.async_api import TimeoutError as PWTimeout
from playwright.async_api import async_playwright

from bili_up_finder.config import Config
from bili_up_finder.search_helper.ai_search_helper import (
    decide_target_video_relevant,
    decide_user_space_video_relevant,
    expand_search_query,
)
from bili_up_finder.web_builder import run_web_builder

for noisy_logger in ["openai", "httpcore", "httpx", "urllib3", "playwright"]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


START_URL = "https://www.bilibili.com"
users_data: list[dict] = []  # 收集所有满足条件的 up 主信息
processed_up_names = set()  # 用于去重, 跳过已处理过 up 主
uploaders = set()


async def obtain_all_video_captions_in_profile(profile_page, scroll=True) -> list[str]:
    await profile_page.wait_for_selector("div.bili-video-card__title a")

    if scroll:  # auto-scroll to load more cards
        prev_height = -1
        while True:
            curr_height = await profile_page.evaluate(
                "document.documentElement.scrollHeight"
            )
            if curr_height == prev_height:  # reached the bottom
                break
            prev_height = curr_height
            # 滑动到底部
            await profile_page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
            await profile_page.wait_for_timeout(800)  # small pause for network / render

    # ③ grab *all* <a> text inside the title divs (one round-trip)
    all_captions_in_user_space = await profile_page.eval_on_selector_all(
        "div.bili-video-card__title a", "els => els.map(e => e.textContent.trim())"
    )

    return all_captions_in_user_space


async def click_most_viewed(page):
    """点击『最多播放』并返回真正存在的卡片 selector"""
    btn = page.locator("div.radio-filter__item:has-text('最多播放')")
    await btn.click(force=True)  # force 避免被遮挡时报错

    # 等待新的卡片 anchor 挂到 DOM；多套 selector 兜底
    selectors = [
        "div.upload-video-card_main a[href*='/video/']",
        "div.upload-video-card__main a[href*='/video/']",
        "a[href*='/video/'][target='_blank']",
    ]
    for sel in selectors:
        try:
            await page.wait_for_selector(sel, state="attached", timeout=10_000)
            return sel
        except PWTimeout:
            continue
    raise RuntimeError("⚠️  点了『最多播放』后 10 s 仍未出现视频卡片")


async def collect_top_videos(profile_page, anchor_selector, limit=10):
    """
    anchor_selector 由 click_most_viewed() 动态返回，
    保证跟实际 DOM 匹配。
    """
    anchors = profile_page.locator(anchor_selector)

    # 若首屏不足 N 条，就滚动触发懒加载
    while await anchors.count() < limit:
        await profile_page.evaluate("window.scrollBy(0, window.innerHeight)")
        await profile_page.wait_for_timeout(600)
        if await anchors.count() >= limit or await profile_page.evaluate(
            "window.scrollY + window.innerHeight >= document.body.scrollHeight - 2"
        ):
            break  # 已经到底，或够量

    videos, seen = [], set()
    for i in range(await anchors.count()):
        a = anchors.nth(i)
        href = (await a.get_attribute("href")) or ""
        href = "https:" + href if href.startswith("//") else href
        if href in seen:
            continue
        seen.add(href)

        # 卡片根节点（向上找最近的 upload-video-card）
        card = a.locator("xpath=ancestor::*[contains(@class,'upload-video-card')]")

        # 标题：先找 title 链接，退而求其次找 title 属性
        try:
            title = (
                await card.locator("div.bili-video-card__title a").inner_text()
            ).strip()
        except PWTimeout:
            title = (await a.get_attribute("title") or "").strip()

        # 缩略图
        thumb_raw = await card.locator("img").first.get_attribute("src")
        thumb = "https:" + thumb_raw if thumb_raw.startswith("//") else thumb_raw

        videos.append({"title": title, "href": href, "thumb": thumb})
        if len(videos) >= limit:
            break

    return videos


async def go_to_user_space(video_page, search_query: str, config: Config) -> None:
    """
    users_data 是一个全局变量，收集所有满足条件的 UP 主信息。
    每个 UP 主信息是一个字典，包含以下键：
    - "uploader": UP 主名称
    - "profile": UP 主个人空间链接
    - "videos": UP 主视频列表，每个视频是一个字典，包含以下键：
        - "title": 视频标题
        - "href": 视频链接
        - "thumb": 视频缩略图链接
    """

    panel = video_page.locator(".up-panel-container")
    await panel.wait_for(state="attached")

    # ② ── 找到“带文字”的名字链接 ──────────────────────────────
    name_link = panel.locator("a.staff-name, a.up-name").first  # 两种 class 二选一
    await name_link.wait_for(state="visible")  # 等它真的渲染文字

    has_name = await name_link.count() > 0  # 理论上一定 >0

    # ③ ── 拿昵称,个人空间完整 URL ────────────────────────────
    if has_name:
        up_link = name_link  # 就用它来点击
        uploader = (await up_link.inner_text()).strip()
    else:
        # 极端情况：仍然没有文字（几乎不会发生），退回头像 <a>
        up_link = panel.locator("a[href*='space.bilibili.com']").first
        uploader = (
            await up_link.get_attribute("title")  # title
            or await up_link.locator("img").first.get_attribute("alt")  # img.alt
            or ""
        )

    # element.href → 绝对 URL
    profile_url: str = await up_link.evaluate("el => el.href")

    # ④ ── 点击并等待新标签页 ───────────────────────────────────
    async with video_page.expect_popup() as pop:
        await up_link.click()

    profile_page = await pop.value
    await profile_page.wait_for_load_state("networkidle")

    # 检测账号是否已经注销
    error_code_element = await profile_page.query_selector('[class*="code"]')
    if error_code_element:
        error_text = await error_code_element.inner_text()
        if "404" in error_text:
            await profile_page.close()
            return

    # 进入「投稿」标签
    await profile_page.locator("a.nav-tab__item:has-text('投稿')").click()
    all_captions = await obtain_all_video_captions_in_profile(profile_page)

    await profile_page.wait_for_selector(
        "div.bili-video-card__wrap .bili-video-card__title"
    )

    video_links_profile_page = profile_page.locator(
        "div.bili-video-card__wrap .bili-video-card__title"
    )

    num_videos = await video_links_profile_page.count()

    if num_videos <= config.min_acceptable_videos:
        logger.info(
            f"UP主 {uploader} 的视频数量 {num_videos} 小于最小可接受数量 {config.min_acceptable_videos}，跳过。"
        )
        await profile_page.close()

        return

    if decide_user_space_video_relevant(all_captions, search_query, config.verbose):
        anchor_sel = await click_most_viewed(profile_page)
        videos = await collect_top_videos(profile_page, anchor_sel)
        logger.info(f"UP主 {uploader} 符合搜索结果...")

        # ⭐️⭐️ 只追加到 users_data，不立刻生成文件
        if uploader not in uploaders:
            uploaders.add(uploader)
            users_data.append(
                {
                    "uploader": uploader,
                    "profile": profile_url,
                    "videos": videos,
                }
            )

    await profile_page.close()


async def open_all_search_videos(
    page, context, search_query: str, config: Config
) -> None:
    """Open each search-result video in a new tab, do something, then close it."""
    # Because every search-result “card” is made of two separately-clickable zones—the thumbnail
    # and the text block—Bilibili drops an <a> tag on each of them, both pointing to the same BV-URL.
    # Pick only the anchor that sits directly inside the wrapper

    # 等待视频列表加载
    await page.wait_for_selector(
        "div.bili-video-card__wrap .bili-video-card__info--right > a[href*='/video/']"
    )

    video_links = page.locator(
        "div.bili-video-card__wrap .bili-video-card__info--right > a[href*='/video/']"
    )

    total = await video_links.count()

    logger.debug(
        f"🎬  发现一共 {total} 视频链接, 页面显示{config.default_videos_per_page}个视频"
    )

    spans_up_names = page.locator("span.bili-video-card__info--author")

    for i in range(
        min(config.video_go_through_per_page, total, config.default_videos_per_page)
    ):
        if len(users_data) >= config.num_up:
            return

        up_name = await spans_up_names.nth(i).text_content()
        if up_name:
            up_name = up_name.strip()

        logger.debug(
            f"▶️  视频 {i + 1}/{config.default_videos_per_page}, 收集 {len(uploaders)}"
        )

        if up_name in processed_up_names:
            logger.debug(f"跳过已处理过的 UP 主: {up_name}")
            continue

        processed_up_names.add(up_name)

        async with context.expect_page() as popup_info:
            await video_links.nth(i).click()

        video_page = await popup_info.value
        await video_page.wait_for_load_state("networkidle")

        logger.debug(f"URL: {video_page.url}")
        title = await video_page.title()
        logger.debug(f"标题:, {title.split('_哔哩哔哩')[0]}")

        tags = await video_page.eval_on_selector_all(
            "div.ordinary-tag a.tag-link", "els => els.map(el => el.textContent.trim())"
        )

        logger.debug(
            f"标签: {tags}",
        )

        is_relevant_search_query = decide_target_video_relevant(
            title, tags, search_query, config.verbose
        )

        if is_relevant_search_query:
            await go_to_user_space(video_page, search_query, config)

        await video_page.close()
        logger.debug("关闭视频页面")

    logger.info("✅  所有视频处理完毕 ... ")


async def main(search_query: str, config: Config):
    logger.info(f"开始搜索: {search_query}, 搜索up主数量上限: {config.num_up}")

    os.makedirs("playwright/.auth", exist_ok=True)
    # If file doesn't exist, create it with empty JSON
    if not os.path.exists("playwright/.auth/state.json"):
        file_path = "playwright/.auth/state.json"
        with open(file_path, "w") as f:
            f.write("{}")
        f.close()

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="playwright/.auth/state.json")

        # Create a new page
        page = await context.new_page()

        # Check if the user is logged in
        await page.goto(
            f"https://search.bilibili.com/all?keyword={search_query}",
            wait_until="networkidle",
        )

        expanded_search_query = expand_search_query(
            search_query=search_query, verbose=config.verbose
        )

        while True:
            await page.locator("span.vui_tabs--nav-text", has_text="视频").click()
            await open_all_search_videos(page, context, expanded_search_query, config)
            if len(users_data) >= config.num_up:
                logger.info(
                    f"已找到 {len(users_data)} 个 UP 主，达到上限 {config.num_up}，停止搜索。"
                )
                break
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_selector("text=下一页")
                await page.click("text=下一页")

            except PWTimeout:
                logger.info("没有更多页面了，停止搜索。")
                break

        if users_data:  # 至少命中 1 个
            run_web_builder(users_data, search_query)
        else:
            logger.info("没有找到符合条件的 UP 主")

        await browser.close()
