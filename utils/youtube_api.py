import os
import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime
from urllib.parse import parse_qs, urlparse

def set_api_key(api_key: str):
    st.session_state["YOUTUBE_API_KEY"] = api_key

def get_api_key():
    return st.session_state.get("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY")

def build_youtube_client():
    api_key = get_api_key()
    if not api_key:
        st.error("❌ Chưa có YouTube API Key.")
        return None
    return build("youtube", "v3", developerKey=api_key)

def search_meditation_videos_today():
    youtube = build_youtube_client()
    if youtube is None:
        return None

    today = datetime.utcnow()
    published_after = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat("T") + "Z"

    request = youtube.search().list(
        part="snippet",
        q="meditation",
        type="video",
        order="date",
        publishedAfter=published_after,
        maxResults=50
    )
    response = request.execute()

    videos = []
    video_ids = []

    for item in response.get("items", []):
        vid = item["id"]["videoId"]
        video_ids.append(vid)
        videos.append({
            "Video ID": vid,
            "Title": item["snippet"]["title"],
            "Channel": item["snippet"]["channelTitle"],
            "Published At": item["snippet"]["publishedAt"],
            "Thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
            "Video URL": f"https://www.youtube.com/watch?v={vid}"
        })

    # Lấy stats chi tiết
    if video_ids:
        stats_df = get_videos_stats(youtube, video_ids)
        df = pd.DataFrame(videos).merge(stats_df, on="Video ID", how="left")
        return df
    return None

def get_videos_stats(youtube, video_ids):
    stats_list = []
    for i in range(0, len(video_ids), 50):
        request = youtube.videos().list(
            part="statistics,snippet,liveStreamingDetails",
            id=",".join(video_ids[i:i+50])
        )
        response = request.execute()
        for item in response.get("items", []):
            stats = item.get("statistics", {})
            live_info = item.get("liveStreamingDetails", {})
            stats_list.append({
                "Video ID": item["id"],
                "Views": int(stats.get("viewCount", 0)),
                "Likes": int(stats.get("likeCount", 0)),
                "Comments": int(stats.get("commentCount", 0)),
                "Is Livestream": "liveStreamingDetails" in item,
                "Country": item["snippet"].get("defaultAudioLanguage", "N/A"),
                "Subs": None  # API không trả trực tiếp subs của video, phải gọi channel API
            })
    return pd.DataFrame(stats_list)

def get_stats_summary(df):
    fastest_1k_title = None
    if not df[df["Views"] >= 1000].empty:
        fastest_1k_title = df[df["Views"] >= 1000].sort_values("Published At").iloc[0]["Title"]

    return {
        "total_videos": len(df),
        "total_channels": df["Channel"].nunique(),
        "fastest_1k_title": fastest_1k_title or "Chưa có video đạt 1K views",
        "total_livestreams": df[df["Is Livestream"] == True].shape[0]
    }
