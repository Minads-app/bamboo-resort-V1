import streamlit as st
from src.db import (
    get_all_rooms,
    get_all_room_types,
    check_in_reserved_room,
    get_booking_by_id,
    get_pending_online_bookings,
    get_confirmed_online_bookings,
    confirm_online_booking,
)
from src.models import RoomStatus
from src.ui import apply_sidebar_style, create_custom_sidebar_menu

st.set_page_config(page_title="Sơ đồ phòng", layout="wide")
apply_sidebar_style()
create_custom_sidebar_menu()

st.title("🏨 Sơ đồ phòng - The Bamboo Resort")

# --- 1. LẤY DỮ LIỆU ---
rooms = get_all_rooms()
types = get_all_room_types()
type_map = {t["type_code"]: t["name"] for t in types}

# --- 1b. BOOKING ONLINE CHỜ XÁC NHẬN & LỊCH SỬ ---
col_pending, col_history = st.columns(2)

with col_pending:
    pending_online = get_pending_online_bookings()
    if pending_online:
        with st.expander(
            f"📨 {len(pending_online)} booking online đang CHỜ xác nhận thanh toán",
            expanded=True,
        ):
            for b in pending_online:
                room_id = b.get("room_id", "")
                booking_id = b.get("id", "")

                st.markdown(
                    f"**Phòng {room_id}** - {b.get('customer_name','')} ({b.get('customer_phone','')})"
                )

                pay_type = b.get("online_payment_type", "")
                status_raw = b.get("online_payment_status", "pending")
                status_label = (
                    "Chưa upload chứng từ"
                    if status_raw == "pending"
                    else "Chờ lễ tân xác nhận"
                )

                st.caption(
                    f"Hình thức: {pay_type} | Trạng thái thanh toán: **{status_label}**"
                )
                check_in = b.get("check_in")
                check_out = b.get("check_out_expected")
                if check_in:
                    st.write(f"- Check-in: {check_in.strftime('%d/%m/%Y %H:%M')}")
                if check_out:
                    st.write(f"- Check-out dự kiến: {check_out.strftime('%d/%m/%Y %H:%M')}")

                # Hiển thị thumbnail hình chụp thanh toán (nếu có)
                img_b64 = b.get("payment_screenshot_b64")
                if img_b64:
                    import base64

                    st.write("Hình chụp thanh toán (thu nhỏ):")
                    st.image(
                        base64.b64decode(img_b64),
                        caption=b.get("payment_screenshot_name", ""),
                        width=260,
                    )
                    with st.expander("🔍 Xem ảnh kích thước lớn"):
                        st.image(
                            base64.b64decode(img_b64),
                            caption=b.get("payment_screenshot_name", ""),
                            use_column_width=True,
                        )

                # Nút xác nhận đã nhận tiền
                if status_raw != "confirmed" and booking_id:
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        clicked = st.button(
                            "✅ Xác nhận đã nhận tiền",
                            key=f"confirm_online_{booking_id}",
                            use_container_width=True,
                        )
                        if clicked:
                            ok, msg = confirm_online_booking(booking_id)
                            if ok:
                                st.success(
                                    "Đã xác nhận đã nhận tiền. Booking đã được cập nhật."
                                )
                                st.rerun()
                            else:
                                st.error(f"Lỗi khi xác nhận: {msg}")
                    with c2:
                        st.caption(
                            "Sau khi xác nhận, booking sẽ không còn trong danh sách chờ."
                        )

                st.markdown("---")

with col_history:
    confirmed_online = get_confirmed_online_bookings(limit=20)
    with st.expander(
        f"📁 Lịch sử booking online đã xác nhận ({len(confirmed_online)} gần nhất)",
        expanded=False,
    ):
        if not confirmed_online:
            st.caption("Chưa có booking online nào được xác nhận.")
        else:
            for b in confirmed_online:
                room_id = b.get("room_id", "")
                st.markdown(
                    f"**Phòng {room_id}** - {b.get('customer_name','')} ({b.get('customer_phone','')})"
                )
                check_in = b.get("check_in")
                if check_in:
                    st.caption(
                        f"Check-in dự kiến: {check_in.strftime('%d/%m/%Y %H:%M')}"
                    )

                img_b64 = b.get("payment_screenshot_b64")
                if img_b64:
                    import base64

                    st.image(
                        base64.b64decode(img_b64),
                        caption="Ảnh thanh toán (thu nhỏ)",
                        width=220,
                    )
                    with st.expander("🔍 Xem ảnh chi tiết", expanded=False):
                        st.image(
                            base64.b64decode(img_b64),
                            caption=b.get("payment_screenshot_name", ""),
                            use_column_width=True,
                        )

                st.markdown("---")

# Hàm helper để lấy màu sắc và icon dựa trên trạng thái
def get_status_style(status_str):
    # Map string status sang màu sắc và icon
    if status_str == RoomStatus.AVAILABLE:
        return "🟢", "#e6fffa", "border: 2px solid #4caf50;" # Xanh lá
    elif status_str == RoomStatus.RESERVED:
        return "🟠", "#fff3e0", "border: 2px solid #ff9800;" # Cam (Đặt trước)
    elif status_str == RoomStatus.PENDING_PAYMENT:
        return "💸", "#e0e7ff", "border: 2px solid #3b82f6;" # Xanh dương (Chờ thanh toán)
    elif status_str == RoomStatus.OCCUPIED:
        return "🔴", "#FF7DB0", "border: 2px solid #f44336;" # Đỏ (Đang ở)
    elif status_str == RoomStatus.DIRTY:
        return "🧹", "#fffbe6", "border: 2px solid #ffeb3b;" # Vàng (Dơ)
    elif status_str == RoomStatus.MAINTENANCE:
        return "🔧", "#f0f2f6", "border: 2px solid #9e9e9e;" # Xám (Bảo trì)
    else:
        return "❓", "#ffffff", "border: 2px solid #ccc;"

# --- 2. THANH CÔNG CỤ (FILTER, SEARCH & STATS) ---
col_filter, col_stats = st.columns([1.2, 2.8])

with col_filter:
    # Lấy danh sách tầng duy nhất
    floors = sorted(list(set([r["floor"] for r in rooms]))) if rooms else []
    filter_floor = st.multiselect("Lọc theo tầng", options=floors)

    st.markdown("**🔍 Tìm khách ĐẶT TRƯỚC**")
    search_text = st.text_input(
        "Nhập tên khách hoặc SĐT",
        placeholder="VD: An, 09...",
        key="search_reserved_guest",
    )

# Tính toán thống kê
total = len(rooms)
count_available = len([r for r in rooms if r.get("status") == RoomStatus.AVAILABLE])
count_occupied = len([r for r in rooms if r.get("status") == RoomStatus.OCCUPIED])
count_reserved = len([r for r in rooms if r.get("status") == RoomStatus.RESERVED])
count_dirty = len([r for r in rooms if r.get("status") == RoomStatus.DIRTY])

with col_stats:
    # Hiển thị metrics dạng ngang
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tổng phòng", total)
    c2.metric("Trống", count_available)
    c3.metric("Đang ở", count_occupied, delta_color="inverse")  # Màu đỏ
    c4.metric("Đặt trước", count_reserved)  # Màu cam
    c5.metric("Cần dọn", count_dirty)  # Màu vàng

    # Nếu có nhập search -> hiển thị kết quả nhanh
    if search_text.strip():
        q = search_text.strip().lower()
        reserved_rooms = [r for r in rooms if r.get("status") == RoomStatus.RESERVED]
        matched = []
        for r in reserved_rooms:
            bk_id = r.get("current_booking_id")
            if not bk_id:
                continue
            try:
                bk = get_booking_by_id(bk_id) or {}
            except Exception:
                bk = {}
            name = (bk.get("customer_name") or "").lower()
            phone = (bk.get("customer_phone") or "").lower()
            if q in name or q in phone:
                matched.append((r, bk))

        st.markdown("---")
        st.markdown("**Kết quả tìm khách đặt trước:**")
        if not matched:
            st.caption("Không tìm thấy khách phù hợp.")
        else:
            for r, bk in matched:
                st.markdown(
                    f"- Phòng **{r['id']}** – {bk.get('customer_name','')} ({bk.get('customer_phone','')})"
                )

st.markdown("---")

# --- 3. VẼ SƠ ĐỒ PHÒNG (GRID) ---
if rooms:
    # Sắp xếp phòng
    rooms.sort(key=lambda x: (x['floor'], x['id']))
    
    # Lọc phòng
    display_rooms = [r for r in rooms if not filter_floor or r['floor'] in filter_floor]

    # Custom CSS để hiển thị Card đẹp hơn
    st.markdown("""
    <style>
    .room-card {
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
        color: #333;
    }
    .room-id { font-weight: bold; font-size: 1.2em; }
    .room-type { font-size: 0.8em; color: #666; }
    </style>
    """, unsafe_allow_html=True)

    # Chia lưới: 6 phòng 1 hàng
    cols = st.columns(6)
    
    for i, room in enumerate(display_rooms):
        col = cols[i % 6]
        with col:
            status = room.get('status', RoomStatus.AVAILABLE)
            icon, bg_color, border_style = get_status_style(status)
            
            # Hiển thị Custom Card bằng HTML (để chỉnh màu nền chính xác hơn st.container)
            st.markdown(f"""
            <div class="room-card" style="background-color: {bg_color}; {border_style}">
                <div class="room-id">{room['id']}</div>
                <div class="room-type">{type_map.get(room['room_type_code'], room['room_type_code'])}</div>
                <div style="margin-top: 5px;">{icon} {status}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Nút thao tác nhanh dưới mỗi phòng
            with st.popover("Thao tác", use_container_width=True):
                st.write(f"**Phòng {room['id']}**")
                st.caption(f"Trạng thái: {status}")

                # Lấy thông tin booking (nếu phòng có current_booking_id)
                booking_info = None
                booking_id = room.get("current_booking_id")
                if booking_id:
                    try:
                        booking_info = get_booking_by_id(booking_id)
                    except Exception:
                        booking_info = None

                if status == RoomStatus.AVAILABLE:
                    # Cho phép đi thẳng sang trang Booking với phòng đã chọn
                    if st.button("🛎️ Booking", key=f"booking_{room['id']}", use_container_width=True):
                        st.session_state["prefill_room_id"] = room["id"]
                        try:
                            st.switch_page("pages/2_Booking.py")
                        except Exception:
                            st.info("Không chuyển trang được. Vui lòng chọn menu **Booking** ở sidebar.")

                elif status == RoomStatus.OCCUPIED:
                    # Xem thông tin khách đang ở
                    if booking_info:
                        with st.expander("👁 Xem thông tin khách đang ở", expanded=False):
                            st.write(f"**Khách:** {booking_info.get('customer_name', '')}")
                            st.write(f"**SĐT:** {booking_info.get('customer_phone', '')}")
                            st.write(f"**Check-in:** {booking_info.get('check_in').strftime('%d/%m/%Y %H:%M') if booking_info.get('check_in') else ''}")
                            st.write(f"**Dự kiến trả:** {booking_info.get('check_out_expected').strftime('%d/%m/%Y %H:%M') if booking_info.get('check_out_expected') else ''}")

                    st.warning("Bạn chắc chắn muốn Checkout?")
                    c_yes, c_no = st.columns(2)
                    with c_yes:
                        if st.button("✅ Có, Checkout", key=f"checkout_yes_{room['id']}", use_container_width=True):
                            # Chuyển sang trang Checkout, chọn sẵn phòng này
                            st.session_state["prefill_checkout_room_id"] = room["id"]
                            try:
                                st.switch_page("pages/3_Checkout.py")
                            except Exception:
                                st.info("Không chuyển trang được. Vui lòng chọn menu **Trả phòng** ở sidebar.")
                    with c_no:
                        st.button("❌ Không", key=f"checkout_no_{room['id']}", use_container_width=True)

                elif status == RoomStatus.RESERVED:
                    st.warning("Phòng đang **Đặt trước**.")

                    # Xem thông tin khách đặt
                    if booking_info:
                        with st.expander("👁 Xem thông tin khách đặt", expanded=False):
                            st.write(f"**Khách:** {booking_info.get('customer_name', '')}")
                            st.write(f"**SĐT:** {booking_info.get('customer_phone', '')}")
                            st.write(f"**Giờ dự kiến đến:** {booking_info.get('check_in').strftime('%d/%m/%Y %H:%M') if booking_info.get('check_in') else ''}")
                            st.write(f"**Giờ dự kiến trả:** {booking_info.get('check_out_expected').strftime('%d/%m/%Y %H:%M') if booking_info.get('check_out_expected') else ''}")

                    if st.button("✅ Check-in ngay", key=f"checkin_{room['id']}", type="primary", use_container_width=True):
                        ok, msg = check_in_reserved_room(room["id"])
                        if ok:
                            st.success(f"Đã check-in phòng {room['id']}! (Booking: {msg})")
                            st.rerun()
                        else:
                            st.error(f"Lỗi: {msg}")

                elif status == RoomStatus.DIRTY:
                    if st.button("🧹 Đã dọn xong", key=f"clean_{room['id']}", use_container_width=True):
                        from src.db import update_room_status
                        update_room_status(room['id'], RoomStatus.AVAILABLE)
                        st.rerun()

else:
    st.info("Chưa có dữ liệu phòng. Vui lòng vào trang Settings để tạo.")