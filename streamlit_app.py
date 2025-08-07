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

if videos_df.empty:
    st.warning("Không tìm thấy video nào hôm nay.")
    st.stop()

# Tổng số video
st.metric("📈 Tổng video hôm nay", len(videos_df))

# Livestream count
live_count = len(videos_df[videos_df['liveBroadcastContent'] == 'live'])
st.metric("📺 Livestream meditation", live_count)

# Số kênh còn hoạt động
total_channels = videos_df['channelTitle'].nunique()
st.metric("📣 Số kênh hoạt động", total_channels)

# Lọc theo quốc gia (nếu có cột channelCountry)
if 'channelCountry' in videos_df.columns:
    countries = videos_df['channelCountry'].dropna().unique()
    selected_country = st.selectbox("🌍 Lọc theo quốc gia", options=['Tất cả'] + sorted(countries.tolist()))

    if selected_country != 'Tất cả':
        videos_df = videos_df[videos_df['channelCountry'] == selected_country]

# Video >1000 views
popular_videos = videos_df[videos_df["viewCount"] > 1000].sort_values("publishedAt")
st.subheader("🔥 Video > 1000 views hôm nay")
cols = st.columns(3)
for i, (_, row) in enumerate(popular_videos.iterrows()):
    with cols[i % 3]:
        st.video(f"https://www.youtube.com/watch?v={row['videoId']}")
        st.write(f"**{row['title']}**\n{row['channelTitle']} — {row['viewCount']:,} views")

# Video đang livestream
live_videos = videos_df[videos_df['liveBroadcastContent'] == 'live']
if not live_videos.empty:
    st.subheader("🔴 Video đang livestream")
    cols_live = st.columns(2)
    for i, (_, row) in enumerate(live_videos.iterrows()):
        with cols_live[i % 2]:
            st.video(f"https://www.youtube.com/watch?v={row['videoId']}")
            st.write(f"**{row['title']}**\n{row['channelTitle']}")

# Thống kê kênh
channel_stats = videos_df.groupby("channelTitle").agg({
    "videoId": "count",
    "viewCount": "sum"
}).reset_index().rename(columns={"videoId": "Tổng video", "viewCount": "Tổng views"})
st.subheader("📊 Thống kê kênh")
st.dataframe(channel_stats.sort_values("Tổng views", ascending=False))

# Biểu đồ top kênh theo view
fig1 = px.bar(channel_stats.sort_values("Tổng views", ascending=False).head(10),
             x="channelTitle", y="Tổng views",
             title="Top 10 kênh theo lượt xem hôm nay")
st.plotly_chart(fig1, use_container_width=True)

# Biểu đồ phân bố quốc gia
if 'channelCountry' in videos_df.columns:
    country_dist = videos_df['channelCountry'].value_counts().reset_index()
    country_dist.columns = ['Quốc gia', 'Số video']
    fig2 = px.pie(country_dist, names='Quốc gia', values='Số video', title='Tỷ lệ video theo quốc gia')
    st.plotly_chart(fig2, use_container_width=True)
