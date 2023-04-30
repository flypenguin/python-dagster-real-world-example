import pandas as pd
import requests
from dagster import asset, get_dagster_logger, Output, MetadataValue


@asset
def top_story_ids():
    newstories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    return requests.get(newstories_url).json()[:100]


@asset
def top_stories(top_story_ids):
    logger = get_dagster_logger()
    results = []
    for item_id in top_story_ids:
        url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        item = requests.get(url).json()
        results.append(item)
    df = pd.DataFrame(results)
    logger.info(f"got {len(results)} top stories")
    return Output(
        value=df,
        metadata={
            "num_records": len(results),
            "preview": MetadataValue.md(df.head().to_markdown()),
        },
    )
