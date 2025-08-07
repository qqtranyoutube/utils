# utils/youtube_api.py

import requests
import streamlit as st
from datetime import datetime, timedelta

def search_meditation_videos_today():
    api_key = st.secrets["youtube_api_key"]
    now = datetime.utcnow()
    published_after = (now - timedelta(days=1)).isoformat("T") + "Z"

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": "meditation",
        "type": "video",
        "order": "date",
        "publishedAfter": published_after,
        "maxResults": 20,
        "key": api_key
    }

    res = requests.get(url, params=params).json()

    video_data = []
    for item in res.get("items", []):
        video = {
            "videoId": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channelTitle": item["snippet"]["channelTitle"],
            "publishedAt": item["snippet"]["publishedAt"],
            "liveBroadcastContent": item["snippet"]["liveBroadcastContent"],
            "viewCount": 0  # sẽ cập nhật sau
        }
        video_data.append(video)

    return video_data
