"""
UI Helper Functions - CSS và styling chung cho toàn bộ app
"""
import streamlit as st

def apply_sidebar_style():
    """
    Áp dụng CSS tùy chỉnh cho sidebar (left menu) trên tất cả các trang.
    Gọi hàm này ở đầu mỗi trang để đảm bảo sidebar có cùng style.
    """
    st.markdown("""
    <style>
        /* Thay đổi màu nền của sidebar */
        [data-testid="stSidebar"] {
            background-color: #3A6F43; /* Màu xanh đậm - bạn có thể đổi thành màu khác */
            background-image: linear-gradient(180deg, #3A6F43 0%, #064232 100%); /* Gradient (tùy chọn) */
        }
        
        /* Thay đổi màu chữ trong sidebar */
        [data-testid="stSidebar"] * {
            color: #ffffff !important; /* Màu chữ trắng */
        }
        
        /* Style cho các nút trong sidebar */
        [data-testid="stSidebar"] button {
            color: #ffffff !important;
        }
        
        /* Style cho các link trong sidebar */
        [data-testid="stSidebar"] a {
            color: #ffffff !important;
        }
        
        /* Style cho header sidebar (nếu có) */
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #ffffff !important;
        }
        
        /* Ẩn menu mặc định của Streamlit để dùng custom menu */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
        
        /* Style cho custom menu buttons - chỉ áp dụng cho button trong sidebar */
        [data-testid="stSidebar"] button[kind="secondary"] {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            color: #ffffff !important;
            transition: all 0.3s ease;
            margin-bottom: 3px !important;
            width: 100% !important;
            padding-top: 6px !important;
            padding-bottom: 6px !important;
            border-radius: 8px !important;
            font-size: 15px !important;
        }
        
        /* Hover effect chỉ cho button, không cho markdown container */
        [data-testid="stSidebar"] button[kind="secondary"]:hover {
            background-color: rgba(255, 255, 255, 0.25) !important;
            border-color: rgba(255, 255, 255, 0.4) !important;
            transform: translateX(2px);
        }
        
        /* Loại bỏ hover effect trên markdown container để tránh highlight sai vị trí */
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:hover {
            background-color: transparent !important;
        }
        
        /* Đảm bảo không có khoảng cách thừa giữa các button */
        [data-testid="stSidebar"] .stButton {
            margin-bottom: 4px !important;
        }

        /* Style cho item đang active để cao rộng đều với button */
        [data-testid="stSidebar"] .menu-active-item {
            background-color: rgba(255, 255, 255, 0.22);
            padding: 6px 12px;
            border-radius: 8px;
            margin-bottom: 4px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.3);
            font-size: 15px;
        }
    </style>
    """, unsafe_allow_html=True)

def create_custom_sidebar_menu():
    """
    Tạo custom sidebar menu với tên tùy chỉnh.
    Gọi hàm này trong main.py hoặc các trang để hiển thị menu tùy chỉnh.
    """
    import os
    
    # Detect trang hiện tại từ file path
    try:
        import inspect
        frame = inspect.currentframe()
        caller_file = frame.f_back.f_globals.get('__file__', '')
        if 'main.py' in caller_file or caller_file.endswith('main.py'):
            current_page = "main"
        elif '1_Dashboard' in caller_file:
            current_page = "dashboard"
        elif '2_Booking' in caller_file:
            current_page = "booking"
        elif '3_Checkout' in caller_file:
            current_page = "checkout"
        elif '3_Finance' in caller_file:
            current_page = "finance"
        elif '9_Settings' in caller_file:
            current_page = "settings"
        else:
            current_page = "main"
    except:
        current_page = st.session_state.get("current_page", "main")
    
    with st.sidebar:
        st.markdown("### 🎋 Menu")
        st.markdown("---")
        
        # Định nghĩa menu items với tên tùy chỉnh
        menu_items = [
            ("🏠", "Trang chủ", "main", "main.py"),
            ("🏨", "Sơ đồ phòng", "dashboard", "pages/1_Dashboard.py"),
            ("🛎️", "Đặt phòng", "booking", "pages/2_Booking.py"),
            ("💸", "Trả phòng", "checkout", "pages/3_Checkout.py"),
            ("📊", "Báo cáo", "finance", "pages/3_Finance.py"),
            ("⚙️", "Cài đặt", "settings", "pages/9_Settings.py"),
        ]
        
        # Tạo các nút menu
        for icon, label, page_id, page_path in menu_items:
            is_current = (current_page == page_id)
            
            # Highlight trang hiện tại
            if is_current:
                st.markdown(
                    f'<div class="menu-active-item"><strong>{icon} {label}</strong></div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(f"{icon} {label}", key=f"menu_{page_id}", use_container_width=True, type="secondary"):
                    try:
                        st.switch_page(page_path)
                    except Exception as e:
                        # Fallback: reload page với query param
                        st.rerun()
        
        st.markdown("---")
        st.caption("The Bamboo Resort")
