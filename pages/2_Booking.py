import streamlit as st
from datetime import datetime, timedelta
from src.db import get_all_rooms, get_all_room_types, create_booking
from src.models import Booking, BookingType, RoomStatus, BookingStatus
from src.logic import calculate_estimated_price
from src.ui import apply_sidebar_style, create_custom_sidebar_menu

st.set_page_config(page_title="Đặt phòng", layout="wide")

from src.ui import require_login
require_login()

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

    
    # Grid Layout for Input Form
    with st.container(border=True):
        col_main, col_pay = st.columns([2, 1], gap="medium")

        with col_main:
            # Row 1: Guest Info & Room Selection (Compact)
            c1, c2 = st.columns(2, gap="small")
            
            with c1:
                st.caption("1. Thông tin khách")
                c_name = st.text_input("Họ tên khách (*)", key="c_name")
                c_phone = st.text_input("SĐT", key="c_phone")
                c_type = st.radio("Loại khách", ["Khách lẻ", "Khách đoàn"], horizontal=True, label_visibility="collapsed")
            
            with c2:
                st.caption("2. Chọn phòng")
                # Nếu đi từ Dashboard sang: chọn sẵn phòng
                prefill_room_id = st.session_state.pop("prefill_room_id", None)
                
                selected_rooms = [] 
                
                if c_type == "Khách đoàn":
                    default_val = [prefill_room_id] if (prefill_room_id and prefill_room_id in available_room_ids) else []
                    selected_rooms = st.multiselect("Chọn phòng", available_room_ids, default=default_val, label_visibility="collapsed", placeholder="Chọn nhiều phòng...")
                else:
                    default_index = 0
                    if prefill_room_id in available_room_ids:
                        default_index = available_room_ids.index(prefill_room_id)
                    
                    s_r = st.selectbox("Chọn phòng", available_room_ids, index=default_index, label_visibility="collapsed")
                    if s_r: selected_rooms = [s_r]
            
            if not selected_rooms:
                st.info("⬅️ Vui lòng chọn phòng.")
                st.stop()
            
            st.divider()
            
            # Row 2: Booking Details
            # Calculate pricing for the FIRST room to determine modes
            first_room_id = selected_rooms[0]
            r_obj = next((r for r in available_rooms if r['id'] == first_room_id), None)
            
            if r_obj:
                t_info = type_map.get(r_obj['room_type_code'], {})
                pricing = t_info.get('pricing', {})
                allowed_modes = []
                if pricing.get('enable_hourly', True): allowed_modes.append(BookingType.HOURLY)
                if pricing.get('enable_overnight', True): allowed_modes.append(BookingType.OVERNIGHT)
                if pricing.get('enable_daily', True): allowed_modes.append(BookingType.DAILY)
                
                if not allowed_modes:
                    st.error(f"Phòng {first_room_id} chưa được cấu hình giá!")
                    st.stop()
            
            c3, c4 = st.columns([1, 2], gap="small")
            with c3:
                st.caption("Hình thức thuê")
                booking_mode = st.selectbox("Mode", allowed_modes, format_func=lambda x: x.value, label_visibility="collapsed")
            
            with c4:
                # Time selection - Compact
                frozen_now = st.session_state["current_checkin_time"]
                
                # Logic giờ vào mặc định
                default_in_val = frozen_now.time()
                if booking_mode == BookingType.DAILY:
                    default_in_val = datetime.strptime("14:00", "%H:%M").time()

                # Row 1: Check-in
                cc1, cc2, cc3, cc4 = st.columns(4, gap="small")
                cc1.caption("Check-in")
                in_date = cc2.date_input("Ngày vào", value=frozen_now.date(), format="DD/MM/YYYY", label_visibility="collapsed")
                in_time = cc3.time_input("Giờ vào", value=default_in_val, step=60, label_visibility="collapsed")
                check_in_time = datetime.combine(in_date, in_time)

                # Logic tính giờ ra
                if booking_mode == BookingType.HOURLY:
                    default_out = check_in_time + timedelta(hours=2)
                elif booking_mode == BookingType.OVERNIGHT:
                    tomorrow = check_in_time + timedelta(days=1)
                    default_out = tomorrow.replace(hour=12, minute=0, second=0)
                else: 
                    tomorrow = check_in_time + timedelta(days=1)
                    default_out = tomorrow.replace(hour=12, minute=0, second=0)

                # Row 2: Check-out
                cc1.caption("Check-out")
                out_date = cc2.date_input("Ngày ra", value=default_out.date(), format="DD/MM/YYYY", label_visibility="collapsed")
                out_time = cc3.time_input("Giờ ra", value=default_out.time(), step=60, label_visibility="collapsed")
                check_out_time = datetime.combine(out_date, out_time)

        with col_pay:
            st.caption("3. Xác nhận & Thanh toán")
            
            # Logic tính tiền (Tổng các phòng)
            total_est_price = 0
            details_text = []

            for rid in selected_rooms:
                ro = next((r for r in available_rooms if r['id'] == rid), None)
                if ro:
                    ti = type_map.get(ro['room_type_code'], {})
                    price_cfg = get_applicable_price_config(check_in_time.date(), ti, system_config)
                    p = calculate_estimated_price(check_in_time, check_out_time, booking_mode, price_cfg)
                    total_est_price += p
                    details_text.append(f"- {rid}: {p:,.0f} đ")
            
            # Show breakdown if multiple
            if len(selected_rooms) > 1:
                 with st.expander(f"Chi tiết {len(selected_rooms)} phòng"):
                     for l in details_text: st.write(l)

            # Debug info (optional)
            if selected_rooms:
                first_ro = next((r for r in available_rooms if r['id'] == selected_rooms[0]), None)
                if first_ro:
                    first_ti = type_map.get(first_ro['room_type_code'], {})
                    first_pricing = get_applicable_price_config(check_in_time.date(), first_ti, system_config)
                    if first_pricing != first_ti.get('pricing', {}):
                         st.caption("ℹ️ Đang áp dụng giá đặc biệt")

            st.metric("Tổng tạm tính", f"{total_est_price:,.0f} đ")
            deposit = st.number_input("Tiền cọc", step=50000, format="%d", label_visibility="collapsed", placeholder="Tiền cọc")

            st.write("")
            is_checkin_now = st.checkbox("Check-in ngay?", value=True)
            btn_label = "✅ CHECK-IN" if is_checkin_now else "💾 LƯU"
            
            if st.button(btn_label, type="primary", use_container_width=True):
                if not c_name:
                    st.error("Thiếu tên khách!")
                elif check_out_time <= check_in_time:
                    st.error("Giờ ra sai!")
                else:
                    # Loop create bookings
                    success_count = 0
                    created_ids = []
                    
                    # Split deposit per room? Or assign to first? 
                    # Let's split evenly or assign to first. Simpler: Assign to first room, others 0?
                    # A better way: Store verify deposit for the Group? 
                    # For now: Avg deposit per room to keep data simple
                    avg_deposit = deposit / len(selected_rooms) if selected_rooms else 0

                    for rid in selected_rooms:
                        # Recalculate price for specific room (just to be safe)
                        ro = next((r for r in available_rooms if r['id'] == rid), None)
                        if ro:
                            ti = type_map.get(ro['room_type_code'], {})
                            price_cfg = get_applicable_price_config(check_in_time.date(), ti, system_config)
                            p_room = calculate_estimated_price(check_in_time, check_out_time, booking_mode, price_cfg)
                            
                            new_bk = Booking(
                                room_id=rid,
                                customer_name=c_name,
                                customer_phone=c_phone,
                                customer_type=c_type,
                                booking_type=booking_mode,
                                check_in=check_in_time,
                                check_out_expected=check_out_time,
                                price_original=p_room,
                                deposit=avg_deposit # Split deposit
                            )
                            suc, rez_id = create_booking(new_bk, is_checkin_now)
                            if suc:
                                success_count += 1
                                created_ids.append(rez_id)
                    
                    if success_count == len(selected_rooms):
                        # Success All
                        # Show summary bill for ALL
                        
                        st.session_state["booking_success_data"] = {
                            "booking_id": ", ".join(created_ids),
                            "room_id": ", ".join(selected_rooms),
                            "customer_name": c_name,
                            "customer_phone": c_phone,
                            "booking_type": booking_mode.value,
                            "check_in": check_in_time,
                            "check_out": check_out_time,
                            "price": total_est_price,
                            "deposit": deposit,
                            "status_text": "Đã nhận phòng" if is_checkin_now else "Đặt trước"
                        }
                        st.rerun()
                    else:
                        st.error(f"Có lỗi xảy ra! Chỉ tạo được {success_count}/{len(selected_rooms)} phòng.")