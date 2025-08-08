import logging

from assistant import DeepSeekAssistant

from bili_up_finder.config import config
from search_helper.system_prompt.reader import get_system_prompts

logger = logging.getLogger(__name__)


def expand_search_query(search_query: str) -> str:
    instructions = get_system_prompts("expand_search_query")

    if config.verbose:
        reason = " 在yes或no之后, 告诉我你为什么这么认为。"
        instructions += f" {reason}"

    client = DeepSeekAssistant(instructions=instructions, verbose=config.verbose)
    response = client.ask(search_query)

    logger.debug(
        f"扩展关键词结果: {response}",
    )

    return response


def decide_target_video_relevant(
    title: str, tags: list[str], search_query: str
) -> bool:
    instructions = get_system_prompts("decide_target_video_relevant")

    client = DeepSeekAssistant(instructions=instructions, verbose=config.verbose)
    response = client.ask(
        f"视频标题是: {title}. 附加的标签: {', '.join(tags)}. 搜索查询是: {search_query}."
    )

    logger.info(
        f"DeepSeek response: {response}",
    )

    if "yes" in response.lower():
        return True
    elif "no" in response.lower():
        return False
    else:
        if config.verbose is False:
            raise ValueError(
                "The response from AI Assistant is neither 'yes' nor 'no'."
            )


def decide_user_space_video_relevant(
    video_captions: list[str], search_query: str
) -> bool:
    instructions = get_system_prompts("decide_user_space_video_relevant")

    client = DeepSeekAssistant(instructions=instructions, verbose=config.verbose)
    response = client.ask(
        f"视频标题列表: {', '.join(video_captions)}. 搜索关键词是: {search_query}."
    )

    logger.debug(f"video_captions: {video_captions}")

    logger.info(f"decide_user_space_video_relevant, DeepSeek response: {response}")

    if "yes" in response.lower():
        return True
    elif "no" in response.lower():
        return False
    else:
        raise ValueError("The response from AI Assistant is neither 'yes' nor 'no'.")
