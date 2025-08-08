import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from utils.youtube_api import final_pipeline
from googleapiclient.errors import HttpError

# Page config
st.set_page_config(page_title="Meditation YouTube Analyzer — PRO", layout="wide")

# Title / description
st.title("🧘 Meditation YouTube Analyzer — PRO")
st.markdown("""
Công cụ phân tích **video chủ đề meditation** trên YouTube — cập nhật trong ngày.\
Tính năng: nhập API key, tìm video hôm nay, thống kê, grid full-width responsive, lọc nâng cao, RPM ước tính, xuất CSV.
""")

# --- API key input (prefer secrets) ---
def get_api_key_ui():
    if "YOUTUBE_API_KEY" in st.session_state:
        return st.session_state["YOUTUBE_API_KEY"]
    if st.secrets and st.secrets.get("YOUTUBE_API_KEY"):
        st.session_state["YOUTUBE_API_KEY"] = st.secrets.get("YOUTUBE_API_KEY")
        return st.session_state["YOUTUBE_API_KEY"]

    with st.sidebar.expander("🔑 YouTube API Key (recommended to save in Secrets)"):
        with st.form("api_key_form"):
            key = st.text_input("YouTube API Key", type="password")
            submitted = st.form_submit_button("Lưu tạm & chạy")
            if submitted:
                if key.strip():
                    st.session_state["YOUTUBE_API_KEY"] = key.strip()
                    st.success("API Key đã lưu tạm trong phiên.")
                    st.experimental_rerun()
                else:
                    st.error("API Key không hợp lệ.")
    return None

api_key = get_api_key_ui()
if not api_key:
    st.stop()

# Sidebar controls
st.sidebar.header("Bộ lọc & Cấu hình")
rpm_base = st.sidebar.slider("RPM base (USD/1000 views) - dùng cho ước tính", 0.2, 10.0, 2.5, 0.1)
cols_per_row = st.sidebar.selectbox("Số cột hiển thị trên grid (desktop)", [3,4,5], index=1)

# Advanced filters
st.sidebar.subheader("Bộ lọc nâng cao")
filter_keyword = st.sidebar.text_input("Từ khóa tiêu đề")
filter_channel = st.sidebar.text_input("Tên kênh (partial)")
filter_country = st.sidebar.selectbox("Quốc gia", options=["All"], index=0)
min_rpm = st.sidebar.number_input("RPM tối thiểu (USD)", min_value=0.0, value=0.0, step=0.1)
only_monetizable = st.sidebar.checkbox("Chỉ hiện video đủ điều kiện Monetization (>=1000 views)")

# Fetch data (with error handling)
with st.spinner("🔍 Đang lấy dữ liệu từ YouTube (vui lòng chờ)..."):
    try:
        df = final_pipeline(api_key)
        # Scale RPM by base multiplier
        if not df.empty:
            df["estimatedRPM_USD"] = (df["estimatedRPM_USD"].fillna(0).astype(float) * (rpm_base / 2.5)).round(2)
    except HttpError as e:
        st.error("🚨 YouTube API trả về lỗi (có thể vượt quota). Xem logs chi tiết.")
        st.exception(e)
        st.stop()
    except Exception as e:
        st.error("🚨 Lỗi nội bộ khi chạy pipeline")
        st.exception(e)
        st.stop()

if df.empty:
    st.info("Không tìm thấy video meditation hôm nay.")
    st.stop()

# Populate country filter choices
countries = sorted(df.get("country", pd.Series(["Unknown"]).astype(str)).fillna("Unknown").unique().tolist())
filter_country = st.sidebar.selectbox("Quốc gia", options=["All"] + countries, index=0 if "All" in ["All"] else 0)

# Apply filters to df_display
df_display = df.copy()
if filter_keyword:
    df_display = df_display[df_display["title"].str.contains(filter_keyword, case=False, na=False)]
if filter_channel:
    df_display = df_display[df_display["channelTitle"].str.contains(filter_channel, case=False, na=False)]
if filter_country and filter_country != "All":
    df_display = df_display[df_display["country"] == filter_country]
if min_rpm > 0:
    df_display = df_display[df_display["estimatedRPM_USD"] >= float(min_rpm)]
if only_monetizable:
    df_display = df_display[df_display["Monetizable"] == True]

# --- Top metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("📈 Tổng video hôm nay", len(df))
col2.metric("📣 Kênh hoạt động", df["channelId"].nunique())
videos_1k = df[df["viewCount"] >= 1000].sort_values("publishedAt")
fastest_1k = videos_1k.iloc[0]["title"] if not videos_1k.empty else "Chưa có"
col3.metric("🔥 Video đạt 1000 views nhanh nhất", fastest_1k[:80])
col4.metric("🔴 Livestreams", int(df["liveDetailsPresent"].sum()))

# --- Chart: views by hour ---
st.subheader("📊 Thống kê theo giờ đăng (UTC)")
df["publishedHour"] = pd.to_datetime(df["publishedAt"]).dt.hour
fig = px.histogram(df, x="publishedHour", nbins=24, labels={"publishedHour": "Giờ (UTC)"})
st.plotly_chart(fig, use_container_width=True)

# --- Grid full-width responsive ---
st.subheader("📂 Tất cả video hôm nay (Grid)")

# CSS: full-width container & nicer cards
st.markdown(f"""
<style>
.block-container{{padding:1rem 2rem 2rem 2rem;}}
.video-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
  width: 100%;
}}
.video-card {{
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  border:1px solid #e6e6e6;
  box-shadow: 0 6px 18px rgba(15,15,15,0.06);
  transition: transform .15s ease-in-out, box-shadow .15s ease-in-out;
}}
.video-card:hover{{transform:translateY(-6px);box-shadow:0 10px 30px rgba(15,15,15,0.12);}}
.video-thumb{{width:100%;height:190px;object-fit:cover;display:block}}
.card-body{{padding:12px 14px;font-family:Inter, Roboto, Arial, sans-serif}}
.title{{font-weight:600;font-size:15px;color:#111;line-height:1.3;display:block;text-decoration:none}}
.meta{{color:#666;font-size:13px;margin-top:8px}}
.badge{{display:inline-block;padding:4px 8px;border-radius:10px;font-size:12px;background:#ff5252;color:#fff;margin-right:6px}}
.rpm-badge{{display:inline-block;padding:4px 8px;border-radius:8px;font-size:12px;background:#1976d2;color:#fff;margin-left:6px}}
</style>
""", unsafe_allow_html=True)

# Render grid HTML
html = '<div class="video-grid">'
for _, r in df_display.iterrows():
    vid = r.get("videoId")
    url = f"https://www.youtube.com/watch?v={vid}"
    thumb = r.get("thumbnail") or ""
    title = (r.get("title") or "")[:140]
    channel = r.get("channelTitle") or ""
    views = int(r.get("viewCount", 0))
    rpm = float(r.get("estimatedRPM_USD", 0.0))
    monet = r.get("Monetizable", False)
    live = r.get("liveDetailsPresent", False)
    subs = int(r.get("subscriberCount", 0)) if not pd.isna(r.get("subscriberCount")) else 0

    live_html = '<span class="badge">LIVE</span>' if live else ''
    monet_html = f'<span class="rpm-badge">${rpm:,.2f}</span>'

    html += f"""
    <div class="video-card">
      <a href="{url}" target="_blank"><img class="video-thumb" src="{thumb}"/></a>
      <div class="card-body">
         <a class="title" href="{url}" target="_blank">{title}</a>
         <div class="meta">{live_html} {channel} — {views:,} views • subs {subs:,} {monet_html}</div>
      </div>
    </div>
    """
html += '</div>'
components.html(html, height=820, scrolling=True)

# --- Detailed table + CSV export ---
st.subheader("🔎 Bảng chi tiết & Export")
# prepare table
table_df = df_display.copy()
if "title" in table_df.columns:
    table_df["Title (link)"] = table_df.apply(lambda r: f"[{r['title'][:120]}](https://www.youtube.com/watch?v={r['videoId']})", axis=1)
cols_show = [c for c in ["Title (link)", "channelTitle", "viewCount", "subscriberCount", "channelVideoCount", "country", "Monetizable", "estimatedRPM_USD", "liveDetailsPresent", "publishedAt"] if c in table_df.columns]
st.dataframe(table_df[cols_show].sort_values("viewCount", ascending=False), use_container_width=True)

# CSV export
csv = table_df.to_csv(index=False)
st.download_button("📥 Tải CSV", data=csv, file_name="meditation_videos_today.csv", mime="text/csv")

st.markdown("""
---
*Ghi chú: "Monetizable" là proxy (video có >=1000 views). RPM là ước tính dựa trên lượt xem.*
""")
