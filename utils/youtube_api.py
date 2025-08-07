# utils/youtube_api.py

import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pandas as pd

def search_meditation_videos_today():
    api_key = st.secrets["youtube_api_key"]
    youtube = build("youtube", "v3", developerKey=api_key)

    published_after = (datetime.utcnow() - timedelta(days=1)).isoformat("T") + "Z"

    search_response = youtube.search().list(
        q="meditation",
        type="video",
        part="id,snippet",
        order="date",
        publishedAfter=published_after,
        maxResults=50
    ).execute()

    videos = []
    for item in search_response.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        # Gọi tiếp API để lấy thống kê video
        video_response = youtube.videos().list(
            part="statistics,liveStreamingDetails",
            id=video_id
        ).execute()

        stats = video_response.get("items", [{}])[0].get("statistics", {})
        live = video_response.get("items", [{}])[0].get("snippet", {}).get("liveBroadcastContent", "none")

        videos.append({
            "videoId": video_id,
            "title": snippet.get("title"),
            "channelTitle": snippet.get("channelTitle"),
            "publishedAt": snippet.get("publishedAt"),
            "viewCount": int(stats.get("viewCount", 0)),
            "liveBroadcastContent": live,
        })

    return pd.DataFrame(videos)
# Sau khi lấy channelId từ snippet
channel_id = snippet.get("channelId")

# Lấy quốc gia kênh
channel_info = youtube.channels().list(
    part="snippet",
    id=channel_id
).execute()

country = channel_info["items"][0]["snippet"].get("country", "Unknown")
