# youtube_meditation_analyzer/streamlit_app.py

import streamlit as st
from utils.youtube_api import search_meditation_videos_today
import pandas as pd

st.set_page_config(page_title="Meditation YouTube Analyzer", layout="wide")
st.title("🧘 Meditation YouTube Analyzer")

st.markdown("""
Một công cụ phân tích các video chủ đề **meditation** trên YouTube:
- Hiển thị video đạt 1000 views nhanh nhất hôm nay
- Thống kê tổng video đăng hôm nay
- Video đang livestream
- Số kênh còn hoạt động
""")

# Fetch data
with st.spinner("🔍 Đang tìm video meditation hôm nay..."):
    videos_df = search_meditation_videos_today()

# 1. Tổng số video
st.metric("📈 Tổng video hôm nay", len(videos_df))

# 2. Lọc video >1000 views
popular_videos = videos_df[videos_df["viewCount"] > 1000].sort_values("publishedAt")

st.subheader("🔥 Video > 1000 views hôm nay")
for i, row in popular_videos.iterrows():
    st.video(f"https://www.youtube.com/watch?v={row['videoId']}")
    st.write(f"**{row['title']}** — {row['channelTitle']} ({row['viewCount']} views)")

# 3. Livestream count
live_count = len(videos_df[videos_df['liveBroadcastContent'] == 'live'])
st.metric("📺 Livestream meditation", live_count)

# 4. Thống kê kênh
channel_stats = videos_df.groupby("channelTitle").agg({
    "videoId": "count",
    "viewCount": "sum"
}).reset_index().rename(columns={"videoId": "Tổng video", "viewCount": "Tổng views"})

st.subheader("📊 Thống kê kênh")
st.dataframe(channel_stats)
