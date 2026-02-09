"""
UI Helper Functions - CSS và styling chung cho toàn bộ app
"""
import streamlit as st
from src.db import authenticate_user, get_all_users, create_user, hash_password
from src.models import User, UserRole
import time

def init_default_admin():
    """Tạo tài khoản Admin mặc định nếu hệ thống chưa có user nào"""
    # Chỉ chạy 1 lần check
    if "admin_checked" in st.session_state:
        return

    users = get_all_users()
    if not users:
        # Create default admin
        default_admin = User(
            username="admin",
            password_hash=hash_password("123456"),
            full_name="Administrator",
            role=UserRole.ADMIN,
            is_active=True
        )
        create_user(default_admin.to_dict())
        st.toast("⚠️ Đã tạo tài khoản mặc định: admin / 123456", icon="🛡️")
    
    st.session_state["admin_checked"] = True

def login_form():
    """Hiển thị form đăng nhập"""
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            background-color: white;
            color: #333;
        }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=80) 
        st.markdown("<h2 style='text-align: center;'>Đăng Nhập</h2>", unsafe_allow_html=True)
        
        with st.form("login_frm"):
            username = st.text_input("Tên đăng nhập", placeholder="admin")
            password = st.text_input("Mật khẩu", type="password", placeholder="******")
            
            if st.form_submit_button("Đăng nhập", type="primary", use_container_width=True):
                user = authenticate_user(username, password)
                if user:
                    st.session_state["user"] = user
                    st.success(f"Chào mừng {user.get('full_name')}!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu!")

def require_login():
    """
    Hàm bắt buộc đăng nhập. Đặt ở đầu mỗi trang.
    Nếu chưa login -> Hiện form login -> Chặn render nội dung bằng st.stop()
    Nếu đã login -> Hiển thị nút Logout ở sidebar.
    """
    init_default_admin()
    
    if "user" not in st.session_state:
        login_form()
        st.stop() # Dừng render nội dung bên dưới
    
    # Nếu đã login, hiển thị thông tin user ở sidebar
    user = st.session_state["user"]
    with st.sidebar:
        st.divider()
        st.write(f"👤 **{user.get('full_name', 'User')}**")
        st.caption(f"Vai trò: {user.get('role', 'staff')}")
        if st.button("Đăng xuất", type="secondary"):
            st.session_state.pop("user")
            st.rerun()

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
        # Format: (Icon, Label, PageID, PagePath, AcceptRoles)
        # AcceptRoles = None (All) or List of Roles
        all_menu_items = [
            ("🏠", "Trang chủ", "main", "main.py", None),
            ("🏨", "Sơ đồ phòng", "dashboard", "pages/1_Dashboard.py", None),
            ("🛎️", "Đặt phòng", "booking", "pages/2_Booking.py", None),
            ("🍽️", "Dịch vụ & Ăn uống", "services", "pages/5_Services.py", None),
            ("💸", "Trả phòng", "checkout", "pages/3_Checkout.py", None),
            ("📊", "Báo cáo", "finance", "pages/3_Finance.py", [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]),
            ("⚙️", "Cài đặt", "settings", "pages/9_Settings.py", [UserRole.ADMIN, UserRole.MANAGER]), # Kế toán vào settings xem only thì handle trong page
        ]
        
        # Filter by Role
        user = st.session_state.get("user")
        user_role = user.get("role") if user else None
        
        # Nếu chưa login (đang ở màn hình login), có thể hiển thị menu trống hoặc cơ bản?
        # Nhưng require_login() stop rồi nên k thấy menu đâu.
        # Nếu đã login:
        
        for icon, label, page_id, page_path, roles in all_menu_items:
            # Check permission
            if roles and user_role:
                if user_role not in roles:
                    continue # Skip
            
            # Special case: Manager cannot access Staff tab in settings? 
            # That's inside the page logic. Here we just gate the page access.
            # Kế toán: Không vào Settings (theo list trên).
            # Nhưng yêu cầu user là Kế toán xem dashboard, booking, finance. Done.
            
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
        
        # st.markdown("---") # Moved to require_login footer
        # st.caption("The Bamboo Resort")
