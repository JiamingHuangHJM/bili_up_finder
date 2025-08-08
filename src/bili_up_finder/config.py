import logging

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from rich.logging import RichHandler


class Config(BaseModel):
    """
    Configuration class for the application.
    This class is used to load and validate configuration settings.
    """

    verbose: bool = Field(default=True, description="Enable verbose output")

    video_go_through_per_page: int = Field(
        default=30,
        le=30,  # less than or equal to 30
        ge=1,  # greater than or equal to 1
        description="Number of videos to go through per page (max 30)",
    )

    num_up: int = Field(default=3, ge=1, description="Maximum upload limit")

    default_videos_per_page: int = Field(
        default=30, description="Always set to 30 videos per page"
    )

    min_acceptable_videos: int = Field(
        default=10,
        ge=10,  # greater than or equal to 10
        description="Minimum acceptable videos (must be >= 10)",
    )

    @field_validator("default_videos_per_page", mode="after")
    @classmethod
    def validate_max_videos_per_page(cls, v):
        """Ensure default_videos_per_page is always 30"""
        if v != 30:
            raise ValueError("default_videos_per_page must always be 30")
        return v


# Global instance
config = Config()


def init_config(**kwargs):
    global config
    config = Config(**kwargs)

    load_dotenv()

    console_handler = RichHandler()
    file_handler = logging.FileHandler("logs/app.log")

    logging.basicConfig(
        level=logging.DEBUG if config.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[console_handler, file_handler],
    )
