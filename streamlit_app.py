# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.youtube_api import final_pipeline
from googleapiclient.errors import HttpError

st.set_page_config(page_title="Meditation YouTube Analyzer", layout="wide")
st.title("🧘 Meditation YouTube Analyzer — PRO")

st.markdown(
    """
Công cụ phân tích video chủ đề **meditation** (cập nhật hàng ngày).
Tính năng: tìm video hôm nay, livestream, thống kê kênh, RPM ước tính, lọc nâng cao, grid hiển thị.
"""
)

# --- API key input (Streamlit secrets preferred) ---
def get_api_key_from_ui():
    # prefer session state
    if "YOUTUBE_API_KEY" in st.session_state:
        return st.session_state["YOUTUBE_API_KEY"]

    # prefer secrets set in Streamlit Cloud
    if "YOUTUBE_API_KEY" in st.secrets:
        st.session_state["YOUTUBE_API_KEY"] = st.secrets["YOUTUBE_API_KEY"]
        return st.session_state["YOUTUBE_API_KEY"]

    # form to input API key
    with st.expander("🔑 Nhập YouTube API Key (hoặc lưu ở Secrets)"):
        with st.form("api_form"):
            key = st.text_input("YouTube API Key:", type="password")
            submitted = st.form_submit_button("Lưu cho phiên này")
            if submitted:
                if key.strip():
                    st.session_state["YOUTUBE_API_KEY"] = key.strip()
                    st.success("API Key đã lưu tạm trong phiên.")
                else:
                    st.error("API Key không hợp lệ.")
    return st.session_state.get("YOUTUBE_API_KEY", None)


api_key = get_api_key_from_ui()
if not api_key:
    st.stop()

# Slider for global RPM multiplier / baseline (affects estimated RPM calculation)
st.sidebar.header("Cấu hình RPM")
rpm_override = st.sidebar.slider("Điều chỉnh hệ số RPM (tỷ lệ, mặc định 1.0)", 0.2, 3.0, 1.0, 0.1)

# --- Fetch pipeline (with error handling) ---
with st.spinner("🔍 Đang lấy dữ liệu từ YouTube..."):
    try:
        df = final_pipeline(api_key)
        # apply rpm_override by scaling estimatedRPM_USD
        if not df.empty:
            df["estimatedRPM_USD"] = (df["estimatedRPM_USD"].fillna(0).astype(float) * rpm_override).round(2)
    except HttpError as e:
        st.error("🚨 YouTube API trả về lỗi. Có thể đã vượt quota (quotaExceeded) hoặc bị rate limit.")
        st.exception(e)
        st.stop()
    except Exception as e:
        st.error("🚨 Lỗi khi chạy pipeline.")
        st.exception(e)
        st.stop()

if df.empty:
    st.info("Không có video meditation nào được tìm thấy hôm nay.")
    st.stop()

# --- Top metrics (grid 4 columns) ---
videos_1k = df[df["viewCount"] >= 1000].sort_values("publishedAt")
fastest_1k_title = videos_1k.iloc[0]["title"] if not videos_1k.empty else "Chưa có"

col1, col2, col3, col4 = st.columns(4)
col1.metric("📈 Tổng video hôm nay", len(df))
col2.metric("📣 Kênh hoạt động", df["channelId"].nunique())
col3.metric("🔥 Video đạt 1000 views nhanh nhất", fastest_1k_title[:80])
col4.metric("🔴 Livestreams", int(df["liveDetailsPresent"].sum()))

# --- Filters ---
st.sidebar.header("Bộ lọc nâng cao")
keyword = st.sidebar.text_input("Từ khóa trong tiêu đề")
channel_query = st.sidebar.text_input("Lọc theo tên kênh")
country_filter = st.sidebar.selectbox("Quốc gia (country)", options=["All"] + sorted(df["country"].fillna("Unknown").unique().tolist()))
min_rpm = st.sidebar.number_input("RPM tối thiểu (USD):", 0.0, 10000.0, 0.0, 0.1)
only_monetizable = st.sidebar.checkbox("Chỉ hiển thị video đủ điều kiện Monetization (>=1000 views)", False)

# Apply filters
df_display = df.copy()
if keyword:
    df_display = df_display[df_display["title"].str.contains(keyword, case=False, na=False)]
if channel_query:
    df_display = df_display[df_display["channelTitle"].str.contains(channel_query, case=False, na=False)]
if country_filter and country_filter != "All":
    df_display = df_display[df_display["country"] == country_filter]
if min_rpm > 0:
    df_display = df_display[df_display["estimatedRPM_USD"] >= float(min_rpm)]
if only_monetizable:
    df_display = df_display[df_display["Monetizable"] == True]

# --- Chart: videos by hour ---
df["publishedHour"] = pd.to_datetime(df["publishedAt"]).dt.hour
fig = px.histogram(df, x="publishedHour", nbins=24, title="📊 Số video theo giờ đăng (UTC)", labels={"publishedHour": "Giờ (UTC)"})
st.plotly_chart(fig, use_container_width=True)

# --- Grid (4 columns) HTML render using components.html for full control ---
st.subheader("📂 Tất cả video hôm nay (Grid)")
import streamlit.components.v1 as components

def render_grid_html(df_grid: pd.DataFrame, cols: int = 4):
    # Sanitize/cut long titles
    html = """
    <style>
    .video-grid { display: grid; grid-template-columns: repeat(%d, 1fr); gap: 18px; }
    .video-card { background:#fff; border-radius:10px; box-shadow:0 6px 18px rgba(0,0,0,0.08); overflow:hidden; border:1px solid #e6e6e6; }
    .video-thumb { width:100%%; height:180px; object-fit:cover; display:block; }
    .card-body { padding:10px 12px; font-family:Inter, Roboto, Arial, sans-serif; }
    .title { font-weight:600; font-size:14px; margin-bottom:6px; color:#111; line-height:1.3; }
    .meta { font-size:13px; color:#666; }
    .badge { display:inline-block; padding:3px 8px; border-radius:10px; font-size:12px; background:#ff5252; color:white; margin-right:6px; }
    </style>
    <div class="video-grid">
    """ % cols

    for _, r in df_grid.iterrows():
        title = (r.get("title") or "")[:140]
        thumb = r.get("thumbnail") or ""
        vid = r.get("videoId")
        url = f"https://www.youtube.com/watch?v={vid}"
        channel = r.get("channelTitle") or ""
        views = int(r.get("viewCount", 0))
        subs = int(r.get("subscriberCount", 0)) if not pd.isna(r.get("subscriberCount")) else 0
        rpm = float(r.get("estimatedRPM_USD", 0.0))
        monet = r.get("Monetizable", False)
        live = r.get("liveDetailsPresent", False)

        badge_html = '<span class="badge">LIVE</span>' if live else ""
        monet_html = '<span style="background:#1976d2;color:white;padding:3px 8px;border-radius:8px;font-size:12px;margin-left:6px;">$%.2f</span>' % rpm

        html += f"""
        <div class="video-card">
            <a href="{url}" target="_blank"><img class="video-thumb" src="{thumb}" alt="thumb"/></a>
            <div class="card-body">
                <div class="title"><a href="{url}" target="_blank" style="color:inherit;text-decoration:none">{title}</a></div>
                <div class="meta">{badge_html} {channel} — {views:,} views {monet_html}</div>
            </div>
        </div>
        """

    html += "</div>"
    return html

# Ensure channel-level fields exist (merge from df if named differently)
# Our final df columns: videoId,title,channelTitle,viewCount,subscriberCount,channelVideoCount,estimatedRPM_USD,Monetizable,liveDetailsPresent,thumbnail
# If names differ (older pipelines) attempt to map:
col_map = {
    "videoId": "videoId",
    "title": "title",
    "channelTitle": "channelTitle",
    "viewCount": "viewCount",
    "subscriberCount": "subscriberCount",
    "channelVideoCount": "channelVideoCount",
    "estimatedRPM_USD": "estimatedRPM_USD",
    "Monetizable": "Monetizable",
    "liveDetailsPresent": "liveDetailsPresent",
    "thumbnail": "thumbnail",
}
# Normalize column names expected by render
df_render = df_display.copy()
# Some columns may have different capitalization - create aliases
if "videoId" not in df_render.columns and "Video ID" in df_render.columns:
    df_render["videoId"] = df_render["Video ID"]
if "title" not in df_render.columns and "Title" in df_render.columns:
    df_render["title"] = df_render["Title"]
if "channelTitle" not in df_render.columns and "Channel" in df_render.columns:
    df_render["channelTitle"] = df_render["Channel"]
if "viewCount" not in df_render.columns and "Views" in df_render.columns:
    df_render["viewCount"] = df_render["Views"]
if "thumbnail" not in df_render.columns and "Thumbnail" in df_render.columns:
    df_render["thumbnail"] = df_render["Thumbnail"]

# Render grid
html = render_grid_html(df_render, cols=4)
components.html(html, height=900, scrolling=True)

# --- Detailed table for sorting/filtering ---
st.subheader("🔎 Bảng chi tiết (có link title)")
table_df = df_display.copy()
# Add clickable markdown link column
table_df["Title (link)"] = table_df.apply(lambda r: f"[{r['title'][:120]}](https://www.youtube.com/watch?v={r['videoId']})", axis=1)
# Select useful columns
show_cols = ["Title (link)", "channelTitle", "viewCount", "subscriberCount", "channelVideoCount", "country", "Monetizable", "estimatedRPM_USD", "liveDetailsPresent", "publishedAt"]
present_cols = [c for c in show_cols if c in table_df.columns]
st.dataframe(table_df[present_cols].sort_values("viewCount", ascending=False), use_container_width=True)
