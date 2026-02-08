import streamlit as st
from datetime import datetime, timedelta
from src.db import get_all_rooms, get_all_room_types, create_booking
from src.models import Booking, BookingType, RoomStatus, BookingStatus
from src.logic import calculate_estimated_price
from src.ui import apply_sidebar_style, create_custom_sidebar_menu

st.set_page_config(page_title="Đặt phòng", layout="wide")
apply_sidebar_style()
create_custom_sidebar_menu()

# --- QUẢN LÝ STATE ---
# Biến này dùng để hiện màn hình "Thành công"
if "booking_success_data" not in st.session_state:
    st.session_state["booking_success_data"] = None

# Lấy cấu hình hệ thống (cho giá đặc biệt)
try:
    system_config = get_db().collection("config_system").document("special_days").get().to_dict() or {}
except:
    system_config = {}

# Import hàm mới
from src.logic import get_applicable_price_config

# Hàm reset để quay lại màn hình đặt phòng
def reset_page():
    st.session_state["booking_success_data"] = None
    if "current_checkin_time" in st.session_state:
        st.session_state["current_checkin_time"] = datetime.now()
    st.rerun()

# === MÀN HÌNH 1: KẾT QUẢ THÀNH CÔNG (HIỆN BILL) ===
if st.session_state["booking_success_data"]:
    data = st.session_state["booking_success_data"]
    
    st.balloons()
    st.title("✅ Đặt phòng thành công!")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.success(f"Mã đặt phòng: {data['booking_id']}")
        # Hiển thị dạng vé/bill
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border: 1px dashed #ccc;">
            <h3 style="text-align: center; color: #0068c9;">PHIẾU XÁC NHẬN</h3>
            <p><b>Phòng:</b> {data['room_id']}</p>
            <p><b>Khách hàng:</b> {data['customer_name']} ({data['customer_phone']})</p>
            <hr>
            <p><b>Loại thuê:</b> {data['booking_type']}</p>
            <p><b>Check-in:</b> {data['check_in'].strftime('%d/%m/%Y %H:%M')}</p>
            <p><b>Check-out (Dự kiến):</b> {data['check_out'].strftime('%d/%m/%Y %H:%M')}</p>
            <hr>
            <p><b>Tổng tiền dự kiến:</b> {data['price']:,.0f} đ</p>
            <p><b>Đã cọc:</b> {data['deposit']:,.0f} đ</p>
            <p><b>Trạng thái:</b> {data['status_text']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        if st.button("⬅️ Quay lại trang đặt phòng", type="primary"):
            reset_page()

    with c2:
        st.info("💡 Hướng dẫn:")
        st.write("- Nếu khách đã nhận phòng: Phòng sẽ chuyển màu **ĐỎ** trên sơ đồ.")
        st.write("- Nếu chỉ đặt trước: Phòng sẽ chuyển màu **CAM** và chưa hiện trong danh sách trả phòng.")
    
    st.stop() # Dừng code tại đây, không hiện form bên dưới

# === MÀN HÌNH 2: FORM ĐẶT PHÒNG ===

st.title("🛎️ Check-in / Đặt phòng")

# Reset time logic (giống bài trước)
if "current_checkin_time" not in st.session_state:
    st.session_state["current_checkin_time"] = datetime.now()

# Lấy dữ liệu
rooms = get_all_rooms()
room_types = get_all_room_types()
type_map = {t['type_code']: t for t in room_types}

# Lọc phòng trống
available_rooms = [r for r in rooms if r.get('status') == RoomStatus.AVAILABLE]
available_room_ids = [r['id'] for r in available_rooms]

if not available_rooms:
    st.warning("⚠️ Hết phòng trống!")
    if st.button("Tải lại"): st.rerun()
    st.stop()

with st.container(border=True):
    col_info, col_room, col_pay = st.columns([1.5, 1, 1])

    with col_info:
        st.subheader("1. Thông tin khách")
        c_name = st.text_input("Họ tên khách (*)")
        c_phone = st.text_input("Số điện thoại")
        c_type = st.radio("Loại khách", ["Khách lẻ", "Khách đoàn"], horizontal=True)

    with col_room:
        st.subheader("2. Chọn phòng")
        # Nếu đi từ Dashboard sang: chọn sẵn phòng
        prefill_room_id = st.session_state.pop("prefill_room_id", None)
        default_index = 0
        if prefill_room_id in available_room_ids:
            default_index = available_room_ids.index(prefill_room_id)
        selected_room_id = st.selectbox("Chọn phòng trống", available_room_ids, index=default_index)
        
        # Info phòng
        r_obj = next((r for r in available_rooms if r['id'] == selected_room_id), None)
        if r_obj:
            t_info = type_map.get(r_obj['room_type_code'], {})
            st.info(f"Phòng {selected_room_id} - {t_info.get('name', '')}")
            
            # Lọc booking mode
            st.info(f"Phòng {selected_room_id} - {t_info.get('name', '')}")
            
            # --- START NEW LOGIC: Lấy giá theo ngày ---
            # Mặc định lấy theo ngày hiện tại để hiển thị filter mode (chưa chọn ngày check-in chính thức thì lấy today)
            # Tuy nhiên, khi user đổi ngày check-in bên dưới, giá sẽ được tính lại chính xác trong hàm calculate
            # Ở đây chỉ cần lấy config chuẩn để filter mode
            pricing = t_info.get('pricing', {})
            # --- END NEW LOGIC ---

            allowed_modes = []
            allowed_modes = []
            if pricing.get('enable_hourly', True): allowed_modes.append(BookingType.HOURLY)
            if pricing.get('enable_overnight', True): allowed_modes.append(BookingType.OVERNIGHT)
            if pricing.get('enable_daily', True): allowed_modes.append(BookingType.DAILY)
            
            if not allowed_modes:
                st.error("Loại phòng này chưa được cấu hình cho phép đặt!")
                st.stop()
        
        booking_mode = st.selectbox("Hình thức thuê", allowed_modes, format_func=lambda x: x.value)

        # Time selection (Giữ nguyên logic cũ)
        frozen_now = st.session_state["current_checkin_time"]
        
        st.caption("Thời gian Check-in:")
        c1, c2 = st.columns(2)
        in_date = c1.date_input("Ngày vào", value=frozen_now.date(), format="DD/MM/YYYY")
        
        # Logic giờ vào mặc định
        default_in_val = frozen_now.time()
        if booking_mode == BookingType.DAILY:
            default_in_val = datetime.strptime("14:00", "%H:%M").time()

        in_time = c2.time_input("Giờ vào", value=default_in_val, step=60)
        check_in_time = datetime.combine(in_date, in_time)

        # Logic tính giờ ra
        if booking_mode == BookingType.HOURLY:
            default_out = check_in_time + timedelta(hours=2)
        elif booking_mode == BookingType.OVERNIGHT:
            tomorrow = check_in_time + timedelta(days=1)
            default_out = tomorrow.replace(hour=12, minute=0, second=0)
        else: 
            # Theo ngày: Trả 12h trưa hôm sau
            tomorrow = check_in_time + timedelta(days=1)
            default_out = tomorrow.replace(hour=12, minute=0, second=0)
            
        st.caption("Trả dự kiến:")
        c3, c4 = st.columns(2)
        out_date = c3.date_input("Ngày ra", value=default_out.date(), format="DD/MM/YYYY")
        out_time = c4.time_input("Giờ ra", value=default_out.time(), step=60)
        check_out_time = datetime.combine(out_date, out_time)

    with col_pay:
        st.subheader("3. Xác nhận")
        
        # Logic tính tiền
        # Logic tính tiền
        # Lấy giá áp dụng dựa trên ngày check-in thực tế
        effective_pricing = get_applicable_price_config(check_in_time.date(), t_info, system_config)
        
        est_price = calculate_estimated_price(check_in_time, check_out_time, booking_mode, effective_pricing)
        
        # Debug info (optional - có thể bỏ sau khi test)
        if effective_pricing != t_info.get('pricing', {}):
             st.caption("ℹ️ Đang áp dụng giá đặc biệt (Lễ/Tết hoặc Cuối tuần)")

        st.metric("Tạm tính", f"{est_price:,.0f} đ")
        deposit = st.number_input("Tiền cọc", step=50000, format="%d")

        st.markdown("---")
        
        # --- QUAN TRỌNG: CHECKBOX XÁC NHẬN ---
        # Mặc định là True (Nhận phòng luôn). Nếu bỏ chọn -> Đặt trước (Reserved)
        is_checkin_now = st.checkbox("Khách nhận phòng ngay?", value=True)
        
        btn_label = "✅ CHECK-IN & GIAO CHÌA KHÓA" if is_checkin_now else "💾 LƯU ĐẶT PHÒNG (KHÁCH CHƯA ĐẾN)"
        
        if st.button(btn_label, type="primary", use_container_width=True):
            if not c_name:
                st.error("Thiếu tên khách!")
            elif check_out_time <= check_in_time:
                st.error("Giờ ra sai!")
            else:
                # Tạo object
                new_bk = Booking(
                    room_id=selected_room_id,
                    customer_name=c_name,
                    customer_phone=c_phone,
                    customer_type=c_type,
                    booking_type=booking_mode,
                    check_in=check_in_time,
                    check_out_expected=check_out_time,
                    price_original=est_price,
                    deposit=deposit
                )
                
                # Gọi hàm create_booking mới
                success, result_id = create_booking(new_bk, is_checkin_now)
                
                if success:
                    # Lưu vào session để hiện màn hình bill
                    st.session_state["booking_success_data"] = {
                        "booking_id": result_id,
                        "room_id": selected_room_id,
                        "customer_name": c_name,
                        "customer_phone": c_phone,
                        "booking_type": booking_mode.value,
                        "check_in": check_in_time,
                        "check_out": check_out_time,
                        "price": est_price,
                        "deposit": deposit,
                        "status_text": "Đã nhận phòng" if is_checkin_now else "Đặt trước (Chưa đến)"
                    }
                    st.rerun() # Rerun để render phần IF bên trên
                else:
                    st.error(f"Lỗi: {result_id}")