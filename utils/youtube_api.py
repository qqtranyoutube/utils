from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import os
import datetime
import pandas as pd

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

def search_meditation_videos_today():
    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)

        today = datetime.datetime.utcnow().date()
        published_after = today.isoformat() + "T00:00:00Z"

        search_response = (
            youtube.search()
            .list(
                q="meditation",
                part="id,snippet",
                type="video",
                order="date",
                publishedAfter=published_after,
                maxResults=50,
            )
            .execute()
        )

        videos = []
        for item in search_response.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel_id = item["snippet"]["channelId"]
            channel_title = item["snippet"]["channelTitle"]

            # Get video statistics
            video_response = (
                youtube.videos()
                .list(part="statistics", id=video_id)
                .execute()
            )

            statistics = video_response["items"][0]["statistics"]
            view_count = int(statistics.get("viewCount", 0))

            videos.append({
                "video_id": video_id,
                "title": title,
                "channel_id": channel_id,
                "channel_title": channel_title,
                "view_count": view_count
            })

        return pd.DataFrame(videos)

    except HttpError as e:
        print(f"HTTP error occurred: {e}")
        return pd.DataFrame([])

    except Exception as e:
        print(f"Other error occurred: {e}")
        return pd.DataFrame([])
