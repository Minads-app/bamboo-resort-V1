import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

from src.models import ServiceItem, ServiceCategory, ServiceOrder, RoomStatus
from src.db import (
    get_all_services, save_service, delete_service,
    get_occupied_rooms, add_service_order, get_orders_by_booking,
    get_all_rooms # Để lấy tên phòng nếu cần
)
from src.ui import apply_sidebar_style, create_custom_sidebar_menu, require_login

# --- CONFIG & LAYOUT ---
st.set_page_config(page_title="Dịch vụ & Ăn uống", layout="wide")
require_login()
apply_sidebar_style()
create_custom_sidebar_menu()

st.title("🍽️ Dịch vụ phòng & Ăn uống")

# --- TABS ---
tab_order, tab_menu, tab_history = st.tabs(["🛒 Đặt món (Order)", "📋 Quản lý Menu", "📜 Lịch sử Order"])

# ---------------------------------------------------------
# TAB 1: ĐẶT MÓN (Cho nhân viên)
# ---------------------------------------------------------
with tab_order:
    c_left, c_right = st.columns([1, 2], gap="large")
    
    # 1. Chọn Phòng
    with c_left:
        st.subheader("1. Chọn Phòng")
        occupied = get_occupied_rooms() # Chỉ lấy phòng đang có khách
        if not occupied:
            st.warning("Hiện không có phòng nào đang có khách (Occupied).")
            selected_room = None
        else:
            # Format: "101 - Khu A"
            room_opts = {r['id']: f"{r['id']} - {r.get('floor','Unknown')}" for r in occupied}
            
            # State để giữ phòng đang chọn
            if "selected_room_id" not in st.session_state:
                st.session_state["selected_room_id"] = list(room_opts.keys())[0] if room_opts else None
                
            s_room_id = st.selectbox(
                "Chọn phòng cần gọi món:", 
                options=list(room_opts.keys()), 
                format_func=lambda x: room_opts[x],
                key="sel_room_order"
            )
            
            # Hiển thị thông tin booking
            if s_room_id:
                # Tìm booking id
                # Simple lookup from occupied list
                room_data = next((r for r in occupied if r['id'] == s_room_id), None)
                if room_data:
                    bk_id = room_data.get("current_booking_id")
                    st.info(f"Booking ID: `{bk_id}`")
                    st.session_state["current_ordering_bk_id"] = bk_id
    
    # 2. Chọn Món
    with c_right:
        st.subheader("2. Chọn Món/Dịch vụ")
        
        # Load Menu
        menu = get_all_services()
        if not menu:
            st.warning("Chưa có menu. Vui lòng sang tab 'Quản lý Menu' để thêm món.")
        else:
            # Filter category
            cats = [c.value for c in ServiceCategory]
            sel_cat = st.radio("Danh mục:", ["Tất cả"] + cats, horizontal=True)
            
            # Filter items
            filtered_menu = menu if sel_cat == "Tất cả" else [m for m in menu if m['category'] == sel_cat]
            
            if not filtered_menu:
                st.caption("Không có món nào trong danh mục này.")
            else:
                # Add to cart logic
                if "cart" not in st.session_state:
                    st.session_state["cart"] = {} # { item_id: {data, qty} }
                
                # Grid view for items
                for item in filtered_menu:
                    c1, c2, c3 = st.columns([3, 1.5, 1], gap="small")
                    c1.markdown(f"**{item['name']}** ({item['unit']})")
                    c2.markdown(f"{item['price']:,.0f} đ")
                    
                    if c3.button("➕", key=f"add_{item['id']}", help="Thêm vào giỏ"):
                        cart = st.session_state["cart"]
                        if item['id'] in cart:
                            cart[item['id']]['qty'] += 1
                        else:
                            cart[item['id']] = {
                                "id": item['id'],
                                "name": item['name'],
                                "price": item['price'],
                                "qty": 1
                            }
                        st.toast(f"Đã thêm {item['name']}", icon="🛒")
                    
                    st.divider() # Compact divider
            
            # 3. Giỏ hàng & Xác nhận
            with st.container(border=True):
                st.subheader("🛒 Giỏ hàng")
                cart = st.session_state.get("cart", {})
                
                if not cart:
                    st.caption("Chưa chọn món nào.")
                else:
                    total_order = 0
                    
                    # Display cart items
                    for iid, data in cart.items():
                        sub = data['price'] * data['qty']
                        total_order += sub
                        
                        cc1, cc2, cc3, cc4 = st.columns([3, 1.2, 1.5, 0.5], gap="small")
                        cc1.write(f"{data['name']}")
                        
                        # Qty adjuster
                        new_qty = cc2.number_input(
                            "SL", min_value=1, value=data['qty'], key=f"qty_{iid}", label_visibility="collapsed"
                        )
                        # Update qty if changed
                        if new_qty != data['qty']:
                            cart[iid]['qty'] = new_qty
                            st.rerun()

                        cc3.write(f"{sub:,.0f}")
                        
                        if cc4.button("x", key=f"del_cart_{iid}"):
                            del cart[iid]
                            st.rerun()
                    
                    st.divider()
                    st.markdown(f"### Tổng: :red[{total_order:,.0f} đ]")
                
                note = st.text_input("Ghi chú (Không cay, ít đá...)", key="order_note")
                
                if st.button("✅ Gửi Order / Báo Bếp", type="primary", use_container_width=True):
                    if not s_room_id:
                        st.error("Chưa chọn phòng!")
                    else:
                        # Construct Order Object
                        bk_id = st.session_state.get("current_ordering_bk_id")
                        
                        items_list = []
                        for iid, data in cart.items():
                            items_list.append({
                                "id": iid,
                                "name": data['name'],
                                "price": data['price'],
                                "qty": data['qty'],
                                "total": data['price'] * data['qty']
                            })
                        
                        new_order = ServiceOrder(
                            booking_id=bk_id,
                            room_id=s_room_id,
                            items=items_list,
                            total_value=total_order,
                            note=note
                        )
                        
                        add_service_order(new_order.to_dict())
                        st.success(f"Đã gọi món cho phòng {s_room_id} thành công!")
                        
                        # Clear cart
                        st.session_state["cart"] = {}
                        st.rerun()


# ---------------------------------------------------------
# TAB 2: QUẢN LÝ MENU (Admin/Manager)
# ---------------------------------------------------------
with tab_menu:
    # Check permisison (Optional: Manager/Admin only?)
    # For now allow all staff to edit menu for simplicity or restriction?
    # Let's restrict to Admin/Manager
    curr_user = st.session_state.get("user", {})
    if curr_user.get("role") not in ["admin", "manager"]:
        st.warning("🔒 Chỉ Quản lý mới được chỉnh sửa Menu.")
    else:
        cm_left, cm_right = st.columns([1, 2])
        
        # Form Add/Edit
        with cm_left:
            with st.container(border=True):
                st.subheader("➕ Thêm / Sửa Món")
                
                if "edit_service" not in st.session_state:
                    st.session_state["edit_service"] = None
                
                edit_sv = st.session_state["edit_service"]
                
                is_edit = edit_sv is not None
                
                # Defaults
                d_name = edit_sv['name'] if is_edit else ""
                d_cat = edit_sv['category'] if is_edit else ServiceCategory.DRINK
                d_price = edit_sv['price'] if is_edit else 30000.0
                d_unit = edit_sv['unit'] if is_edit else "ly"
                
                with st.form("frm_service"):
                    s_name = st.text_input("Tên món/Dịch vụ", value=d_name)
                    s_cat = st.selectbox(
                        "Danh mục", 
                        options=[c.value for c in ServiceCategory],
                        index=[c.value for c in ServiceCategory].index(d_cat) if isinstance(d_cat, str) else 0
                    )
                    
                    c_p, c_u = st.columns(2)
                    s_price = c_p.number_input("Giá bán", min_value=0.0, value=float(d_price), step=1000.0)
                    s_unit = c_u.text_input("Đơn vị", value=d_unit)
                    
                    btn_txt = "Cập nhật" if is_edit else "Thêm mới"
                    if st.form_submit_button(btn_txt, type="primary"):
                        if not s_name:
                            st.error("Tên không được để trống")
                        else:
                            sv_obj = ServiceItem(
                                id=edit_sv['id'] if is_edit else None,
                                name=s_name,
                                category=s_cat,
                                price=s_price,
                                unit=s_unit
                            )
                            save_service(sv_obj.to_dict())
                            st.toast(f"Đã lưu {s_name}!", icon="💾")
                            st.session_state["edit_service"] = None
                            st.rerun()
                
                if is_edit:
                    if st.button("Hủy sửa"):
                        st.session_state["edit_service"] = None
                        st.rerun()

        # List Menu
        with cm_right:
            st.subheader("📋 Danh sách Menu")
            full_menu = get_all_services()
            
            if full_menu:
                # Table style
                df = pd.DataFrame(full_menu)
                # Rename cols for display
                # st.dataframe(df[["name", "category", "price", "unit"]]) 
                
                # Custom list for actions
                for svg in full_menu:
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                    c1.write(f"**{svg['name']}**")
                    c2.write(f"{svg['category']}")
                    c3.write(f"{svg['price']:,.0f}/{svg['unit']}")
                    
                    with c4:
                        b_e, b_d = st.columns(2)
                        if b_e.button("✏️", key=f"e_sv_{svg['id']}"):
                            st.session_state["edit_service"] = svg
                            st.rerun()
                        if b_d.button("🗑️", key=f"d_sv_{svg['id']}"):
                            delete_service(svg['id'])
                            st.rerun()
                    st.divider()

# ---------------------------------------------------------
# TAB 3: LỊCH SỬ (Simple View)
# ---------------------------------------------------------
with tab_history:
    st.subheader("📜 Nhật ký Order (Gần đây)")
    # Should get all orders or filter?
    # For now, let's list all service_orders collection (Need a new func getAllOrders if needed, or query by date).
    # Since we didn't write get_all_service_orders, let's skip or add it if requested.
    # For user convenience, let's just show a placeholder or basic idea.
    
    st.info("Tính năng xem lịch sử toàn bộ đang phát triển. Bạn có thể xem chi tiết trong từng Booking History.")
