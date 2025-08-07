import streamlit as st
import pandas as pd
import plotly.express as px
from utils.youtube_api import search_meditation_videos_today

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

# Chuyển thành DataFrame nếu chưa
if isinstance(videos_df, list):
    videos_df = pd.DataFrame(videos_df)

# Xử lý thiếu cột country
if "country" not in videos_df.columns:
    videos_df["country"] = "Unknown"

# Tổng số video
st.metric("📈 Tổng video hôm nay", len(videos_df))

# Livestream count
live_count = len(videos_df[videos_df['liveBroadcastContent'] == 'live'])
st.metric("📺 Livestream meditation", live_count)

# Lọc theo quốc gia
countries = ["Tất cả"] + sorted(videos_df["country"].unique())
selected_country = st.selectbox("🌍 Chọn quốc gia", countries)
if selected_country != "Tất cả":
    videos_df = videos_df[videos_df["country"] == selected_country]

# Video >1000 views
popular_videos = videos_df[videos_df["viewCount"] > 1000].sort_values("publishedAt")
st.subheader("🔥 Video > 1000 views hôm nay")
cols = st.columns(3)
for i, (_, row) in enumerate(popular_videos.iterrows()):
    with cols[i % 3]:
        st.video(f"https://www.youtube.com/watch?v={row['videoId']}")
        st.write(f"**{row['title']}** — {row['channelTitle']} ({row['viewCount']} views)")

# Thống kê kênh
channel_stats = videos_df.groupby("channelTitle").agg({
    "videoId": "count",
    "viewCount": "sum"
}).reset_index().rename(columns={"videoId": "Tổng video", "viewCount": "Tổng views"})
st.subheader("📊 Thống kê kênh")
st.dataframe(channel_stats)

# Biểu đồ cột: Top kênh theo lượt view
fig_bar = px.bar(channel_stats.sort_values("Tổng views", ascending=False).head(10),
                 x="channelTitle", y="Tổng views",
                 title="🏆 Top 10 kênh meditation theo lượt xem hôm nay")
st.plotly_chart(fig_bar, use_container_width=True)

# Biểu đồ tròn: Phân bố video theo quốc gia
country_counts = videos_df["country"].value_counts().reset_index()
country_counts.columns = ["Quốc gia", "Số video"]
fig_pie = px.pie(country_counts, names="Quốc gia", values="Số video",
                 title="🌍 Tỷ lệ video meditation theo quốc gia")
st.plotly_chart(fig_pie, use_container_width=True)
