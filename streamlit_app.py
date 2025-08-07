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

# --- Metrics Grid ---
st.markdown("### 📊 Tổng quan hôm nay")
grid1, grid2, grid3 = st.columns(3)

with grid1:
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
        <h4 style='color:#4a4a4a;'>📈 Tổng video</h4>
        <h2 style='color:#2e7d32;'>{}</h2>
    </div>
    """.format(len(videos_df)), unsafe_allow_html=True)

with grid2:
    live_count = len(videos_df[videos_df['liveBroadcastContent'] == 'live'])
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
        <h4 style='color:#4a4a4a;'>📺 Livestream</h4>
        <h2 style='color:#d32f2f;'>{}</h2>
    </div>
    """.format(live_count), unsafe_allow_html=True)

with grid3:
    total_channels = videos_df['channelTitle'].nunique()
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
        <h4 style='color:#4a4a4a;'>📣 Kênh hoạt động</h4>
        <h2 style='color:#1976d2;'>{}</h2>
    </div>
    """.format(total_channels), unsafe_allow_html=True)

# Bộ lọc tìm kiếm
st.markdown("### 🔍 Bộ lọc video")
col1, col2 = st.columns(2)

with col1:
    keyword_filter = st.text_input("🔤 Lọc theo từ khóa tiêu đề video")

with col2:
    channel_filter = st.text_input("📺 Lọc theo tên kênh")

if keyword_filter:
    videos_df = videos_df[videos_df['title'].str.contains(keyword_filter, case=False, na=False)]
if channel_filter:
    videos_df = videos_df[videos_df['channelTitle'].str.contains(channel_filter, case=False, na=False)]

# Phân loại theo lượt xem
st.markdown("### 🎯 Phân loại video theo lượt xem")
def categorize_views(views):
    if views >= 5000:
        return "Cao"
    elif views >= 1000:
        return "Trung bình"
    return "Thấp"

videos_df['Phân loại lượt xem'] = videos_df['viewCount'].apply(categorize_views)
st.dataframe(videos_df[['title', 'channelTitle', 'viewCount', 'Phân loại lượt xem']])

# Toggle dark mode CSS
if st.toggle("🌙 Chế độ Dark Mode"):
    st.markdown("""
    <style>
    body, .stApp {
        background-color: #121212;
        color: #e0e0e0;
    }
    .video-card {
        background: #1e1e1e !important;
        color: #e0e0e0 !important;
        border-color: #333 !important;
    }
    .video-title {
        color: #fff !important;
    }
    .video-meta {
        color: #aaa !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Toàn bộ video hôm nay
st.subheader("📂 Tất cả video hôm nay")

video_cards = """
<style>
.video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
    justify-content: center;
}
.video-card {
    background: white;
    border-radius: 12px;
    border: 1px solid #ddd;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform 0.2s ease;
}
.video-card:hover {
    transform: scale(1.02);
}
.video-card iframe {
    width: 100%;
    height: 180px;
    border: none;
}
.video-info {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.video-title {
    font-weight: 600;
    font-size: 15px;
    color: #222;
    line-height: 1.4;
}
.video-meta {
    font-size: 13px;
    color: #666;
}
</style>
<div class="video-grid">
"""

for _, row in videos_df.sort_values("publishedAt", ascending=False).iterrows():
    video_cards += f"""
    <div class="video-card">
        <iframe src="https://www.youtube.com/embed/{row['videoId']}" allowfullscreen></iframe>
        <div class="video-info">
            <div class="video-title">{row['title']}</div>
            <div class="video-meta">{row['channelTitle']} — {row['viewCount']:,} views</div>
        </div>
    </div>
    """

video_cards += "</div>"
st.markdown(video_cards, unsafe_allow_html=True)
