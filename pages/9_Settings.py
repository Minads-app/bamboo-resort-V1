import base64
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

# Nhớ import thêm save_room_to_db, get_all_rooms, delete_room ở đầu file
from src.db import (
    delete_room,
    delete_room_type,
    get_all_room_types,
    get_all_rooms,
    save_payment_config,
    save_room_to_db,
    save_room_type_to_db,
    get_payment_config,
    get_system_config,
    save_system_config,
)
from src.models import Room, RoomStatus, PriceConfig, RoomType
from src.ui import apply_sidebar_style, create_custom_sidebar_menu
from datetime import date, datetime, timedelta

st.set_page_config(page_title="Cấu hình hệ thống", layout="wide")
apply_sidebar_style()
create_custom_sidebar_menu()

st.title("⚙️ Cấu hình The Bamboo Resort")

# Sử dụng Tabs để phân chia khu vực quản lý
# Sử dụng Tabs để phân chia khu vực quản lý
tab_types, tab_special_days, tab_rooms, tab_system = st.tabs(
    ["🏨 Loại Phòng & Giá", "📅 Cấu hình Lễ/Tết & Cuối tuần", "🛏️ Danh sách Phòng", "🛠️ Hệ thống & Thanh toán"]
)

# --- TAB 1: QUẢN LÝ LOẠI PHÒNG ---
with tab_types:
    col_input, col_list = st.columns([1, 1.5])
    
    # 1. Form nhập liệu (Bên trái)
    with col_input:
        with st.container(border=True):
            # --- LOGIC EDIT ---
            if "edit_room_type" not in st.session_state:
                st.session_state["edit_room_type"] = None
            
            edit_data = st.session_state["edit_room_type"]
            is_edit_mode = edit_data is not None
            
            form_title = f"✏️ Sửa Loại Phòng: {edit_data['type_code']}" if is_edit_mode else "➕ Thêm Loại Phòng Mới"
            st.subheader(form_title)

            # Giá trị mặc định
            d_name = ""
            d_code = ""
            d_adults = 2
            d_kids = 0
            d_p_daily = 500000
            d_p_overnight = 300000
            d_h1 = 50000
            d_h2 = 90000
            d_h3 = 120000
            d_h_next = 20000
            d_en_hourly = True
            d_en_overnight = True
            d_en_daily = True
            
            if is_edit_mode:
                d_name = edit_data.get('name', '')
                d_code = edit_data.get('type_code', '')
                d_adults = edit_data.get('default_adults', 2)
                d_kids = edit_data.get('default_children', 0)
                
                pricing = edit_data.get('pricing', {})
                d_p_daily = pricing.get('daily_price', 500000)
                d_p_overnight = pricing.get('overnight_price', 300000)
                
                blocks = pricing.get('hourly_blocks', {})
                d_h1 = blocks.get('1', 50000)
                d_h2 = blocks.get('2', 90000)
                d_h3 = blocks.get('3', 120000)
                # Giả định block 4 = h3 + next
                h4 = blocks.get('4', d_h3 + 20000)
                d_h_next = h4 - d_h3 if h4 > d_h3 else 20000
                
                d_en_hourly = pricing.get('enable_hourly', True)
                d_en_overnight = pricing.get('enable_overnight', True)
                d_en_daily = pricing.get('enable_daily', True)
            
            with st.form("frm_room_type"):
                c1, c2 = st.columns(2)
                r_name = c1.text_input("Tên loại phòng", value=d_name, placeholder="VD: Phòng Đơn")
                # Nếu đang Edt thì disable nhập mã
                r_code = c2.text_input("Mã (ID)", value=d_code, placeholder="VD: STD", disabled=is_edit_mode).upper().strip()
                
                c3, c4 = st.columns(2)
                r_adults = c3.number_input("Người lớn mặc định", 1, 10, d_adults)
                r_kids = c4.number_input("Trẻ em mặc định", 0, 10, d_kids)
                
                st.markdown("---")
                st.markdown("##### 💰 Thiết lập Giá (VND)")

                # --- DATA PREPARATION ---
                # Load existing data or defaults
                p_norm = edit_data.get('pricing', {}) if is_edit_mode else {}
                p_week = edit_data.get('pricing_weekend', {}) if is_edit_mode else {}
                p_holi = edit_data.get('pricing_holiday', {}) if is_edit_mode else {}
                
                # Helpers to get default values for inputs
                # Normal defaults to standard values if empty
                def get_norm(key, default):
                    return int(p_norm.get(key, default))
                
                # Weekend/Holiday default to 0 if empty (implying "not set" or disabled)
                def get_extra(data, key):
                    return int(data.get(key, 0))

                # Hourly helpers
                def get_norm_block(h_key, default):
                    blocks = p_norm.get('hourly_blocks', {})
                    return int(blocks.get(h_key, default))

                def get_extra_block(data, h_key):
                    blocks = data.get('hourly_blocks', {})
                    return int(blocks.get(h_key, 0))

                # --- UI RENDERING ---
                
                # HEADERS for Columns (We'll repeat these or just set them once? User image implies headers above the inputs)
                # But since we have multiple sections, let's make a grid helper.
                
                def render_price_row(label, field_key, default_norm, is_block=False, block_key=None):
                    if label:
                        st.markdown(f"**{label}**")
                    c1, c2, c3 = st.columns(3)
                    
                    # Normal
                    with c1:
                        if is_block:
                            val_n = get_norm_block(block_key, default_norm)
                        else:
                            val_n = get_norm(field_key, default_norm)
                        v1 = st.number_input("Ngày thường", value=val_n, step=10000, key=f"n_{field_key}_{block_key}")

                    # Weekend
                    with c2:
                        if is_block:
                            val_w = get_extra_block(p_week, block_key)
                        else:
                            val_w = get_extra(p_week, field_key)
                        v2 = st.number_input("Cuối tuần", value=val_w, step=10000, key=f"w_{field_key}_{block_key}")

                    # Holiday
                    with c3:
                        if is_block:
                            val_h = get_extra_block(p_holi, block_key)
                        else:
                            val_h = get_extra(p_holi, field_key)
                        v3 = st.number_input("Lễ Tết", value=val_h, step=10000, key=f"h_{field_key}_{block_key}")
                    
                    return v1, v2, v3

                # 1. GIÁ NGÀY
                st.markdown("###### 1. Giá ngày (24h)")
                d1, d2, d3 = render_price_row("", "daily_price", 500000)
                
                # 2. GIÁ QUA ĐÊM
                st.markdown("###### 2. Qua đêm")
                o1, o2, o3 = render_price_row("", "overnight_price", 300000)

                # 3. THEO GIỜ
                st.markdown("###### 3. Theo giờ")
                
                # 1 giờ
                h1_n, h1_w, h1_h = render_price_row("1 giờ đầu", "hourly", 50000, True, "1")
                # 2 giờ
                h2_n, h2_w, h2_h = render_price_row("2 giờ đầu", "hourly", 90000, True, "2")
                # 3 giờ
                h3_n, h3_w, h3_h = render_price_row("3 giờ đầu", "hourly", 120000, True, "3")
                
                # Next hour
                # Note: Hourly blocks usually need specific logic for the "next" hour calculation if stored differently
                # In current logic, Block 4 is calculated.
                # Let's ask user for "Mỗi giờ tiếp theo".
                # To simplify, we store this as a separate variable or calc Block 4?
                # Logic cũ: h_next = h4 - h3.
                # Let's retrieve h_next from existing data.
                def get_next_val(data, h3_val):
                    blocks = data.get('hourly_blocks', {})
                    if '4' in blocks and '3' in blocks:
                        diff = int(blocks['4']) - int(blocks['3'])
                        return diff if diff > 0 else 20000
                    return 20000
                
                next_n = get_next_val(p_norm, get_norm_block("3", 120000))
                next_w = get_next_val(p_week, get_extra_block(p_week, "3"))
                next_h = get_next_val(p_holi, get_extra_block(p_holi, "3"))

                st.markdown("**Mỗi giờ tiếp theo (+)**")
                c_nx1, c_nx2, c_nx3 = st.columns(3)
                hn_result = c_nx1.number_input("Ngày thường (+)", value=next_n, step=5000, key="nx_n")
                hw_result = c_nx2.number_input("Cuối tuần (+)", value=next_w, step=5000, key="nx_w")
                hh_result = c_nx3.number_input("Lễ Tết (+)", value=next_h, step=5000, key="nx_h")

                st.markdown("---")
                st.markdown("**⚙️ Cấu hình được phép đặt**")
                c_en1, c_en2, c_en3 = st.columns(3)
                en_hourly = c_en1.checkbox("Cho phép theo giờ", value=d_en_hourly)
                en_overnight = c_en2.checkbox("Cho phép qua đêm", value=d_en_overnight)
                en_daily = c_en3.checkbox("Cho phép theo ngày", value=d_en_daily)

                btn_label = "💾 Cập nhật" if is_edit_mode else "➕ Thêm Mới"
                submitted = st.form_submit_button(btn_label, type="primary", use_container_width=True)
                
                if submitted:
                    if not r_code or not r_name:
                        st.error("Vui lòng nhập Mã và Tên phòng!")
                    else:
                        # Construct Pricing Objects Helper
                        def build_price_config(d, o, h1, h2, h3, h_next):
                            # Nếu tất cả bằng 0 -> Trả về None (để không lưu rác cho Weekend/Holiday)
                            if d == 0 and o == 0 and h1 == 0:
                                return None
                            
                            blocks = {
                                "1": h1, "2": h2, "3": h3,
                                "4": h3 + h_next
                            }
                            return PriceConfig(
                                hourly_blocks=blocks,
                                daily_price=float(d),
                                overnight_price=float(o),
                                enable_hourly=en_hourly,
                                enable_overnight=en_overnight,
                                enable_daily=en_daily
                            )

                        pricing_main = build_price_config(d1, o1, h1_n, h2_n, h3_n, hn_result)
                        # Fallback for main: Must not be None? Actually code expects main pricing.
                        # If user enters 0 for main, it might be an issue, but let's assume they enter valid data.
                        
                        pricing_weekend_obj = build_price_config(d2, o2, h1_w, h2_w, h3_w, hw_result)
                        pricing_holiday_obj = build_price_config(d3, o3, h1_h, h2_h, h3_h, hh_result)
                        
                        new_type = RoomType(
                            type_code=r_code,
                            name=r_name,
                            default_adults=r_adults,
                            default_children=r_kids,
                            pricing=pricing_main,
                            pricing_weekend=pricing_weekend_obj,
                            pricing_holiday=pricing_holiday_obj
                        )
                        
                        try:
                            # Chuyển đổi thành dict, xử lý exclude_none=True để không lưu null fields nếu muốn
                            # Nhưng hàm save_room_type_to_db nhận dict thuần
                            save_room_type_to_db(new_type.to_dict())
                            action = "Cập nhật" if is_edit_mode else "Thêm mới"
                            st.toast(f"✅ {action}: {r_name} thành công!", icon="🎉")
                            
                            # Reset edit state
                            st.session_state["edit_room_type"] = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi lưu vào Firestore: {e}")
            
            # Nút Hủy Edit (nằm ngoài form)
            if is_edit_mode:
                if st.button("❌ Hủy bỏ thay đổi", use_container_width=True):
                    st.session_state["edit_room_type"] = None
                    st.rerun()

    # 2. Danh sách hiển thị (Bên phải)
    with col_list:
        st.subheader("📋 Danh sách Loại phòng")
        
        # Lấy dữ liệu từ Firestore
        room_types_data = get_all_room_types()
        
        if room_types_data:
            for item in room_types_data:
                pricing = item.get('pricing', {})
                
                # Tạo Card hiển thị thông tin
                with st.expander(f"**{item['name']} ({item['type_code']})** - {pricing.get('daily_price', 0):,} đ/ngày"):
                    c_info, c_price = st.columns(2)
                    
                    with c_info:
                        st.write(f"👤 Người lớn: **{item['default_adults']}**")
                        st.write(f"👶 Trẻ em: **{item['default_children']}**")
                        
                        modes = []
                        if pricing.get('enable_hourly', True): modes.append("Giờ")
                        if pricing.get('enable_overnight', True): modes.append("Qua đêm")
                        if pricing.get('enable_daily', True): modes.append("Ngày")
                        st.caption(f"Cho phép: {', '.join(modes)}")
                    
                    with c_price:
                        st.write(f"🌙 Qua đêm: **{pricing.get('overnight_price', 0):,} đ**")
                        # Hiển thị giá giờ dạng chuỗi cho gọn
                        blocks = pricing.get('hourly_blocks', {})
                        st.write(f"⏱️ 1h: {blocks.get('1', 0):,} | 2h: {blocks.get('2', 0):,}")

                    st.write(f"⏱️ 1h: {blocks.get('1', 0):,} | 2h: {blocks.get('2', 0):,}")
 
                    # Nút Sửa & Xóa
                    c_edit, c_del = st.columns([1, 1])
                    with c_edit:
                         if st.button("✏️ Sửa", key=f"edit_{item['type_code']}", use_container_width=True):
                             st.session_state["edit_room_type"] = item
                             st.rerun()
                    
                    with c_del:
                        if st.button("🗑️ Xóa", key=f"del_{item['type_code']}", use_container_width=True):
                            delete_room_type(item['type_code'])
                            if st.session_state.get("edit_room_type", {}).get("type_code") == item['type_code']:
                                st.session_state["edit_room_type"] = None
                            st.rerun()
        else:
            st.info("Chưa có loại phòng nào. Hãy thêm ở cột bên trái.")

        # --- TAB 2: CẤU HÌNH NGÀY LỄ/TẾT & CUỐI TUẦN ---
with tab_special_days:
    col_weekend, col_holiday = st.columns(2)
    
    # Lấy config hiện tại
    try:
        special_days_cfg = get_system_config("special_days")
    except:
        special_days_cfg = {}
        
    # current_weekends = set(special_days_cfg.get("weekend_days", [])) # OLD LOGIC
    current_holidays = set(special_days_cfg.get("holidays", []))
    current_weekend_weekdays = special_days_cfg.get("weekend_weekdays", [5, 6]) # Default Sat(5), Sun(6)

    # Helper function lưu
    def save_special_days():
        cfg = {
            # "weekend_days": list(current_weekends), # OLD
            "weekend_weekdays": current_weekend_weekdays,
            "holidays": list(current_holidays)
        }
        save_system_config("special_days", cfg)
        st.toast("Đã lưu cấu hình ngày đặc biệt!", icon="💾")

    # 1. Cấu hình Cuối Tuần
    with col_weekend:
        st.subheader("📅 Định nghĩa Cuối Tuần")
        st.caption("Chọn các thứ trong tuần được tính là 'Cuối tuần' (áp dụng cho CẢ NĂM).")
        
        weekday_map = {
            0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 
            4: "Thứ 6", 5: "Thứ 7", 6: "Chủ Nhật"
        }
        
        # Multiselect
        selected_days = st.multiselect(
            "Chọn thứ:",
            options=list(weekday_map.keys()),
            format_func=lambda x: weekday_map[x],
            default=current_weekend_weekdays
        )
        
        if st.button("Lưu cấu hình Cuối tuần", type="primary"):
            current_weekend_weekdays = selected_days
            save_special_days()
            st.rerun()

        st.info(f"Đang áp dụng: {', '.join([weekday_map[d] for d in sorted(current_weekend_weekdays)])}")

    # 2. Cấu hình Ngày Lễ
    with col_holiday:
        st.subheader("🎉 Ngày Lễ / Tết")
        st.caption("Danh sách ngày được tính là 'Lễ/Tết' (áp dụng giá Holiday).")
        
        # Load notes
        current_notes = special_days_cfg.get("holiday_notes", {}) # Dict { "YYYY-MM-DD": "Note" }

        # Helper save expanded
        def save_special_days_extended():
            cfg = {
                "weekend_weekdays": current_weekend_weekdays,
                "holidays": list(current_holidays),
                "holiday_notes": current_notes
            }
            save_system_config("special_days", cfg)
            st.toast("Đã lưu cấu hình ngày đặc biệt!", icon="💾")

        # --- FORM THÊM NGÀY ---
        with st.container(border=True):
            st.write("###### ➕ Thêm Ngày Lễ")
            
            tab_single, tab_range, tab_auto = st.tabs(["Chọn Ngày Lẻ", "Chọn Khoảng Ngày", "Tự Động"])
            
            # MODE 1: CHỌN NGÀY LẺ
            with tab_single:
                with st.form("frm_single_day"):
                    st.caption("Chọn một ngày cụ thể (VD: Giỗ tổ 10/3).")
                    d_single = st.date_input("Chọn ngày", value=date.today(), format="DD/MM/YYYY")
                    note_single = st.text_input("Ghi chú (Tùy chọn)", placeholder="VD: Giỗ tổ Hùng Vương")
                    
                    if st.form_submit_button("Thêm Ngay"):
                        d_str = d_single.strftime("%Y-%m-%d")
                        if d_str not in current_holidays:
                            current_holidays.add(d_str)
                            if note_single:
                                current_notes[d_str] = note_single
                            save_special_days_extended()
                            st.rerun()
                        else:
                            st.warning("Ngày này đã có trong danh sách!")
                            # Update note nếu muốn?
                            if note_single:
                                current_notes[d_str] = note_single
                                save_special_days_extended()
                                st.rerun()

            # MODE 2: CHỌN KHOẢNG NGÀY
            with tab_range:
                with st.form("frm_range_day"):
                    st.caption("Chọn Bắt đầu & Kết thúc -> Thêm tất cả ngày ở giữa.")
                    c_start, c_end = st.columns(2)
                    d_start = c_start.date_input("Từ ngày", value=date.today(), format="DD/MM/YYYY")
                    d_end = c_end.date_input("Đến ngày", value=date.today() + timedelta(days=1), format="DD/MM/YYYY")
                    note_range = st.text_input("Ghi chú chung cho khoảng này", placeholder="VD: Nghỉ Tết Nguyên Đán")
                    
                    if st.form_submit_button("Thêm Khoảng"):
                        if d_end < d_start:
                            st.error("Ngày kết thúc phải sau ngày bắt đầu!")
                        else:
                            delta = d_end - d_start
                            added_count = 0
                            for i in range(delta.days + 1):
                                day = d_start + timedelta(days=i)
                                day_str = day.strftime("%Y-%m-%d")
                                current_holidays.add(day_str)
                                if note_range:
                                    current_notes[day_str] = note_range
                                added_count += 1
                            
                            save_special_days_extended()
                            st.success(f"Đã thêm {added_count} ngày vào danh sách!")
                            st.rerun()

            # MODE 3: TỰ ĐỘNG (VN)
            with tab_auto:
                st.caption("Thêm nhanh các ngày lễ cố định của Việt Nam.")
                if st.button("Thêm tự động (2025-2027)", use_container_width=True):
                    holidays_list = []
                    notes_map = {}
                    
                    # 1. Dương lịch
                    years = [2025, 2026, 2027]
                    fixed_dates = {
                        "01-01": "Tết Dương Lịch", 
                        "04-30": "Giải phóng MN", 
                        "05-01": "Quốc tế Lao động", 
                        "09-02": "Quốc khánh"
                    }
                    for y in years:
                        for d, n in fixed_dates.items():
                            full_d = f"{y}-{d}"
                            holidays_list.append(full_d)
                            notes_map[full_d] = n

                    # 2. Âm lịch (Hardcode)
                    lunar_mapped = {
                        2025: [
                            ("2025-01-28", "Tết Nguyên Đán"), ("2025-01-29", "Tết Nguyên Đán"), 
                            ("2025-01-30", "Tết Nguyên Đán"), ("2025-01-31", "Tết Nguyên Đán"), 
                            ("2025-02-01", "Tết Nguyên Đán"), ("2025-04-07", "Giỗ tổ Hùng Vương")
                        ],
                        2026: [
                            ("2026-02-16", "Tết Nguyên Đán"), ("2026-02-17", "Tết Nguyên Đán"),
                            ("2026-02-18", "Tết Nguyên Đán"), ("2026-02-19", "Tết Nguyên Đán"),
                            ("2026-02-20", "Tết Nguyên Đán"), ("2026-04-26", "Giỗ tổ Hùng Vương")
                        ],
                        2027: [
                            ("2027-02-05", "Tết Nguyên Đán"), ("2027-02-06", "Tết Nguyên Đán"),
                            ("2027-02-07", "Tết Nguyên Đán"), ("2027-02-08", "Tết Nguyên Đán"),
                            ("2027-02-09", "Tết Nguyên Đán"), ("2027-04-15", "Giỗ tổ Hùng Vương")
                        ]
                    }
                    
                    for y in years:
                        if y in lunar_mapped:
                            for d_str, note in lunar_mapped[y]:
                                holidays_list.append(d_str)
                                notes_map[d_str] = note

                    count = 0
                    for h in holidays_list:
                        if h not in current_holidays:
                            current_holidays.add(h)
                            current_notes[h] = notes_map.get(h, "")
                            count += 1
                        else:
                            # Update note nếu chưa có
                            if not current_notes.get(h):
                                current_notes[h] = notes_map.get(h, "")
                    
                    save_special_days_extended()
                    st.success(f"Đã thêm {count} ngày Lễ/Tết!")
                    st.rerun()

        # --- DANH SÁCH HIỂN THỊ ---
        st.divider()
        c_tit, c_act = st.columns([2, 1])
        c_tit.write(f"**Danh sách ({len(current_holidays)} ngày):**")
        
        if st.button("🗑️ Xóa TẤT CẢ", type="secondary"):
            current_holidays.clear()
            current_notes.clear()
            save_special_days_extended()
            st.rerun()

        sorted_holidays = sorted(list(current_holidays))
        
        if sorted_holidays:
            # Tạo DataFrame display
            data_display = []
            for d_str in sorted_holidays:
                data_display.append({
                    "Ngày Lễ": d_str,
                    "Ngày hiển thị": pd.to_datetime(d_str).strftime("%d/%m/%Y"),
                    "Ghi chú": current_notes.get(d_str, "")
                })
                
            df_h = pd.DataFrame(data_display)
            
            # Hiển thị bảng có tích chọn
            event_h = st.dataframe(
                df_h[["Ngày hiển thị", "Ghi chú"]], 
                on_select="rerun", 
                selection_mode="multi-row", 
                use_container_width=True,
                height=400
            )

            # Xử lý xóa
            if len(event_h.selection.rows) > 0:
                rows_to_del = [sorted_holidays[i] for i in event_h.selection.rows]
                st.info(f"Đang chọn {len(rows_to_del)} ngày để xóa.")
                
                if st.button("🗑️ Xóa ngày đã chọn", type="primary"):
                    for r in rows_to_del:
                        current_holidays.remove(r)
                        if r in current_notes:
                            del current_notes[r]
                    save_special_days_extended()
                    st.rerun()

    # --- TAB 3: QUẢN LÝ DANH SÁCH PHÒNG ---
with tab_rooms:
    # Lấy danh sách loại phòng để nạp vào Selectbox (Move up to be available for both)
    all_types = get_all_room_types()
    if not all_types:
        st.warning("⚠️ Vui lòng tạo 'Loại phòng' bên Tab 1 trước!")
    else:
        # Tạo dictionary map
        type_options = {t["type_code"]: f"{t['name']} ({t['type_code']})" for t in all_types}
        type_map_simple = {t["type_code"]: t["name"] for t in all_types}

        c_add, c_view = st.columns([1, 2])
        
        # --- STATE MANAGEMENT ---
        if "edit_room" not in st.session_state:
            st.session_state["edit_room"] = None
        
        edit_room_data = st.session_state["edit_room"]
        is_edit_room = edit_room_data is not None

        # 1. Form thêm/sửa phòng
        with c_add:
            with st.container(border=True):
                form_title = f"✏️ Sửa Phòng {edit_room_data['id']}" if is_edit_room else "➕ Thêm Phòng Mới"
                st.subheader(form_title)
                
                # Default values
                d_id = ""
                d_type = list(type_options.keys())[0] if type_options else ""
                d_floor = ""
                d_status = RoomStatus.AVAILABLE
                
                if is_edit_room:
                    d_id = edit_room_data["id"]
                    d_type = edit_room_data["room_type_code"]
                    d_floor = str(edit_room_data.get("floor", ""))
                
                with st.form("frm_room"):
                    # Nếu edit thì không cho sửa ID để tránh lỗi logic, hoặc phải handle delete old -> create new
                    # Đơn giản nhất: Disable ID khi edit
                    r_id = st.text_input("Số phòng", value=d_id, placeholder="101", disabled=is_edit_room).strip()
                    r_type_code = st.selectbox(
                        "Loại phòng",
                        options=list(type_options.keys()),
                        format_func=lambda x: type_options[x],
                        index=list(type_options.keys()).index(d_type) if d_type in type_options else 0
                    )
                    r_floor = st.text_input("Khu vực", value=d_floor, placeholder="VD: Tầng 1, Khu A...").strip()

                    btn_lbl = "💾 Cập nhật" if is_edit_room else "Lưu Phòng"
                    if st.form_submit_button(btn_lbl, type="primary"):
                        if r_id:
                            new_room = Room(
                                id=r_id,
                                room_type_code=r_type_code,
                                floor=r_floor or "Khu vực 1",
                                status=RoomStatus.AVAILABLE, # Khôi phục status mặc định hoặc giữ nguyên?
                                # Thực tế nếu edit, ta nên giữ nguyên status cũ trừ khi muốn reset
                            )
                            # Nếu đang edit, giữ status cũ
                            if is_edit_room:
                                new_room.status = edit_room_data.get("status", RoomStatus.AVAILABLE)
                                new_room.current_booking_id = edit_room_data.get("current_booking_id")
                                new_room.note = edit_room_data.get("note", "")

                            save_room_to_db(new_room.to_dict())
                            msg = "Cập nhật" if is_edit_room else "Thêm mới"
                            st.toast(f"✅ {msg} phòng {r_id} thành công!", icon="🎉")
                            st.session_state["edit_room"] = None
                            st.rerun()
                        else:
                            st.error("Chưa nhập số phòng!")
                
                if is_edit_room:
                    if st.button("❌ Hủy bỏ thay đổi", use_container_width=True):
                        st.session_state["edit_room"] = None
                        st.rerun()

        # 2. Danh sách phòng hiện có
        with c_view:
            st.subheader("📋 Danh sách Phòng")
            rooms = get_all_rooms()
            if rooms:
                # Header row
                h1, h2, h3, h4, h5 = st.columns([1, 1.5, 1.5, 1.5, 1.5])
                h1.markdown("**Phòng**")
                h2.markdown("**Loại**")
                h3.markdown("**Khu vực**")
                h4.markdown("**Trạng thái**")
                h5.markdown("**Thao tác**")
                st.divider()
                
                # Sort rooms by Area then ID
                rooms.sort(key=lambda x: (str(x.get("floor","")), x["id"]))

                for r in rooms:
                    c1, c2, c3, c4, c5 = st.columns([1, 1.5, 1.5, 1.5, 1.5])
                    c1.write(f"**{r['id']}**")
                    c2.write(type_map_simple.get(r['room_type_code'], r['room_type_code']))
                    c3.write(str(r.get('floor', '')))
                    
                    # Status coloring helper (reusing logic implicitly or simplified)
                    stt = r.get('status', RoomStatus.AVAILABLE)
                    color = "green" if stt == RoomStatus.AVAILABLE else "red" if stt == RoomStatus.OCCUPIED else "orange"
                    c4.markdown(f":{color}[{stt}]")
                    
                    # Actions
                    with c5:
                        b_edit, b_del = st.columns(2)
                        if b_edit.button("✏️", key=f"btn_edit_{r['id']}", help="Sửa thông tin"):
                            st.session_state["edit_room"] = r
                            st.rerun()
                        
                        if b_del.button("🗑️", key=f"btn_del_{r['id']}", help="Xóa phòng này"):
                            delete_room(r['id'])
                            if st.session_state.get("edit_room", {}).get("id") == r['id']:
                                st.session_state["edit_room"] = None
                            st.rerun()
                    st.markdown("---")
            else:
                st.info("Chưa có phòng nào. Hãy thêm ở bên trái.")

# --- TAB 3: HỆ THỐNG & TÀI KHOẢN THANH TOÁN ---
with tab_system:
    # 1. CẤU HÌNH THÔNG TIN ĐƠN VỊ
    st.subheader("🏢 Thông tin đơn vị")
    st.caption("Thông tin này sẽ hiển thị trên Header của trang Booking và trong các mẫu in ấn.")
    
    # Load config with specific key
    sys_conf = get_system_config("general_info") or {}
    
    with st.form("frm_sys_info"):
        c1, c2 = st.columns(2)
        hotel_name = c1.text_input("Tên đơn vị (Khách sạn/Resort)", value=sys_conf.get("hotel_name", "The Bamboo Resort"))
        biz_type = c2.selectbox(
            "Loại hình kinh doanh",
            options=["Resort", "Khách sạn", "Homestay", "Villa", "Nhà nghỉ", "Căn hộ dịch vụ"],
            index=["Resort", "Khách sạn", "Homestay", "Villa", "Nhà nghỉ", "Căn hộ dịch vụ"].index(sys_conf.get("business_type", "Resort")) if sys_conf.get("business_type") in ["Resort", "Khách sạn", "Homestay", "Villa", "Nhà nghỉ", "Căn hộ dịch vụ"] else 0
        )
        
        addr = st.text_input("Địa chỉ", value=sys_conf.get("address", ""))
        
        c3, c4, c5 = st.columns(3)
        phone = c3.text_input("Điện thoại", value=sys_conf.get("phone", ""))
        email = c4.text_input("Email", value=sys_conf.get("email", ""))
        website = c5.text_input("Website", value=sys_conf.get("website", ""))
        
        if st.form_submit_button("💾 Lưu thông tin đơn vị", type="primary"):
            new_conf = {
                "hotel_name": hotel_name,
                "business_type": biz_type,
                "address": addr,
                "phone": phone,
                "email": email,
                "website": website,
                # Giữ lại các field cũ nếu có (tránh ghi đè mất data holiday)
                "holidays": sys_conf.get("holidays", []),
                "holiday_notes": sys_conf.get("holiday_notes", {}),
                "weekend_weekdays": sys_conf.get("weekend_weekdays", [5, 6])
            }
            save_system_config(content=new_conf) # Hàm save_system_config mặc định lưu vào 'system' collection nếu ko chỉ định key? 
            # Kiểm tra lại hàm save_system_config trong db.py: def save_system_config(key="system", content={}): 
            # À, file db.py có vẻ dùng key="system" mặc định hoặc phải truyền.
            # Trong code cũ: save_system_config("special_days", cfg).
            # Vậy ở đây ta nên lưu vào key="general_info" hoặc update vào "system" chung?
            # Để đơn giản và tránh conflict với special_days, ta lưu vào "general_info".
            # Tuy nhiên, model SystemConfig đang gom hết. 
            # Tốt nhất là lưu vào key "general_info"
            save_system_config("general_info", new_conf)
            st.toast("Đã lưu thông tin đơn vị!", icon="🏢")
            st.rerun()

    st.divider()

    # 2. TÀI KHOẢN THANH TOÁN
    st.subheader("💳 Tài khoản thanh toán (Ngân hàng)")
    st.caption(
        "Khai báo thông tin tài khoản để in trên Bill và hiển thị QR khi khách thanh toán online."
    )

    # Lấy cấu hình hiện có
    current_cfg = get_payment_config()

    col_txt, col_qr = st.columns([1.2, 1])

    with col_txt:
        with st.form("frm_payment_config"):
            bank_name = st.text_input(
                "Ngân hàng",
                value=current_cfg.get("bank_name", ""),
                placeholder="VD: Vietcombank",
            )
            bank_id = st.text_input(
                "Mã ngân hàng (VietQR bankId/BIN)",
                value=current_cfg.get("bank_id", ""),
                placeholder="VD: 970436 (Vietcombank)",
            )
            account_name = st.text_input(
                "Tên chủ tài khoản",
                value=current_cfg.get("account_name", ""),
                placeholder="VD: CÔNG TY TNHH ...",
            )
            account_number = st.text_input(
                "Số tài khoản",
                value=current_cfg.get("account_number", ""),
                placeholder="VD: 0123456789",
            )
            note = st.text_area(
                "Ghi chú hiển thị trên Bill (tuỳ chọn)",
                value=current_cfg.get("note", ""),
                placeholder="VD: Nội dung chuyển khoản: Tên + SĐT khách",
            )

            submitted = st.form_submit_button(
                "💾 Lưu thông tin tài khoản", type="primary", use_container_width=True
            )

            if submitted:
                cfg = dict(
                    bank_name=bank_name.strip(),
                    bank_id=bank_id.strip(),
                    account_name=account_name.strip(),
                    account_number=account_number.strip(),
                    note=note.strip(),
                )
                try:
                    save_payment_config(cfg)
                    st.success("Đã lưu thông tin tài khoản thanh toán.")
                except Exception as e:
                    st.error(f"Lỗi khi lưu cấu hình: {e}")

    with col_qr:
        st.markdown("**Xem trước VietQR tự động**")
        st.caption(
            "Hệ thống sẽ tự tạo ảnh VietQR từ Mã ngân hàng (bankId/BIN) và Số tài khoản. Không cần upload ảnh QR."
        )

        cfg = get_payment_config() or {}
        bank_id_cfg = cfg.get("bank_id")
        acc_no_cfg = cfg.get("account_number")

        if bank_id_cfg and acc_no_cfg:
            qr_url = (
                f"https://img.vietqr.io/image/"
                f"{bank_id_cfg}-{acc_no_cfg}-compact2.png?"
                f"accountName={quote_plus(cfg.get('account_name',''))}&"
                f"addInfo={quote_plus(cfg.get('note','Thanh toan tien phong'))}"
            )
            st.image(qr_url, caption="VietQR được tạo tự động", use_column_width=True)
            st.code(qr_url, language="text")
        else:
            st.info(
                "Nhập Mã ngân hàng (VietQR bankId/BIN) và Số tài khoản ở bên trái để tạo QR tự động."
            )