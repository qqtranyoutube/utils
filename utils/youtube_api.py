import os
import datetime
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=API_KEY)

SEARCH_QUERY = "meditation"
MAX_RESULTS = 50


def search_meditation_videos_today():
    today = datetime.datetime.utcnow().date()
    published_after = f"{today}T00:00:00Z"
    published_before = f"{today}T23:59:59Z"

    videos = []
    next_page_token = None

    while True:
        try:
            request = youtube.search().list(
                q=SEARCH_QUERY,
                part="id,snippet",
                type="video",
                order="date",
                maxResults=MAX_RESULTS,
                publishedAfter=published_after,
                publishedBefore=published_before,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]
                videos.append({
                    "video_id": video_id,
                    "title": snippet["title"],
                    "channel_title": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"]
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

            time.sleep(1)  # tránh vượt quota

        except HttpError as e:
            print(f"❌ Lỗi khi gọi YouTube API: {e}")
            break

    return pd.DataFrame(videos)


def get_video_statistics(video_ids):
    stats = []
    for i in range(0, len(video_ids), 50):
        try:
            response = youtube.videos().list(
                part="statistics,snippet",
                id=",".join(video_ids[i:i + 50])
            ).execute()

            for item in response.get("items", []):
                vid = item["id"]
                stats_item = item["statistics"]
                snippet = item["snippet"]

                stats.append({
                    "video_id": vid,
                    "title": snippet.get("title", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "view_count": int(stats_item.get("viewCount", 0)),
                    "like_count": int(stats_item.get("likeCount", 0)),
                    "comment_count": int(stats_item.get("commentCount", 0))
                })

            time.sleep(1)

        except HttpError as e:
            print(f"❌ Lỗi khi lấy thống kê video: {e}")
            continue

    return pd.DataFrame(stats)


def estimate_rpm(views):
    # Giả định mức RPM trung bình: $0.5 → $5 tùy thị trường
    if views < 1000:
        return 0
    elif views < 5000:
        return round(views * 0.5 / 1000, 2)
    elif views < 10000:
        return round(views * 1.5 / 1000, 2)
    else:
        return round(views * 3.5 / 1000, 2)


def enrich_with_rpm(df):
    df["estimated_rpm"] = df["view_count"].apply(estimate_rpm)
    df["monetizable"] = df["view_count"].apply(lambda x: x >= 1000)
    return df
