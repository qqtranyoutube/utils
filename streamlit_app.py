import streamlit as st
import pandas as pd
import plotly.express as px
from utils.youtube_api import search_meditation_videos_today
from googleapiclient.errors import HttpError

st.set_page_config(page_title="Meditation YouTube Analyzer", layout="wide")
st.title("🧘 Meditation YouTube Analyzer")

st.markdown("""
Công cụ theo dõi xu hướng video **meditation** trên YouTube, cập nhật **hàng ngày**:
- 🔥 Video đạt 1000 views nhanh nhất hôm nay
- 📈 Tổng số video đăng hôm nay
- 🔴 Video đang livestream
- 📣 Tổng số kênh còn hoạt động
""")

# Fetch data
with st.spinner("🔍 Đang lấy dữ liệu video meditation hôm nay..."):
    try:
        videos_df = search_meditation_videos_today()
    except HttpError as e:
        st.error("🚨 Lỗi khi truy vấn YouTube API.")
        st.exception(e)
        st.stop()

if isinstance(videos_df, list):
    videos_df = pd.DataFrame(videos_df)

if videos_df.empty:
    st.warning("⚠️ Không tìm thấy video nào hôm nay.")
    st.stop()

# Tìm video đạt 1000 views nhanh nhất
videos_1000 = videos_df[videos_df['viewCount'] >= 1000].sort_values(by='publishedAt')
fastest_1000 = videos_1000.iloc[0] if not videos_1000.empty else None

# --- Metrics Grid ---
st.markdown("### 📊 Tổng quan hôm nay")
g1, g2, g3, g4 = st.columns(4)

with g1:
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
        <h4 style='color:#4a4a4a;'>🔥 Đạt 1000 views nhanh</h4>
        <h5 style='color:#444;'>{}</h5>
    </div>
    """.format(fastest_1000['title'][:40] + "..." if fastest_1000 is not None else "Chưa có"), unsafe_allow_html=True)

with g2:
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
        <h4 style='color:#4a4a4a;'>📈 Tổng video</h4>
        <h2 style='color:#2e7d32;'>{}</h2>
    </div>
    """.format(len(videos_df)), unsafe_allow_html=True)

with g3:
    live_count = len(videos_df[videos_df['liveBroadcastContent'] == 'live'])
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
        <h4 style='color:#4a4a4a;'>🔴 Livestream</h4>
        <h2 style='color:#d32f2f;'>
