import streamlit as st
import pandas as pd
import plotly.express as px
from utils.youtube_api import search_meditation_videos_today

st.set_page_config(page_title="🧘 Meditation YouTube Dashboard", layout="wide")
st.title("🧘 Meditation YouTube Analyzer")

st.markdown("""
Một công cụ phân tích các video chủ đề **meditation** trên YouTube:
- Hiển thị video đạt 1000 views nhanh nhất hôm nay
- Thống kê tổng video đăng hôm nay
- Video đang livestream
- Số kênh còn hoạt động
- Lọc theo quốc gia
- Biểu đồ thống kê views & video
""")

# Fetch data
with st.spinner("🔍 Đang tìm video meditation hôm nay..."):
    videos_df = search_meditation_videos_today()

if videos_df.empty:
    st.warning("Không tìm thấy video meditation nào hôm nay.")
    st.stop()

# Clean data
videos_df['publishedAt'] = pd.to_datetime(videos_df['publishedAt'])
videos_df['viewCount'] = videos_df['viewCount'].astype(int)

# Filter by country
countries = videos_df['country'].unique().tolist()
selected_country = st.selectbox("🌍 Chọn quốc gia", ["Tất cả"] + sorted(countries))

if selected_country != "Tất cả":
    videos_df = videos_df[videos_df['country'] == selected_country]

# Grid: popular videos >1000 views
popular_videos = videos_df[videos_df["viewCount"] > 1000].sort_values("publishedAt")
st.subheader("🔥 Video > 1000 views hôm nay")
cols = st.columns(3)
for idx, (_, row) in enumerate(popular_videos.iterrows()):
    with cols[idx % 3]:
        st.video(f"https://www.youtube.com/watch?v={row['videoId']}")
        st.write(f"**{row['title']}**\n
        👤 `{row['channelTitle']}`\n
        👁️ {row['viewCount']} views\n
        📍 {row['country']}")

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("📈 Tổng video hôm nay", len(videos_df))
col2.metric("📺 Đang livestream", len(videos_df[videos_df['liveBroadcastContent'] == 'live']))
col3.metric("📊 Số kênh", videos_df['channelTitle'].nunique())

# Channel stats
channel_stats = videos_df.groupby("channelTitle").agg({
    "videoId": "count",
    "viewCount": "sum",
    "country": "first"
}).reset_index().rename(columns={
    "videoId": "Tổng video",
    "viewCount": "Tổng views"
})

st.subheader("📊 Thống kê theo kênh")
st.dataframe(channel_stats)

# Biểu đồ
st.subheader("📉 Biểu đồ thống kê")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    bar = px.bar(channel_stats.sort_values("Tổng views", ascending=False).head(10),
                 x="channelTitle", y="Tổng views",
                 title="Top 10 kênh có lượt xem cao nhất")
    st.plotly_chart(bar, use_container_width=True)

with chart_col2:
    pie = px.pie(videos_df, names="country", title="Tỷ lệ video theo quốc gia")
    st.plotly_chart(pie, use_container_width=True)
