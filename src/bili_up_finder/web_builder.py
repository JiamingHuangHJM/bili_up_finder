import logging
import os
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

current_dir = os.path.dirname(os.path.abspath(__file__))
samples_dir = os.path.join(current_dir, "reports")

logger = logging.getLogger(__name__)


def run_web_builder(user_data: list[dict], search_query: str) -> None:
    env = Environment(
        loader=FileSystemLoader("./reports"),  # 模板目录
        autoescape=select_autoescape(["html"]),  # 防 XSS
    )

    tpl = env.get_template("index.j2")
    html = tpl.render(user_data=user_data)
    file_name = (
        f"reports/{search_query}_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.html"
    )
    Path(file_name).write_text(html, encoding="utf-8")

    logger.info(f"Up主报告生成成功, 保存在{file_name}")
