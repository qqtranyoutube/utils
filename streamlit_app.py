import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
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
        <h2 style='color:#d32f2f;'>{}</h2>
    </div>
    """.format(live_count), unsafe_allow_html=True)

with g4:
    total_channels = videos_df['channelTitle'].nunique()
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
        <h4 style='color:#4a4a4a;'>📣 Kênh hoạt động</h4>
        <h2 style='color:#1976d2;'>{}</h2>
    </div>
    """.format(total_channels), unsafe_allow_html=True)

# RPM ước tính
avg_rpm = st.slider("💰 Nhập RPM trung bình (USD/1000 views):", 0.2, 8.0, 2.5, 0.1)
videos_df['RPM (USD)'] = (videos_df['viewCount'] / 1000) * avg_rpm
st.metric(label="🏡 Doanh thu ước tính (tổng):", value=f"${videos_df['RPM (USD)'].sum():,.2f}")

# Thống kê theo giờ
videos_df['publishedHour'] = pd.to_datetime(videos_df['publishedAt']).dt.hour
fig = px.histogram(videos_df, x='publishedHour', nbins=24, title="📊 Thống kê số video theo giờ đăng",
                   labels={'publishedHour': 'Giờ trong ngày'}, color_discrete_sequence=['#2196f3'])
st.plotly_chart(fig, use_container_width=True)

# Bộ lọc tìm kiếm nâng cao
st.markdown("### 🔍 Bộ lọc video nâng cao")
col1, col2, col3 = st.columns(3)

with col1:
    keyword_filter = st.text_input("🌤️ Lọc theo từ khóa tiêu đề video")

with col2:
    channel_filter = st.text_input("💼 Lọc theo tên kênh")

with col3:
    rpm_threshold = st.number_input("💰 Lọc theo RPM tối thiểu (USD):", min_value=0.0, step=0.1, value=0.0)

if keyword_filter:
    videos_df = videos_df[videos_df['title'].str.contains(keyword_filter, case=False, na=False)]
if channel_filter:
    videos_df = videos_df[videos_df['channelTitle'].str.contains(channel_filter, case=False, na=False)]
videos_df = videos_df[videos_df['RPM (USD)'] >= rpm_threshold]

# Phân loại theo lượt xem và điều kiện kiếm tiền
st.markdown("### 🌟 Phân loại video theo lượt xem và kiểm tiền")
def categorize_views(views):
    if views >= 5000:
        return "Cao"
    elif views >= 1000:
        return "Trung bình"
    return "Thấp"

def monetize_status(views):
    return "✅ Đủ điều kiện" if views >= 1000 else "❌ Chưa đủ"

videos_df['Phân loại lượt xem'] = videos_df['viewCount'].apply(categorize_views)
videos_df['Monetization'] = videos_df['viewCount'].apply(monetize_status)

# Thêm cột liên kết
videos_df['Tiêu đề (có link)'] = videos_df.apply(lambda row: f"[{row['title']}](https://www.youtube.com/watch?v={row['videoId']})", axis=1)

st.dataframe(videos_df[['Tiêu đề (có link)', 'channelTitle', 'viewCount', 'Phân loại lượt xem', 'Monetization', 'RPM (USD)']])

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

# Toàn bộ video hôm nay dạng grid
st.subheader("📂 Tất cả video hôm nay")

video_grid_html = """
<style>
.video-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
    padding: 10px;
}
.video-card {
    background: white;
    border-radius: 12px;
    border: 1px solid #ccc;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column;
    transition: transform 0.2s ease;
    height: 100%;
}
.video-card:hover {
    transform: scale(1.02);
}
.video-card iframe {
    width: 100%;
    aspect-ratio: 16 / 9;
    border: none;
}
.video-info {
    padding: 10px 14px;
    font-family: sans-serif;
    font-size: 14px;
}
.video-title {
    font-weight: 600;
    margin-bottom: 6px;
    color: #222;
    line-height: 1.4;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}
.video-meta {
    color: #555;
    font-size: 13px;
}
</style>
<div class="video-grid">
"""

for _, row in videos_df.sort_values("publishedAt", ascending=False).iterrows():
    video_grid_html += f"""
    <div class="video-card">
        <iframe src="https://www.youtube.com/embed/{row['videoId']}" allowfullscreen></iframe>
        <div class="video-info">
            <div class="video-title">{row['title']}</div>
            <div class="video-meta">{row['channelTitle']} — {row['viewCount']:,} views</div>
        </div>
    </div>
    """

video_grid_html += "</div>"
components.html(video_grid_html, height=1200, scrolling=True)
