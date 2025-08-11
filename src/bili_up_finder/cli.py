import asyncio

import click

from bili_up_finder.config import init_config
from bili_up_finder.up_finder import main


@click.command()
@click.option(
    "-q", "--query", required=True, type=str, help="Search query for finding UPs."
)
@click.option("-n", "--num-up", default=10, type=int, help="number of UPs to collect.")
@click.option(
    "-v", "--verbose", default=False, type=bool, help="Enable or disable debug prints."
)
@click.option(
    "--video-go-through-per-page",
    default=30,
    type=int,
    help="Number of videos to go through in each search result.",
)
@click.option(
    "--default-videos-per-page",
    default=30,
    type=int,
    help="Maximum number of videos per page to click on.",
)
@click.option(
    "--min-acceptable-videos",
    default=10,
    type=int,
    help="Minimum acceptable number of videos for an UP.",
)
def cli(
    query,
    num_up,
    verbose,
    video_go_through_per_page,
    default_videos_per_page,
    min_acceptable_videos,
):
    config = init_config(
        num_up=num_up,
        video_go_through_per_page=video_go_through_per_page,
        default_videos_per_page=default_videos_per_page,
        min_acceptable_videos=min_acceptable_videos,
        verbose=verbose,
    )
    # Run the main function with the provided search query
    asyncio.run(main(query, config=config))
