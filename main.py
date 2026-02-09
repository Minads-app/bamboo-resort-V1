import streamlit as st
from datetime import date
from src.ui import apply_sidebar_style, create_custom_sidebar_menu
from src.db import get_all_rooms, get_all_bookings
from src.models import RoomStatus, BookingStatus

st.set_page_config(
    page_title="QUẢN LÝ PHÒNG KHÁCH SẠN The Bamboo Resort",
    page_icon="🎋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from src.ui import require_login
require_login()

# Áp dụng CSS cho sidebar và tạo custom menu
# Áp dụng CSS cho sidebar và tạo custom menu
apply_sidebar_style()
create_custom_sidebar_menu()

st.markdown("<h1 style='text-align: center; margin-bottom: 5px;'>🎋 QUẢN LÝ PHÒNG KHÁCH SẠN</h1>", unsafe_allow_html=True)

# --- 1. THỐNG KÊ NHANH ---
rooms = get_all_rooms()
total_rooms = len(rooms)
available_rooms = len([r for r in rooms if r.get("status") == RoomStatus.AVAILABLE])

bookings = get_all_bookings()
today = date.today()

# Xác định các booking "đặt trước hôm nay" (chưa nhận phòng)
reserved_status_values = {
    "Đã đặt",
    "Confirmed",
}
try:
    reserved_status_values.add(BookingStatus.CONFIRMED.value)
except Exception:
    pass

today_reserved = []
for b in bookings:
    status = b.get("status")
    if hasattr(status, "value"):
        status = status.value
    check_in = b.get("check_in")
    if status in reserved_status_values and check_in is not None:
        d = getattr(check_in, "date", lambda: None)()
        if d == today:
            today_reserved.append(b)

# Hiển thị Metric gọn hơn
st.markdown("""
<style>
div[data-testid="stMetricValue"] {
    font-size: 24px !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 14px !important;
}
</style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Tổng số phòng", total_rooms)
with col2:
    st.metric("Phòng đang trống", available_rooms)
with col3:
    st.metric("Khách đến hôm nay", len(today_reserved))

# --- 2. DANH SÁCH KHÁCH ĐẶT PHÒNG HÔM NAY ---
st.markdown("---")
st.markdown("##### 📅 Khách đặt phòng hôm nay")

if not today_reserved:
    st.info("Hôm nay chưa có khách đặt phòng trước.")
else:
    # Chuẩn hoá dữ liệu hiển thị
    rows = []
    for b in today_reserved:
        check_in = b.get("check_in")
        check_out = b.get("check_out_expected") or b.get("check_out")
        rows.append(
            {
                "Phòng": b.get("room_id", ""),
                "Khách": b.get("customer_name", ""),
                "SĐT": b.get("customer_phone", ""),
                "Check-in": check_in.strftime("%H:%M") if check_in else "",
                "Check-out": check_out.strftime("%H:%M") if check_out else "",
            }
        )

    try:
        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        for r in rows:
            st.write(
                f"**Phòng {r['Phòng']}** - {r['Khách']} ({r['SĐT']}) | "
                f"{r['Check-in']} → {r['Check-out']}"
            )

st.caption("MinAds Hotel Manager 1.0")