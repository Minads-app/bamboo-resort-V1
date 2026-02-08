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
                st.markdown("**💰 Thiết lập Giá (VND)**")
                
                # Giá cơ bản
                p_daily = st.number_input("Giá ngày (24h)", value=int(d_p_daily), step=50000, format="%d")
                p_overnight = st.number_input("Giá qua đêm", value=int(d_p_overnight), step=50000, format="%d")
                
                # Giá theo giờ (Logic động)
                st.caption("Giá theo giờ (Block):")
                col_h1, col_h2, col_h3 = st.columns(3)
                h1 = col_h1.number_input("1 giờ đầu", value=int(d_h1), step=10000)
                h2 = col_h2.number_input("2 giờ đầu", value=int(d_h2), step=10000)
                h3 = col_h3.number_input("3 giờ đầu", value=int(d_h3), step=10000)
                h_next = st.number_input("Mỗi giờ tiếp theo (+)", value=int(d_h_next), step=5000)

                # --- NEW: CẤU HÌNH GIÁ LỄ/TẾT & CUỐI TUẦN ---
                st.markdown("---")
                st.markdown("**📅 Giá Lễ/Tết & Cuối tuần (Tùy chọn)**")
                
                # Hàm helper để tạo form nhập giá
                def price_input_block(prefix, default_config=None):
                    defaults = default_config or {}
                    en = st.checkbox(f"Kích hoạt giá riêng cho {prefix}", value=bool(defaults.get('daily_price') or defaults.get('overnight_price')))
                    if en:
                        d_p_daily_n = defaults.get('daily_price', d_p_daily)
                        d_p_overnight_n = defaults.get('overnight_price', d_p_overnight)
                        # Giả sử giá giờ không đổi hoặc đổi theo tỷ lệ (đơn giản hóa UI: chỉ đổi giá ngày/đêm)
                        
                        c1, c2 = st.columns(2)
                        p_d = c1.number_input(f"Giá ngày ({prefix})", value=int(d_p_daily_n), step=50000, key=f"{prefix}_daily")
                        p_o = c2.number_input(f"Giá đêm ({prefix})", value=int(d_p_overnight_n), step=50000, key=f"{prefix}_overnight")
                        return PriceConfig(
                            hourly_blocks={"1": h1, "2": h2, "3": h3, "4": h3 + h_next}, # Kế thừa block giờ cơ bản
                            daily_price=float(p_d),
                            overnight_price=float(p_o),
                            enable_hourly=en_hourly,
                            enable_overnight=en_overnight,
                            enable_daily=en_daily
                        )
                    return None

                tab_p_weekend, tab_p_holiday = st.tabs(["Cuối tuần", "Lễ/Tết"])
                
                with tab_p_weekend:
                    st.caption("Áp dụng cho ngày check-in thuộc danh sách 'Cuối tuần'.")
                    p_weekend_cfg = price_input_block("Weekend", edit_data.get('pricing_weekend') if is_edit_mode else None)
                
                with tab_p_holiday:
                    st.caption("Áp dụng cho ngày check-in thuộc danh sách 'Lễ/Tết'.")
                    p_holiday_cfg = price_input_block("Holiday", edit_data.get('pricing_holiday') if is_edit_mode else None)

                st.markdown("---")

                st.markdown("**⚙️ Cấu hình được phép đặt**")
                c_en1, c_en2, c_en3 = st.columns(3)
                en_hourly = c_en1.checkbox("Cho phép theo giờ", value=d_en_hourly)
                en_overnight = c_en2.checkbox("Cho phép qua đêm", value=d_en_overnight)
                en_daily = c_en3.checkbox("Cho phép theo ngày", value=d_en_daily)

                btn_label = "💾 Cập nhật" if is_edit_mode else "➕ Thêm Mới"
                submitted = st.form_submit_button(btn_label, type="primary", use_container_width=True)
                
                if submitted:
                    # Logic lưu (giữ nguyên, chỉ cần update lại thông báo logic)
                    if not r_code or not r_name:
                        st.error("Vui lòng nhập Mã và Tên phòng!")
                    else:
                        # ... (Logic tạo object Pricing & RoomType giữ nguyên) ... 
                        # Tạo object Pricing
                        pricing = PriceConfig(
                            hourly_blocks={
                                "1": h1, 
                                "2": h2, 
                                "3": h3, 
                                "4": h3 + h_next
                            }, 
                            overnight_price=float(p_overnight),
                            daily_price=float(p_daily),
                            enable_hourly=en_hourly,
                            enable_overnight=en_overnight,
                            enable_daily=en_daily
                        )
                        
                        new_type = RoomType(
                            type_code=r_code,
                            name=r_name,
                            default_adults=r_adults,
                            default_children=r_kids,
                            pricing=pricing,
                            pricing_weekend=p_weekend_cfg,
                            pricing_holiday=p_holiday_cfg
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
        
        with st.form("frm_add_holiday"):
            d_input = st.date_input("Chọn ngày Lễ (có thể chọn khoảng)", value=[], format="DD/MM/YYYY")
            if st.form_submit_button("Thêm ngày Lễ"):
                # Xử lý input range
                dates_to_add = []
                if isinstance(d_input, (list, tuple)):
                    if len(d_input) == 2:
                        start, end = d_input
                        delta = end - start
                        for i in range(delta.days + 1):
                            dates_to_add.append(start + timedelta(days=i))
                    elif len(d_input) == 1:
                        dates_to_add.append(d_input[0])
                else:
                    dates_to_add.append(d_input)
                
                count_added = 0
                for d in dates_to_add:
                    d_str = d.strftime("%Y-%m-%d")
                    if d_str not in current_holidays:
                        current_holidays.add(d_str)
                        count_added += 1
                
                if count_added > 0:
                    save_special_days()
                    st.success(f"Đã thêm {count_added} ngày Lễ.")
                    st.rerun()
                else:
                     st.warning("Ngày này đã có.")
        
        st.write("---")
        # Helper: Thêm lễ VN cơ bản
        st.write("---")
        # Helper: Thêm lễ VN cơ bản (2025-2027)
        if st.button("Thêm nhanh Lễ Tết VN (2025-2027)", use_container_width=True):
            holidays_list = []
            
            # 1. Dương lịch cố định (30/4, 1/5, 2/9, 1/1)
            years = [2025, 2026, 2027]
            fixed_dates = ["01-01", "04-30", "05-01", "09-02"]
            for y in years:
                for d in fixed_dates:
                    holidays_list.append(f"{y}-{d}")

            # 2. Âm lịch quy đổi (Giỗ tổ 10/3, Tết Nguyên Đán)
            # Dữ liệu hardcode cho chính xác (Nguồn: Lịch vạn niên)
            lunar_mapped = {
                2025: [
                    "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31", "2025-02-01", # Tết (29-mùng 4)
                    "2025-04-07" # Giỗ tổ (10/3 AL)
                ],
                2026: [
                    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", # Tết
                    "2026-04-26" # Giỗ tổ
                ],
                2027: [
                    "2027-02-05", "2027-02-06", "2027-02-07", "2027-02-08", "2027-02-09", # Tết
                    "2027-04-15" # Giỗ tổ
                ]
            }
            
            for y in years:
                if y in lunar_mapped:
                    holidays_list.extend(lunar_mapped[y])

            count = 0
            for h in holidays_list:
                if h not in current_holidays:
                    current_holidays.add(h)
                    count += 1
            
            save_special_days()
            st.success(f"Đã thêm {count} ngày Lễ/Tết vào danh sách!")
            st.rerun()
            
        st.divider()
        st.write(f"**Danh sách ({len(current_holidays)} ngày):**")
        sorted_holidays = sorted(list(current_holidays))
        
        if sorted_holidays:
            df_h = pd.DataFrame({"Ngày Lễ": sorted_holidays})
            # Convert sang DD/MM/YYYY
            df_h["Ngày hiển thị"] = pd.to_datetime(df_h["Ngày Lễ"]).dt.strftime("%d/%m/%Y")
            
            event_h = st.dataframe(
                df_h[["Ngày hiển thị"]], 
                on_select="rerun", 
                selection_mode="multi-row", 
                use_container_width=True,
                height=300
            )
            if len(event_h.selection.rows) > 0:
                if st.button("🗑️ Xóa ngày đã chọn (Lễ)", type="primary"):
                    rows_to_del = [sorted_holidays[i] for i in event_h.selection.rows]
                    for r in rows_to_del:
                        current_holidays.remove(r)
                    save_special_days()
                    st.rerun()

    # --- TAB 3: QUẢN LÝ DANH SÁCH PHÒNG ---
with tab_rooms:
    # Lấy danh sách loại phòng để nạp vào Selectbox
    all_types = get_all_room_types()
    if not all_types:
        st.warning("⚠️ Vui lòng tạo 'Loại phòng' bên Tab 1 trước!")
    else:
        # Tạo dictionary dạng {"STD": "Phòng Đơn", "VIP": "Phòng VIP"} để hiển thị cho đẹp
        type_options = {
            t["type_code"]: f"{t['name']} ({t['type_code']})" for t in all_types
        }

        c_add, c_view = st.columns([1, 2])

        # 1. Form thêm phòng
        with c_add:
            with st.form("frm_add_room"):
                st.subheader("➕ Thêm Phòng Mới")
                r_id = st.text_input("Số phòng", placeholder="101").strip()
                r_type_code = st.selectbox(
                    "Loại phòng",
                    options=list(type_options.keys()),
                    format_func=lambda x: type_options[x],
                )
                r_floor = st.number_input("Tầng", min_value=1, value=1)

                if st.form_submit_button("Lưu Phòng", type="primary"):
                    if r_id:
                        new_room = Room(
                            id=r_id,
                            room_type_code=r_type_code,
                            floor=r_floor,
                            status=RoomStatus.AVAILABLE,
                        )
                        save_room_to_db(new_room.to_dict())
                        st.toast(f"Đã thêm phòng {r_id}", icon="✅")
                        st.rerun()
                    else:
                        st.error("Chưa nhập số phòng!")

        # 2. Danh sách phòng hiện có
        with c_view:
            st.subheader("Danh sách Phòng")
            rooms = get_all_rooms()
            if rooms:
                # Chuyển thành DataFrame để hiển thị bảng
                df_rooms = pd.DataFrame(rooms)

                # Map mã loại phòng sang tên cho dễ đọc
                df_rooms["Loại"] = df_rooms["room_type_code"].map(
                    lambda x: type_options.get(x, x)
                )

                # Hiển thị bảng
                st.dataframe(
                    df_rooms[["id", "Loại", "floor", "status"]],
                    column_config={
                        "id": "Số Phòng",
                        "floor": "Tầng",
                        "status": "Trạng thái",
                    },
                    use_container_width=True,
                    hide_index=True,
                )

                # Xóa nhanh (Demo đơn giản)
                with st.expander("🗑️ Xóa phòng"):
                    del_id = st.selectbox(
                        "Chọn phòng cần xóa", [r["id"] for r in rooms]
                    )
                    if st.button("Xác nhận xóa"):
                        delete_room(del_id)
                        st.rerun()
            else:
                st.info("Chưa có phòng nào. Hãy thêm ở bên trái.")

# --- TAB 3: HỆ THỐNG & TÀI KHOẢN THANH TOÁN ---
with tab_system:
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