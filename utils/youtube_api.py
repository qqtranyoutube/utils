import os
import datetime
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def search_meditation_videos_today():
    today = datetime.datetime.utcnow().date().isoformat() + "T00:00:00Z"
    search_response = youtube.search().list(
        q="meditation",
        part="snippet",
        maxResults=50,
        order="date",
        publishedAfter=today,
        type="video"
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_response["items"]]

    if not video_ids:
        return []

    videos_response = youtube.videos().list(
        part="snippet,statistics,liveStreamingDetails",
        id=','.join(video_ids)
    ).execute()

    videos_data = []
    for item in videos_response["items"]:
        snippet = item["snippet"]
        statistics = item.get("statistics", {})
        live_details = item.get("liveStreamingDetails", {})

        video_data = {
            "videoId": item["id"],
            "title": snippet.get("title"),
            "channelTitle": snippet.get("channelTitle"),
            "publishedAt": snippet.get("publishedAt"),
            "viewCount": int(statistics.get("viewCount", 0)),
            "likeCount": int(statistics.get("likeCount", 0)),
            "commentCount": int(statistics.get("commentCount", 0)),
            "liveBroadcastContent": snippet.get("liveBroadcastContent", "none"),
            "actualStartTime": live_details.get("actualStartTime")
        }
        videos_data.append(video_data)

    return videos_data
