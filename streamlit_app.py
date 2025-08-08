# streamlit_app.py
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from googleapiclient.errors import HttpError

from utils.youtube_api import final_pipeline

st.set_page_config(page_title="Meditation YouTube Analyzer — PRO", layout="wide")
st.title("🧘 Meditation YouTube Analyzer — PRO")
st.markdown(
    "Công cụ phân tích video **meditation** — tìm video hôm nay, livestream, thống kê kênh, RPM ước tính, grid full-width responsive."
)

# ------------------------- API key input (secrets preferred) -------------------------
def get_api_key_ui():
    # 1) session_state
    if "YOUTUBE_API_KEY" in st.session_state:
        return st.session_state["YOUTUBE_API_KEY"]
    # 2) Streamlit secrets
    if st.secrets and st.secrets.get("YOUTUBE_API_KEY"):
        st.session_state["YOUTUBE_API_KEY"] = st.secrets["YOUTUBE_API_KEY"]
        return st.session_state["YOUTUBE_API_KEY"]
    # 3) sidebar form
    with st.sidebar.expander("🔑 YouTube API Key (recommended: save in Secrets)"):
        with st.form("api_key_form"):
            key = st.text_input("YouTube API Key:", type="password")
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

# ------------------------- Sidebar controls -------------------------
st.sidebar.header("Bộ lọc & Cấu hình")
rpm_scale = st.sidebar.slider("Điều chỉnh hệ số RPM (tỷ lệ)", 0.2, 4.0, 1.0, 0.1)
cols_desktop = st.sidebar.selectbox("Số cột trên desktop (grid)", [3, 4, 5], index=1)

st.sidebar.subheader("Lọc nâng cao")
kw = st.sidebar.text_input("Từ khóa tiêu đề")
channel_q = st.sidebar.text_input("Tên kênh (partial)")
country_options_placeholder = ["All"]  # will populate after fetch
min_rpm = st.sidebar.number_input("RPM tối thiểu (USD)", 0.0, 100000.0, 0.0, 0.1)
only_monetizable = st.sidebar.checkbox("Chỉ video đủ điều kiện Monetization (>=1000 views)", False)

# ------------------------- Fetch data -------------------------
with st.spinner("🔍 Đang lấy dữ liệu từ YouTube..."):
    try:
        df = final_pipeline(api_key)
        # apply rpm scaling
        if not df.empty:
            df["estimatedRPM_USD"] = (df["estimatedRPM_USD"].fillna(0).astype(float) * rpm_scale).round(2)
    except HttpError as e:
        st.error("🚨 YouTube API trả về lỗi (có thể quotaExceeded). Kiểm tra API Key / quota.")
        st.exception(e)
        st.stop()
    except Exception as e:
        st.error("🚨 Lỗi khi lấy dữ liệu.")
        st.exception(e)
        st.stop()

if df.empty:
    st.info("Không tìm thấy video meditation hôm nay.")
    st.stop()

# populate country filter now
countries = sorted(df.get("country", pd.Series(["Unknown"])).fillna("Unknown").unique().tolist())
country = st.sidebar.selectbox("Quốc gia", ["All"] + countries, index=0)

# ------------------------- Apply filters -------------------------
df_display = df.copy()
if kw:
    df_display = df_display[df_display["title"].str.contains(kw, case=False, na=False)]
if channel_q:
    df_display = df_display[df_display["channelTitle"].str.contains(channel_q, case=False, na=False)]
if country and country != "All":
    df_display = df_display[df_display["country"] == country]
if min_rpm > 0:
    df_display = df_display[df_display["estimatedRPM_USD"] >= float(min_rpm)]
if only_monetizable:
    df_display = df_display[df_display["Monetizable"] == True]

# ------------------------- Top metrics -------------------------
st.markdown("### 📊 Tổng quan hôm nay")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📈 Tổng video hôm nay", len(df))
col2.metric("📣 Kênh hoạt động", df["channelId"].nunique())
videos_1k = df[df["viewCount"] >= 1000].sort_values("time_to_1k_h")  # smaller time_to_1k_h = faster
fastest_1k = videos_1k.iloc[0] if not videos_1k.empty else None
col3.metric("🔥 Video đạt 1000 views nhanh nhất", fastest_1k["title"] if fastest_1k is not None else "Chưa có")
col4.metric("🔴 Livestreams", int(df["liveDetailsPresent"].sum()))

# ------------------------- Featured top video card (detailed & attractive) -------------------------
st.markdown("### 🔥 Video đạt 1000 views nhanh nhất")
if fastest_1k is not None:
    r = fastest_1k
    # compute nice time strings
    published_at = pd.to_datetime(r["publishedAt"])
    published_str = published_at.strftime("%Y-%m-%d %H:%M UTC")
    time_to_1k_h = r.get("time_to_1k_h")
    time_to_1k_text = f"{time_to_1k_h} giờ" if time_to_1k_h is not None else "—"

    # short description trimmed
    desc = (r.get("description") or "")[:280].replace("\n", " ")
    html_top = f"""
    <div style="display:flex; gap:18px; align-items:flex-start; width:100%; margin-bottom:14px;">
      <a href="https://www.youtube.com/watch?v={r['videoId']}" target="_blank" style="flex:0 0 360px;">
        <img src="{r.get('thumbnail')}" style="width:360px; height:202px; object-fit:cover; border-radius:10px;"/>
      </a>
      <div style="flex:1;">
        <a href="https://www.youtube.com/watch?v={r['videoId']}" target="_blank" style="text-decoration:none;">
          <h2 style="margin:0;color:#1e88e5;">{r.get('title')}</h2>
        </a>
        <p style="margin:6px 0 4px 0; color:#666;">
          <a href="https://www.youtube.com/channel/{r.get('channelId')}" target="_blank" style="color:#333;text-decoration:none;font-weight:600;">{r.get('channelTitle')}</a>
          &nbsp;•&nbsp; {r.get('viewCount',0):,} views
          &nbsp;•&nbsp; {published_str}
        </p>
        <div style="margin:8px 0;">
          <span style="display:inline-block;background:#ff7043;color:white;padding:6px 10px;border-radius:8px;font-weight:700;margin-right:8px;">⏱ {time_to_1k_text} để đạt 1K</span>
          <span style="display:inline-block;background:#1976d2;color:white;padding:6px 10px;border-radius:8px;font-weight:600;">💰 ${r.get('estimatedRPM_USD',0):,.2f} (ước tính)</span>
        </div>
        <p style="color:#444;margin-top:6px;line-height:1.4;">{desc}{'...' if len(desc) >= 280 else ''}</p>
      </div>
    </div>
    """
    st.markdown(html_top, unsafe_allow_html=True)
else:
    st.info("Chưa có video nào đạt 1000 views hôm nay.")

# ------------------------- Chart: videos by hour -------------------------
st.subheader("📈 Phân bố video theo giờ đăng (UTC)")
df["publishedHour"] = pd.to_datetime(df["publishedAt"]).dt.hour
fig = px.histogram(df, x="publishedHour", nbins=24, labels={"publishedHour":"Giờ (UTC)"})
st.plotly_chart(fig, use_container_width=True)

# ------------------------- Grid full-width responsive -------------------------
st.subheader("📂 Tất cả video hôm nay (Grid)")
# CSS
st.markdown(
    f"""
    <style>
    .block-container{{padding:1rem 1.6rem 2rem 1.6rem;}}
    .video-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 18px;
      width: 100%;
    }}
    .video-card {{
      background: #fff;
      border-radius: 12px;
      overflow: hidden;
      border:1px solid #eee;
      box-shadow:0 6px 18px rgba(15,15,15,0.06);
      transition: transform .15s ease-in-out, box-shadow .15s ease-in-out;
    }}
    .video-card:hover{{transform:translateY(-6px);box-shadow:0 10px 30px rgba(15,15,15,0.12);}}
    .video-thumb{{width:100%;height:170px;object-fit:cover;display:block}}
    .card-body{{padding:12px 14px;font-family:Inter, Roboto, Arial, sans-serif}}
    .title{{font-weight:600;font-size:14px;color:#111;line-height:1.3;display:block;text-decoration:none}}
    .meta{{color:#666;font-size:13px;margin-top:8px}}
    .badge{{display:inline-block;padding:4px 8px;border-radius:10px;font-size:12px;background:#ff5252;color:#fff;margin-right:6px}}
    .rpm-badge{{display:inline-block;padding:4px 8px;border-radius:8px;font-size:12px;background:#1976d2;color:#fff;margin-left:6px}}
    </style>
    """,
    unsafe_allow_html=True,
)

def render_grid_html(df_grid: pd.DataFrame, cols: int = 4) -> str:
    html = '<div class="video-grid">'
    for _, r in df_grid.iterrows():
        vid = r.get("videoId")
        url = f"https://www.youtube.com/watch?v={vid}"
        thumb = r.get("thumbnail") or ""
        title = (r.get("title") or "")[:160]
        channel = r.get("channelTitle") or ""
        views = int(r.get("viewCount", 0))
        subs = int(r.get("subscriberCount", 0)) if not pd.isna(r.get("subscriberCount")) else 0
        rpm = float(r.get("estimatedRPM_USD", 0.0))
        monet = r.get("Monetizable", False)
        live = r.get("liveDetailsPresent", False)

        live_html = '<span class="badge">LIVE</span>' if live else ''
        monet_html = f'<span class="rpm-badge">${rpm:,.2f}</span>'

        html += f"""
        <div class="video-card">
          <a href="{url}" target="_blank"><img class="video-thumb" src="{thumb}" alt="thumb"/></a>
          <div class="card-body">
             <a class="title" href="{url}" target="_blank">{title}</a>
             <div class="meta">{live_html} {channel} — {views:,} views {monet_html}</div>
          </div>
        </div>
        """
    html += "</div>"
    return html

html = render_grid_html(df_display, cols=cols_desktop)
components.html(html, height=820, scrolling=True)

# ------------------------- Detailed table + CSV export -------------------------
st.subheader("🔎 Bảng chi tiết (có link tiêu đề)")
table_df = df_display.copy()
table_df["Title (link)"] = table_df.apply(lambda r: f"[{r['title'][:140]}](https://www.youtube.com/watch?v={r['videoId']})", axis=1)
cols_show = [c for c in ["Title (link)", "channelTitle", "viewCount", "subscriberCount", "channelVideoCount", "country", "Monetizable", "estimatedRPM_USD", "liveDetailsPresent", "publishedAt"] if c in table_df.columns]
st.dataframe(table_df[cols_show].sort_values("viewCount", ascending=False), use_container_width=True)

csv = table_df.to_csv(index=False)
st.download_button("📥 Tải CSV", data=csv, file_name="meditation_videos_today.csv", mime="text/csv")

st.markdown("---")
st.markdown("*Ghi chú: `Monetizable` là proxy (video có >=1000 views). RPM là ước lượng.*")
