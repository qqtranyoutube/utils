import os
from datetime import datetime
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

def get_api_key():
    """Lấy API key từ env hoặc nhập tay nếu chưa có."""
    if "YOUTUBE_API_KEY" in st.session_state:
        return st.session_state["YOUTUBE_API_KEY"]

    api_key = os.getenv("YOUTUBE_API_KEY") or st.secrets.get("YOUTUBE_API_KEY", None)

    if not api_key:
        st.warning("⚠ Chưa tìm thấy **YOUTUBE_API_KEY**. Vui lòng nhập để tiếp tục.")
        with st.form("api_key_form"):
            user_key = st.text_input("Nhập YouTube API Key:", type="password")
            submitted = st.form_submit_button("Lưu & Tiếp tục")
            if submitted:
                if user_key.strip():
                    st.session_state["YOUTUBE_API_KEY"] = user_key.strip()
                    st.success("✅ API Key đã được lưu.")
                    return user_key.strip()
                else:
                    st.error("❌ API Key không hợp lệ.")
                    return None
        return None

    st.session_state["YOUTUBE_API_KEY"] = api_key
    return api_key

def build_youtube_service():
    """Khởi tạo YouTube API client."""
    api_key = get_api_key()
    if not api_key:
        return None
    return build("youtube", "v3", developerKey=api_key)

def search_meditation_videos_today():
    """Lấy video meditation đăng hôm nay + thống kê."""
    youtube = build_youtube_service()
    if youtube is None:
        st.stop()

    today = datetime.utcnow().date()
    published_after = datetime.combine(today, datetime.min.time()).isoformat("T") + "Z"

    search_req = youtube.search().list(
        q="meditation",
        part="snippet",
        type="video",
        order="date",
        publishedAfter=published_after,
        maxResults=50
    )
    search_res = search_req.execute()

    videos_data = []
    for item in search_res.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        channel_id = snippet["channelId"]

        # Lấy stats video
        stats_resp = youtube.videos().list(
            part="statistics",
            id=video_id
        ).execute()
        stats = stats_resp["items"][0]["statistics"] if stats_resp.get("items") else {}

        # Lấy stats channel
        channel_resp = youtube.channels().list(
            part="statistics",
            id=channel_id
        ).execute()
        ch_stats = channel_resp["items"][0]["statistics"] if channel_resp.get("items") else {}

        videos_data.append({
            "video_id": video_id,
            "title": snippet["title"],
            "channel_title": snippet["channelTitle"],
            "published_at": snippet["publishedAt"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
            "comments": int(stats.get("commentCount", 0)) if "commentCount" in stats else None,
            "subs": int(ch_stats.get("subscriberCount", 0)),
            "total_videos": int(ch_stats.get("videoCount", 0)),
            "channel_id": channel_id
        })

    df = pd.DataFrame(videos_data)
    return df.sort_values(by="views", ascending=False).reset_index(drop=True)
