import streamlit as st
from utils.youtube_api import (
    set_api_key, search_meditation_videos_today, get_stats_summary
)

st.set_page_config(page_title="YouTube Meditation Analyzer PRO", layout="wide")

st.title("🧘 YouTube Meditation Analyzer PRO")

# Kiểm tra API Key
if "YOUTUBE_API_KEY" not in st.session_state:
    st.warning("🔑 Bạn chưa nhập YouTube API Key.")
    with st.form("api_key_form"):
        api_key_input = st.text_input("Nhập YouTube API Key:", type="password")
        submitted = st.form_submit_button("Lưu API Key")
        if submitted:
            if api_key_input.strip():
                set_api_key(api_key_input.strip())
                st.success("✅ API Key đã được lưu! Hãy bấm 'Run' để tiếp tục.")
                st.experimental_rerun()
            else:
                st.error("❌ API Key không hợp lệ. Vui lòng nhập lại.")
else:
    # Khi đã có API key thì chạy tìm kiếm video
    st.success("✅ API Key đã sẵn sàng.")

    with st.spinner("🔍 Đang tìm kiếm video meditation hôm nay..."):
        videos_df = search_meditation_videos_today()

    if videos_df is not None and not videos_df.empty:
        # Thống kê
        stats = get_stats_summary(videos_df)
        st.subheader("📊 Thống kê hôm nay")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tổng video hôm nay", stats["total_videos"])
        col2.metric("Tổng kênh hoạt động", stats["total_channels"])
        col3.metric("Video >1000 views nhanh nhất", stats["fastest_1k_title"])
        col4.metric("Video đang livestream", stats["total_livestreams"])

        # Hiển thị bảng chi tiết
        st.subheader("📋 Danh sách video hôm nay")
        st.dataframe(videos_df, use_container_width=True)

    else:
        st.info("📭 Không tìm thấy video meditation nào hôm nay.")
