import requests
from dagster import asset


@asset
def top_story_ids():
    newstories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    return requests.get(newstories_url).json()[:100]
