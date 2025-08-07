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

# Lọc theo quốc gia (nếu có)
if 'channelCountry' in videos_df.columns:
    countries = videos_df['channelCountry'].dropna().unique()
    selected_country = st.selectbox("🌍 Lọc theo quốc gia", options=['Tất cả'] + sorted(countries.tolist()))
    if selected_country != 'Tất cả':
        videos_df = videos_df[videos_df['channelCountry'] == selected_country]

# Video >1000 views
popular_videos = videos_df[videos_df["viewCount"] > 1000].sort_values("publishedAt")
st.subheader("🔥 Video nổi bật (>1000 views)")
cols = st.columns(3)
for i, (_, row) in enumerate(popular_videos.iterrows()):
    with cols[i % 3]:
        st.video(f"https://www.youtube.com/watch?v={row['videoId']}")
        st.markdown(f"**{row['title']}**<br>{row['channelTitle']} — {row['viewCount']:,} views", unsafe_allow_html=True)

# Livestream videos
live_videos = videos_df[videos_df['liveBroadcastContent'] == 'live']
if not live_videos.empty:
    st.subheader("🔴 Video đang livestream")
    cols_live = st.columns(2)
    for i, (_, row) in enumerate(live_videos.iterrows()):
        with cols_live[i % 2]:
            st.video(f"https://www.youtube.com/watch?v={row['videoId']}")
            st.markdown(f"**{row['title']}**<br>{row['channelTitle']}", unsafe_allow_html=True)

# Thống kê kênh
channel_stats = videos_df.groupby("channelTitle").agg({
    "videoId": "count",
    "viewCount": "sum"
}).reset_index().rename(columns={"videoId": "Tổng video", "viewCount": "Tổng views"})
st.subheader("📊 Thống kê kênh")
st.dataframe(channel_stats.sort_values("Tổng views", ascending=False))

# Biểu đồ top kênh
fig1 = px.bar(channel_stats.sort_values("Tổng views", ascending=False).head(10),
             x="channelTitle", y="Tổng views",
             title="Top 10 kênh theo lượt xem hôm nay",
             labels={"channelTitle": "Kênh", "Tổng views": "Lượt xem"})
st.plotly_chart(fig1, use_container_width=True)

# Biểu đồ phân bố quốc gia
if 'channelCountry' in videos_df.columns:
    country_dist = videos_df['channelCountry'].value_counts().reset_index()
    country_dist.columns = ['Quốc gia', 'Số video']
    fig2 = px.pie(country_dist, names='Quốc gia', values='Số video', title='Tỷ lệ video theo quốc gia')
    st.plotly_chart(fig2, use_container_width=True)

# Toàn bộ video hôm nay
st.subheader("🗂️ Tất cả video hôm nay")

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
