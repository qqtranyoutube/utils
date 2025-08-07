from googleapiclient.discovery import build
from datetime import datetime
import pandas as pd
import streamlit as st

def search_meditation_videos_today():
    api_key = st.secrets["youtube_api_key"]
    youtube = build("youtube", "v3", developerKey=api_key)

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    published_after = today.isoformat("T") + "Z"

    videos = []
    next_page_token = None
    max_pages = 10  # tối đa 500 video (50 x 10)

    for _ in range(max_pages):
        search_response = youtube.search().list(
            q="meditation",
            part="snippet",
            type="video",
            maxResults=50,
            order="viewCount",
            publishedAfter=published_after,
            relevanceLanguage="en",
            pageToken=next_page_token
        ).execute()

        for item in search_response.get("items", []):
            video_id = item["id"].get("videoId")
            snippet = item["snippet"]
            channel_id = snippet.get("channelId")

            # Lấy thông tin video
            video_response = youtube.videos().list(
                part="statistics,liveStreamingDetails,contentDetails",
                id=video_id
            ).execute()
            video_data = video_response.get("items", [{}])[0]

            stats = video_data.get("statistics", {})
            view_count = int(stats.get("viewCount", 0))

            # Lấy thông tin kênh
            channel_response = youtube.channels().list(
                part="snippet",
                id=channel_id
            ).execute()
            country = channel_response.get("items", [{}])[0].get("snippet", {}).get("country", "Unknown")

            videos.append({
                "videoId": video_id,
                "title": snippet.get("title", ""),
                "channelTitle": snippet.get("channelTitle", ""),
                "publishedAt": snippet.get("publishedAt", ""),
                "liveBroadcastContent": snippet.get("liveBroadcastContent", "none"),
                "viewCount": view_count,
                "channelId": channel_id,
                "country": country
            })

        next_page_token = search_response.get("nextPageToken")
        if not next_page_token:
            break

    return pd.DataFrame(videos)
