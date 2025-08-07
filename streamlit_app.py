import streamlit as st
import pandas as pd
import plotly.express as px
from utils.youtube_api import search_meditation_videos_today

st.set_page_config(page_title="Meditation YouTube Analyzer", layout="wide")
st.title("🧘 Meditation YouTube Analyzer")

st.markdown("""
Một công cụ phân tích các video chủ đề **meditation** trên YouTube:
- Hiển thị video đạt 10000 views nhanh nhất hôm nay (dạng grid)
- Thống kê tổng video đăng hôm nay, video đang livestream
- Bộ lọc theo quốc gia
- Biểu đồ thống kê video & views theo kênh
""")

# Fetch data
with st.spinner("🔍 Đang tìm video meditation hôm nay..."):
    videos_df = search_meditation_videos_today()

# Nếu là list thì chuyển thành DataFrame
if isinstance(videos_df, list):
    videos_df = pd.DataFrame(videos_df)

# ⛔ Kiểm tra nếu trống
if videos_df.empty:
    st.warning("Không tìm thấy video meditation hôm nay.")
    st.stop()

# 👉 Quốc gia (nếu có)
if "country" not in videos_df.columns:
    videos_df["country"] = "Unknown"

# Bộ lọc quốc gia
countries = videos_df["country"].unique().tolist()
selected_country = st.selectbox("🌍 Lọc theo quốc gia", ["Tất cả"] + sorted(countries))
if selected_country != "Tất cả":
    videos_df = videos_df[videos_df["country"] == selected_country]

# Tổng số video
st.metric("📈 Tổng video hôm nay", len(videos_df))

# Livestream
live_count = len(videos_df[videos_df['liveBroadcastContent'] == 'live'])
st.metric("📺 Video đang livestream", live_count)

# Video > 1000 views
popular_videos = videos_df[videos_df["viewCount"] > 10000].sort_values("publishedAt")
st.subheader("🔥 Video > 10000 views hôm nay")

# 👉 Hiển thị dạng grid 3 cột
cols = st.columns(3)
for i, (_, row) in enumerate(popular_videos.iterrows()):
    with cols[i % 3]:
        st.video(f"https://www.youtube.com/watch?v={row['videoId']}")
        st.markdown(f"**{row['title']}**")
        st.caption(f"👤 {row['channelTitle']} | 👁️ {row['viewCount']} views")

# Thống kê từng kênh
st.subheader("📊 Thống kê kênh (Tổng video & view)")
channel_stats = videos_df.groupby("channelTitle").agg({
    "videoId": "count",
    "viewCount": "sum"
}).reset_index().rename(columns={"videoId": "Tổng video", "viewCount": "Tổng views"})

st.dataframe(channel_stats)

# Biểu đồ cột: video theo kênh
fig1 = px.bar(channel_stats.sort_values("Tổng video", ascending=False), 
              x="channelTitle", y="Tổng video", title="Số video theo kênh")
st.plotly_chart(fig1, use_container_width=True)

# Biểu đồ cột: views theo kênh
fig2 = px.bar(channel_stats.sort_values("Tổng views", ascending=False), 
              x="channelTitle", y="Tổng views", title="Tổng lượt xem theo kênh")
st.plotly_chart(fig2, use_container_width=True)
