import streamlit as st
from datetime import date
from src.ui import apply_sidebar_style, create_custom_sidebar_menu
from src.db import get_all_rooms, get_all_bookings
from src.models import RoomStatus, BookingStatus

st.set_page_config(
    page_title="QUẢN LÝ PHÒNG KHÁCH SẠN The Bamboo Resort",
    page_icon="🎋",
    layout="wide"
)

from src.ui import require_login
require_login()

# Áp dụng CSS cho sidebar và tạo custom menu
apply_sidebar_style()
create_custom_sidebar_menu()

st.title("🎋 QUẢN LÝ PHÒNG KHÁCH SẠN The Bamboo Resort")

st.markdown("""
### Chào mừng trở lại!
Hệ thống quản lý đang chạy. Vui lòng chọn chức năng ở thanh bên trái (Sidebar).
""")

st.divider()

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

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Tổng số phòng", total_rooms)
with col2:
    st.metric("Phòng đang trống", available_rooms)
with col3:
    st.metric("Khách đặt phòng hôm nay", len(today_reserved))

st.markdown("---")

# --- 2. DANH SÁCH KHÁCH ĐẶT PHÒNG HÔM NAY ---
st.subheader("📅 Danh sách khách đặt phòng hôm nay")

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
                "Check-in dự kiến": check_in.strftime("%d/%m/%Y %H:%M") if check_in else "",
                "Check-out dự kiến": check_out.strftime("%d/%m/%Y %H:%M") if check_out else "",
            }
        )

    try:
        import pandas as pd

        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        for r in rows:
            st.write(
                f"**Phòng {r['Phòng']}** - {r['Khách']} ({r['SĐT']}) | "
                f"{r['Check-in dự kiến']} → {r['Check-out dự kiến']}"
            )

st.caption("Hệ thống đang: 🟢 Online | Powered by MinAds")