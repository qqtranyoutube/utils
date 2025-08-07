import os
import pandas as pd
from datetime import datetime, timedelta
from googleapiclient.discovery import build
import streamlit as st

def search_meditation_videos_today():
    api_key = st.secrets["youtube_api_key"]
    youtube = build("youtube", "v3", developerKey=api_key)

    # Lấy thời điểm đầu ngày hôm nay (UTC)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    published_after = today.isoformat("T") + "Z"

    # Tìm kiếm video chủ đề "meditation"
    search_response = youtube.search().list(
        q="meditation",
        part="snippet",
        type="video",
        maxResults=100,
        order="date",
        publishedAfter=published_after
    ).execute()

    videos = []
    for item in search_response.get("items", []):
        snippet = item["snippet"]
        video_id = item["id"]["videoId"]
        channel_id = snippet["channelId"]

        # Lấy thông tin video
        video_response = youtube.videos().list(
            part="statistics,liveStreamingDetails",
            id=video_id
        ).execute()

        video_stats = video_response.get("items", [{}])[0].get("statistics", {})
        live_details = video_response.get("items", [{}])[0].get("liveStreamingDetails", {})
        view_count = int(video_stats.get("viewCount", 0))
        live_status = snippet.get("liveBroadcastContent", "none")

        # Lấy thông tin kênh để lấy quốc gia
        channel_response = youtube.channels().list(
            part="snippet",
            id=channel_id
        ).execute()

        country = channel_response.get("items", [{}])[0].get("snippet", {}).get("country", "Unknown")

        videos.append({
            "videoId": video_id,
            "title": snippet.get("title"),
            "channelTitle": snippet.get("channelTitle"),
            "channelId": channel_id,
            "publishedAt": snippet.get("publishedAt"),
            "viewCount": view_count,
            "liveBroadcastContent": live_status,
            "country": country
        })

    return pd.DataFrame(videos)
