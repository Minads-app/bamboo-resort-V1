import streamlit as st
from datetime import datetime, timedelta
from src.db import get_all_rooms, get_all_room_types, create_booking, get_db, find_customer_by_phone
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
    from src.db import get_system_config
    system_config = get_system_config("special_days")
except Exception as e:
    # st.error(f"Lỗi tải config: {e}") # Có thể uncomment để debug
    print(f"Error loading system config: {e}")
    system_config = {}

# Import hàm mới
from src.logic import get_applicable_price_config

# Hàm reset để quay lại màn hình đặt phòng
def reset_page():
    st.session_state["booking_success_data"] = None
    if "current_checkin_time" in st.session_state:
        st.session_state["current_checkin_time"] = datetime.now()
    st.rerun()

def check_customer_phone():
    """Callback khi nhập SĐT"""
    phone = st.session_state.get("c_phone", "")
    if phone and len(phone.strip()) >= 3:
        info = find_customer_by_phone(phone)
        if info:
             st.session_state["c_name"] = info["customer_name"]
             # Có thể fill thêm loại khách nếu muốn
             # if info.get("customer_type"):
             #    st.session_state["c_type"] = info["customer_type"]
             st.toast(f"Đã tìm thấy khách cũ: {info['customer_name']}", icon="👤")

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

# Reset time logic
if "current_checkin_time" not in st.session_state:
    st.session_state["current_checkin_time"] = datetime.now()

try:
    # Lấy dữ liệu
    rooms = get_all_rooms()
    room_types = get_all_room_types()
    type_map = {t['type_code']: t for t in room_types}

    # Lọc phòng trống
    available_rooms = [r for r in rooms if r.get('status') == RoomStatus.AVAILABLE]
    
    # Fallback cho trường hợp status lưu dạng string
    if not available_rooms and rooms:
        available_rooms = [r for r in rooms if str(r.get('status')) == str(RoomStatus.AVAILABLE) or str(r.get('status')) == "AVAILABLE" or r.get('status') == 'available']

    available_room_ids = [r['id'] for r in available_rooms]

except Exception as e:
    st.error(f"Lỗi tải dữ liệu: {e}")
    st.stop()

if not available_rooms:
    st.warning("⚠️ Hết phòng trống!")
    if st.button("Tải lại"): st.rerun()
    st.stop()

    
# Grid Layout for Input Form
with st.container(border=True):
    col_main, col_pay = st.columns([2, 1], gap="small")

    with col_main:
        # Chia cột bên trái thành 2 cột con: Cột 1 (Khách + Thời gian) | Cột 2 (Chọn phòng + Thông tin)
        c1, c2 = st.columns(2, gap="small")
        
        # --- CỘT 1: THÔNG TIN KHÁCH & THỜI GIAN ---
        with c1:
            st.caption("1. Thông tin khách")
            c_name = st.text_input("Họ tên khách (*)", key="c_name")
            c_phone = st.text_input("Số điện thoại (*)", key="c_phone", on_change=check_customer_phone)
            
            # Gộp loại khách và hình thức thuê chung 1 hàng để tiết kiệm chỗ
            cc_type, cc_mode = st.columns(2, gap="small")
            with cc_type:
                c_type = st.radio("Loại khách", ["Khách lẻ", "Khách đoàn"], horizontal=True, label_visibility="collapsed")
            
            with cc_mode:
                # Logic xác định mode dựa trên cấu hình các loại phòng
                # Chỉ hiện các mode mà ít nhất 1 loại phòng hỗ trợ
                allowed_modes_all = set()
                for t in room_types:
                     p = t.get('pricing', {})
                     if p.get('enable_hourly', True): allowed_modes_all.add(BookingType.HOURLY)
                     if p.get('enable_overnight', True): allowed_modes_all.add(BookingType.OVERNIGHT)
                     if p.get('enable_daily', True): allowed_modes_all.add(BookingType.DAILY)
                
                # Sort modes for consistent order
                mode_order = [BookingType.HOURLY, BookingType.OVERNIGHT, BookingType.DAILY]
                final_modes = [m for m in mode_order if m in allowed_modes_all]
                if not final_modes: final_modes = [BookingType.HOURLY] # Fallback

                booking_mode = st.selectbox("Hình thức thuê", final_modes, format_func=lambda x: x.value)

            # Time Selection Logic
            frozen_now = st.session_state["current_checkin_time"]
            
            # Helper to generate slots
            def _generate_time_slots(selected_date):
                 now = datetime.now()
                 today = now.date()
                 start_min = 0
                 
                 # Nếu là hôm nay, chỉ hiện giờ tương lai (làm tròn lên 15p)
                 if selected_date == today:
                     minutes_from_midnight = now.hour * 60 + now.minute
                     # Làm tròn lên mốc 15 phút tiếp theo
                     # VD: 10:01 -> 10:15, 10:14 -> 10:15, 10:15 -> 10:15? 
                     # Nếu muốn khách vào "ngay bây giờ" thì 10:05 vẫn có thể chọn 10:00?
                     # Yêu cầu: "nếu đặt phòng hôm nay thì các giờ trước thời điểm đặt phòng thì ẩn đi"
                     # Tức là 10:05 thì không được chọn 10:00. Min là 10:15.
                     remainder = minutes_from_midnight % 15
                     if remainder > 0:
                         minutes_from_midnight += (15 - remainder)
                     start_min = minutes_from_midnight
                
                 slots = []
                 for m in range(start_min, 24 * 60, 15):
                     from datetime import time as dtime
                     h = m // 60
                     min_ = m % 60
                     if h < 24:
                        slots.append(dtime(h, min_))
                 return slots

            # Layout Check-in/Check-out gọn trong 1 cột
            cc1, cc2 = st.columns(2, gap="small")
            with cc1:
                st.caption("Ngày nhận phòng")
                in_date = st.date_input("Ngày vào", value=frozen_now.date(), format="DD/MM/YYYY", label_visibility="collapsed", key="in_date")
                
                if booking_mode == BookingType.DAILY:
                     # Check-in 14:00
                     check_in_time = datetime.combine(in_date, datetime.strptime("14:00", "%H:%M").time())
                     st.info(f"🕒 {check_in_time.strftime('%H:%M')}")
                else:
                     # Hourly/Overnight: Selectbox 15 mins
                     slots = _generate_time_slots(in_date)
                     if not slots:
                         st.error("Hết giờ hôm nay!")
                         in_time_val = datetime.now().time() # Fallback
                     else:
                         # Default to nearest current time if in list, else first
                         in_time_val = slots[0]
                         
                     in_time = st.selectbox("Giờ vào", slots, format_func=lambda t: t.strftime("%H:%M"), label_visibility="collapsed")
                     check_in_time = datetime.combine(in_date, in_time)

            with cc2:
                st.caption("Ngày trả phòng")
                # Logic tính giờ ra mặc định
                if booking_mode == BookingType.HOURLY:
                    default_out = check_in_time + timedelta(hours=2)
                elif booking_mode == BookingType.OVERNIGHT:
                    tomorrow = check_in_time + timedelta(days=1)
                    default_out = tomorrow.replace(hour=12, minute=0, second=0)
                else: 
                    # DAILY
                    tomorrow = check_in_time + timedelta(days=1)
                    default_out = tomorrow.replace(hour=12, minute=0, second=0)
                
                if booking_mode == BookingType.DAILY:
                    out_date = st.date_input("Ngày ra", value=default_out.date(), format="DD/MM/YYYY", label_visibility="collapsed", key="out_date")
                    # Check-out 12:00
                    check_out_time = datetime.combine(out_date, datetime.strptime("12:00", "%H:%M").time())
                    st.info(f"🕒 {check_out_time.strftime('%H:%M')}")
                else:
                    out_date = st.date_input("Ngày ra", value=default_out.date(), format="DD/MM/YYYY", label_visibility="collapsed", key="out_date")
                    # Out time cũng nên step 15p? Hay free text?
                    # Để đồng bộ, cho free step 15p
                    # time_input mặc định step 15p (900s)
                    out_time = st.time_input("Giờ ra", value=default_out.time(), step=900, label_visibility="collapsed", key="out_time")
                    check_out_time = datetime.combine(out_date, out_time)

        # --- CỘT 2: CHỌN PHÒNG & GIÁ ---
        with c2:
            st.caption("2. Chọn phòng")
            # Lấy room_id nếu được truyền từ Dashboard
            prefill_room_id = st.session_state.pop("prefill_room_id", None)

            # Filter rooms based on selected booking_mode
            compatible_room_ids = []
            for r in available_rooms:
                t = type_map.get(r['room_type_code'], {})
                p = t.get('pricing', {})
                
                is_compat = False
                if booking_mode == BookingType.HOURLY and p.get('enable_hourly', True): is_compat = True
                elif booking_mode == BookingType.OVERNIGHT and p.get('enable_overnight', True): is_compat = True
                elif booking_mode == BookingType.DAILY and p.get('enable_daily', True): is_compat = True
                
                if is_compat:
                    compatible_room_ids.append(r['id'])
            
            selected_rooms = []
            if c_type == "Khách đoàn":
                default_val = [prefill_room_id] if (prefill_room_id and prefill_room_id in compatible_room_ids) else []
                selected_rooms = st.multiselect("Chọn phòng", compatible_room_ids, default=default_val, label_visibility="collapsed", placeholder="Chọn nhiều phòng...")
            else:
                default_index = 0
                if prefill_room_id in compatible_room_ids:
                    default_index = compatible_room_ids.index(prefill_room_id)
                
                if compatible_room_ids:
                    s_r = st.selectbox("Chọn phòng", compatible_room_ids, index=default_index, label_visibility="collapsed")
                    if s_r: selected_rooms = [s_r]
                else:
                    st.warning(f"Không có phòng nào hỗ trợ hình thức {booking_mode.value}")

            # Hiển thị thông tin phòng theo Mode
            if selected_rooms and len(selected_rooms) == 1:
                rid = selected_rooms[0]
                r_obj = next((r for r in available_rooms if r['id'] == rid), None)
                if r_obj:
                    t_info = type_map.get(r_obj['room_type_code'], {})
                    p_info = t_info.get('pricing', {})
                    
                    # --- LOGIC HIỂN THỊ GIÁ DYNAMIC ---
                    price_html = ""
                    if booking_mode == BookingType.OVERNIGHT:
                         price_html = f'<div style="display: flex; justify-content: space-between;"><span>Qua đêm:</span> <b>{p_info.get("overnight_price", 0):,.0f}</b></div>'
                    elif booking_mode == BookingType.DAILY:
                         price_html = f'<div style="display: flex; justify-content: space-between;"><span>Theo ngày:</span> <b>{p_info.get("daily_price", 0):,.0f}</b></div>'
                    elif booking_mode == BookingType.HOURLY:
                         h_price = p_info.get('hourly_blocks', {}).get('1', 0)
                         price_html = f'<div style="display: flex; justify-content: space-between;"><span>Theo giờ (1h):</span> <b>{h_price:,.0f}</b></div>'

                    st.markdown(f"""
                    <div class="room-info-card">
                        <div class="room-info-header">ℹ️ {t_info.get('name', 'Phòng')} ({rid})</div>
                        <div class="room-info-price">
                            {price_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        if not selected_rooms:
            st.info("⬅️ Vui lòng chọn phòng.")
            st.stop()
        
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
        deposit = st.number_input("Tiền cọc", step=50000, format="%d")

        # st.write("")
        is_checkin_now = st.checkbox("Check-in ngay?", value=True)
        btn_label = "✅ CHECK-IN" if is_checkin_now else "💾 LƯU"
        
        if st.button(btn_label, type="primary", use_container_width=True):
            if not c_name:
                st.error("Thiếu tên khách!")
            elif not c_phone:
                st.error("Thiếu số điện thoại!")
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