import os
import streamlit as st
from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd

# Load biến môi trường từ .env nếu có
load_dotenv()

def get_api_key():
    """
    Lấy API key từ biến môi trường, Streamlit secrets hoặc form nhập tay.
    """
    api_key = os.getenv("YOUTUBE_API_KEY") or st.secrets.get("YOUTUBE_API_KEY", None)

    # Nếu chưa có API key thì hỏi người dùng nhập
    if not api_key:
        st.warning("⚠ Chưa tìm thấy **YOUTUBE_API_KEY**. Vui lòng nhập để tiếp tục.")
        with st.form("api_key_form"):
            user_key = st.text_input("Nhập YouTube API Key:", type="password")
            submit = st.form_submit_button("Lưu & Tiếp tục")
            if submit:
                if user_key.strip():
                    st.session_state["YOUTUBE_API_KEY"] = user_key.strip()
                    st.success("✅ API Key đã được lưu tạm thời cho phiên này.")
                    return user_key.strip()
                else:
                    st.error("❌ API Key không hợp lệ.")
                    return None
        return None

    return api_key


def build_youtube_service():
    """
    Khởi tạo service YouTube API.
    """
    api_key = st.session_state.get("YOUTUBE_API_KEY") or get_api_key()
    if not api_key:
        return None
    return build("youtube", "v3", developerKey=api_key)


def search_meditation_videos_today():
    """
    Tìm video chủ đề meditation đăng hôm nay.
    """
    youtube = build_youtube_service()
    if youtube is None:
        st.stop()  # Dừng app nếu chưa có API key

    today = datetime.utcnow().date()
    published_after = datetime.combine(today, datetime.min.time()).isoformat("T") + "Z"

    request = youtube.search().list(
        q="meditation",
        part="snippet",
        type="video",
        order="date",
        publishedAfter=published_after,
        maxResults=50
    )
    response = request.execute()

    videos_data = []
    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        channel_id = snippet["channelId"]

        # Lấy chi tiết video
        stats_req = youtube.videos().list(
            part="statistics",
            id=video_id
