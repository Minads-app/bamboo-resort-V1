import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import os
from datetime import datetime
from src.models import Booking, BookingStatus, RoomStatus
import uuid


# --- 1. KẾT NỐI FIRESTORE (Singleton) ---
# --- 1. KẾT NỐI FIRESTORE (Singleton) ---

def init_firebase():
    """Khởi tạo Firebase App nếu chưa có"""
    if not firebase_admin._apps:
        try:
            # Ưu tiên 1: File key (Local dev)
            if os.path.exists("firebase_key.json"):
                cred = credentials.Certificate("firebase_key.json")
                firebase_admin.initialize_app(cred)
            # Ưu tiên 2: Streamlit Secrets (Cloud deployment)
            elif "firebase" in st.secrets:
                # Convert st.secrets to a standard dict to avoid issues
                key_dict = dict(st.secrets["firebase"])
                
                # Handle private_key newlines if they are escaped incorrectly
                if "private_key" in key_dict:
                    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
                    
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
            else:
                st.error("⚠️ Lỗi: Không tìm thấy 'firebase_key.json' hoặc cấu hình secrets 'firebase'.")
        except Exception as e:
            st.error(f"Lỗi khởi tạo Firebase: {e}")

def get_db():
    """Lấy object kết nối tới DB"""
    # Đảm bảo đã init chác chắn
    init_firebase()
    return firestore.client()

# --- 2. LOGIC XỬ LÝ DỮ LIỆU (CRUD) ---

def save_room_type_to_db(room_type_data: dict):
    """Lưu hoặc cập nhật loại phòng"""
    db = get_db()
    # Dùng type_code làm ID của document
    doc_id = room_type_data.get("type_code")
    if doc_id:
        db.collection("config_room_types").document(doc_id).set(room_type_data)

def get_all_room_types():
    """Lấy danh sách tất cả loại phòng"""
    db = get_db()
    docs = db.collection("config_room_types").stream()
    return [doc.to_dict() for doc in docs]

def delete_room_type(type_code: str):
    """Xóa loại phòng"""
    db = get_db()
    if type_code:
        db.collection("config_room_types").document(type_code).delete()

# --- LOGIC PHÒNG (ROOMS) ---

def save_room_to_db(room_data: dict):
    """Lưu phòng (101, 102...)"""
    db = get_db()
    # Dùng số phòng làm ID (VD: '101')
    doc_id = room_data.get("id")
    if doc_id:
        db.collection("rooms").document(doc_id).set(room_data)

def get_all_rooms():
    """Lấy danh sách tất cả phòng"""
    db = get_db()
    docs = db.collection("rooms").stream()
    return [doc.to_dict() for doc in docs]

def delete_room(room_id: str):
    """Xóa phòng"""
    db = get_db()
    if room_id:
        db.collection("rooms").document(room_id).delete()
# --- LOGIC BOOKING (CHECK-IN) ---

def create_booking(booking: Booking, is_checkin_now: bool):
    """
    Tạo booking mới.
    - Nếu is_checkin_now = True: Phòng -> OCCUPIED (Đang ở)
    - Nếu is_checkin_now = False: Phòng -> RESERVED (Đặt trước)
    """
    db = get_db()
    
    if not booking.id:
        booking.id = str(uuid.uuid4())[:8]
    
    # Xác định trạng thái
    if is_checkin_now:
        booking.status = BookingStatus.CHECKED_IN
        room_status = RoomStatus.OCCUPIED.value
    else:
        booking.status = BookingStatus.CONFIRMED
        # Nếu là booking online, phòng trước tiên ở trạng thái CHỜ THANH TOÁN
        if getattr(booking, "is_online", False):
            room_status = RoomStatus.PENDING_PAYMENT.value
        else:
            room_status = RoomStatus.RESERVED.value

    booking_data = booking.to_dict()
    
    try:
        # 1. Lưu Booking
        db.collection("bookings").document(booking.id).set(booking_data)
        
        # 2. Update trạng thái phòng
        db.collection("rooms").document(booking.room_id).update({
            "status": room_status,
            "current_booking_id": booking.id
        })
        return True, booking.id
    except Exception as e:
        return False, str(e)

def get_active_booking(room_id: str):
    """Lấy booking đang active của phòng này (nếu có)"""
    db = get_db()
    # Query: tìm booking có room_id == room_id và status == active
    docs = db.collection("bookings")\
        .where("room_id", "==", room_id)\
        .where("status", "==", "active")\
        .limit(1).stream()
    
    for doc in docs:
        return doc.to_dict()
    return None

def cancel_booking(booking_id: str):
    """Hủy booking"""
    db = get_db()
    if booking_id:
        db.collection("bookings").document(booking_id).update({
            "status": "cancelled"
        })
        return True
    return False
# ... (Giữ nguyên code cũ) ...

# --- LOGIC CHECK-OUT ---

def get_occupied_rooms():
    """Lấy danh sách các phòng đang có khách (Occupied)"""
    db = get_db()
    docs = db.collection("rooms").where("status", "==", "Đang ở").stream()
    return [doc.to_dict() for doc in docs]

def get_booking_by_id(booking_id: str):
    """Lấy thông tin chi tiết booking"""
    db = get_db()
    doc = db.collection("bookings").document(booking_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

def process_checkout(booking_id: str, room_id: str, final_amount: float, payment_method: str, note: str, service_fee: float = 0.0):
    """
    Xử lý trả phòng:
    1. Update Booking: status='Completed', set actual_check_out, final_amount, service_fee
    2. Update Room: status='Chưa dọn' (DIRTY) - cần dọn mới bán được tiếp
    """
    db = get_db()
    try:
        # Tự động tính lại tổng tiền dịch vụ (Service Orders) nếu có
        # Lưu ý: final_amount truyền vào có thể đã bao gồm service_fee nếu UI tính rồi.
        # Nhưng để chắc chắn, ta có thể lưu riêng field 'order_service_total' vào booking.
        
        # Ở đây ta giả định final_amount là TỔNG CỘNG (nguyên tiền phòng + dịch vụ).
        # Nhưng ta nên lưu thêm thông tin service_fee (phụ thu) và order_service_total (tiền gọi món).
        
        total_service_orders = calculate_service_total(booking_id)
        
        # Update Booking
        db.collection("bookings").document(booking_id).update({
            "status": "Completed",
            "check_out_actual": datetime.now(),
            "total_amount": final_amount, 
            "service_fee": service_fee, # Phụ thu khác
            "order_service_total": total_service_orders, # Tiền gọi món
            "payment_method": payment_method,
            "note": note
        })
        
        # Update Room
        db.collection("rooms").document(room_id).update({
            "status": RoomStatus.DIRTY, # Chuyển sang dơ để dọn dẹp
            "current_booking_id": firestore.DELETE_FIELD # Xóa link booking
        })
        return True, "Thanh toán thành công"
    except Exception as e:
        return False, str(e)

def update_room_status(room_id: str, new_status: str):
    """Hàm phụ trợ: Dùng để cập nhật trạng thái phòng (VD: Dọn xong -> Trống)"""
    db = get_db()
    db.collection("rooms").document(room_id).update({"status": new_status})

def check_in_reserved_room(room_id: str):
    """
    Check-in nhanh cho phòng đang ở trạng thái Đặt trước.

    - Update booking.status -> "Đang ở"
    - Lưu lại check_in cũ vào `check_in_reserved` (nếu có) và set check_in = now
    - Update room.status -> "Đang ở"
    """
    db = get_db()
    try:
        room_doc = db.collection("rooms").document(room_id).get()
        if not room_doc.exists:
            return False, "Không tìm thấy phòng"

        room = room_doc.to_dict() or {}
        booking_id = room.get("current_booking_id")
        if not booking_id:
            return False, "Phòng đặt trước nhưng thiếu current_booking_id"

        bk_ref = db.collection("bookings").document(booking_id)
        bk_doc = bk_ref.get()
        if not bk_doc.exists:
            return False, "Không tìm thấy booking của phòng"

        bk = bk_doc.to_dict() or {}
        now = datetime.now()

        updates = {
            "status": RoomStatus.OCCUPIED,  # "Đang ở"
            "check_in": now,
        }
        # Lưu lại giờ check-in dự kiến (để truy vết)
        if bk.get("check_in") is not None and bk.get("check_in_reserved") is None:
            updates["check_in_reserved"] = bk.get("check_in")

        bk_ref.update(updates)

        db.collection("rooms").document(room_id).update({
            "status": RoomStatus.OCCUPIED,
        })

        return True, booking_id
    except Exception as e:
        return False, str(e)

# --- FINANCE / REPORTING ---

def get_all_bookings():
    """Lấy toàn bộ bookings (phục vụ báo cáo đơn giản)."""
    db = get_db()
    docs = db.collection("bookings").stream()
    return [doc.to_dict() for doc in docs]

def get_pending_online_bookings():
    """
    Lấy danh sách booking online đang chờ xác nhận thanh toán.

    Điều kiện:
    - is_online == True
    - online_payment_status != 'confirmed'
    """
    db = get_db()
    # Để tránh phải tạo composite index phức tạp trên Firestore,
    # ta chỉ query theo is_online và lọc trạng thái ở phía Python.
    docs = db.collection("bookings").where("is_online", "==", True).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        status = data.get("online_payment_status", "pending")
        if status != "confirmed":
            results.append(data)
    return results

def get_confirmed_online_bookings(limit: int = 20):
    """
    Lấy danh sách booking online đã được xác nhận (online_payment_status == 'confirmed').
    Mặc định trả về tối đa 20 booking mới nhất (theo check_in giảm dần).
    """
    db = get_db()
    docs = db.collection("bookings").where("is_online", "==", True).stream()
    all_items = []
    for doc in docs:
        data = doc.to_dict()
        if data.get("online_payment_status") == "confirmed":
            all_items.append(data)

    # Sắp xếp theo check_in mới nhất
    def _key(b):
        ci = b.get("check_in")
        return ci or datetime.min

    all_items.sort(key=_key, reverse=True)
    return all_items[:limit]

def update_online_payment_proof(
    booking_id: str,
    screenshot_b64: str,
    filename: str,
    mime: str,
):
    """Lưu ảnh chụp thanh toán cho booking online và chuyển trạng thái sang 'waiting_confirm'."""
    db = get_db()
    db.collection("bookings").document(booking_id).update(
        {
            "payment_screenshot_b64": screenshot_b64,
            "payment_screenshot_name": filename,
            "payment_screenshot_mime": mime,
            "online_payment_status": "waiting_confirm",
        }
    )

def confirm_online_booking(booking_id: str):
    """Nhân viên lễ tân xác nhận đã nhận tiền đặt cọc / thanh toán.

    - Cập nhật online_payment_status = 'confirmed'
    - Chuyển trạng thái phòng từ 'Chờ thanh toán' -> 'Đặt trước'
    """
    db = get_db()
    try:
        bk_ref = db.collection("bookings").document(booking_id)
        bk_doc = bk_ref.get()
        if not bk_doc.exists:
            return False, "Không tìm thấy booking"

        data = bk_doc.to_dict() or {}
        room_id = data.get("room_id")

        # 1. Cập nhật trạng thái thanh toán online
        bk_ref.update({"online_payment_status": "confirmed"})

        # 2. Chuyển trạng thái phòng sang Đặt trước
        if room_id:
            db.collection("rooms").document(room_id).update(
                {"status": RoomStatus.RESERVED.value}
            )

        return True, "OK"
    except Exception as e:
        return False, str(e)

# --- SYSTEM CONFIG (PAYMENT INFO) ---

def get_payment_config():
    """
    Lấy cấu hình tài khoản thanh toán (ngân hàng) dùng chung cho:
    - Bill checkout tại quầy
    - Đặt phòng online (QR thanh toán)

    Lưu tại: collection 'config_system', document 'payment'.
    """
    db = get_db()
    doc = db.collection("config_system").document("payment").get()
    if doc.exists:
        return doc.to_dict()
    return {}

def save_payment_config(config: dict):
    """Lưu cấu hình tài khoản thanh toán."""
    db = get_db()
    db.collection("config_system").document("payment").set(config or {})

def get_system_config(key: str):
    """Lấy cấu hình hệ thống theo key (VD: 'special_days')"""
    db = get_db()
    doc = db.collection("config_system").document(key).get()
    if doc.exists:
        return doc.to_dict()
    return {}

def save_system_config(key: str, config: dict):
    """Lưu cấu hình hệ thống theo key"""
    db = get_db()
    db.collection("config_system").document(key).set(config or {})

def get_completed_bookings(start_dt: datetime | None = None, end_dt: datetime | None = None):
    """
    Lấy danh sách booking đã hoàn tất trong khoảng thời gian.

    Ghi chú: Do dữ liệu trạng thái đang có thể lệch chuẩn ("Completed"/"Hoàn tất"/Enum),
    hàm này sẽ lọc mềm và ưu tiên theo `check_out_actual`.
    """
    bookings = get_all_bookings()

    completed_statuses = {
        "Completed",
        "Hoàn tất",
        getattr(BookingStatus, "COMPLETED", None),
    }
    # Loại bỏ None/Enum objects, convert sang string nếu cần
    completed_statuses = set([s.value if hasattr(s, "value") else s for s in completed_statuses if s])

    def _in_range(ts: datetime | None) -> bool:
        if ts is None:
            return False
        # Firestore đôi khi trả datetime có tzinfo -> bỏ tzinfo để so sánh ổn định
        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)
        if start_dt:
            s = start_dt.replace(tzinfo=None) if start_dt.tzinfo else start_dt
            if ts < s:
                return False
        if end_dt:
            e = end_dt.replace(tzinfo=None) if end_dt.tzinfo else end_dt
            if ts > e:
                return False
        return True

    results = []
    for b in bookings:
        status = b.get("status")
        if hasattr(status, "value"):
            status = status.value
            
        # Ưu tiên booking có check_out_actual, vì đó là phát sinh doanh thu thực
        ts = b.get("check_out_actual")
        
        if ts:
            # Nếu có dữ liệu ngày tháng, chỉ lấy nếu NẰM TRONG khoảng thời gian
            if _in_range(ts):
                results.append(b)
            # Nếu có ts nhưng không khớp range -> Bỏ qua luôn, không check status nữa
            continue

        # Fallback: Chỉ check status nếu KHÔNG CÓ check_out_actual (data cũ/lỗi)
        if status in completed_statuses:
            # Nếu thiếu timestamp thì vẫn trả về (trang Finance sẽ loại/hiển thị cảnh báo)
            results.append(b)

    return results

# --- USER MANAGEMENT & AUTH ---

import hashlib

def hash_password(password: str) -> str:
    """Hash mật khẩu bằng SHA256 (đơn giản, có thể nâng cấp thêm salt)"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(username: str):
    """Lấy thông tin user theo username (email)"""
    # Fix: Kiểm tra username rỗng hoặc chỉ chứa khoảng trắng để tránh lỗi Firestore InvalidArgument
    if not username or not username.strip():
        return None
    db = get_db()
    doc = db.collection("users").document(username).get()
    if doc.exists:
        return doc.to_dict()
    return None

def find_customer_by_phone(phone: str):
    """Tìm thông tin khách hàng gần nhất theo số điện thoại"""
    if not phone or len(phone.strip()) < 3:
        return None
    
    db = get_db()
    # Tìm trong collection bookings, order by check_in desc, limit 1
    # Lưu ý: Cần composite index nếu sort và filter cùng lúc.
    # Để tránh lỗi index, ta có thể filter trước rồi sort in-memory nếu số lượng ít,
    # hoặc chỉ cần lấy 1 document bất kỳ (nếu chấp nhận không phải mới nhất).
    # Tuy nhiên, ta muốn lấy tên mới nhất.
    # Hãy thử query simple equality trước.
    
    docs = db.collection("bookings").where("customer_phone", "==", phone.strip()).stream()
    
    # Sort in-memory to find latest
    found_bookings = [doc.to_dict() for doc in docs]
    if not found_bookings:
        return None
        
    # Sort by created_at or check_in. Booking model has check_in.
    def _sort_key(b):
        ts = b.get('check_in')
        if isinstance(ts, datetime):
            return ts.timestamp()
        return 0.0
        
    found_bookings.sort(key=_sort_key, reverse=True)
    
    latest = found_bookings[0]
    return {
        "customer_name": latest.get("customer_name"),
        "customer_phone": latest.get("customer_phone"), # Giữ nguyên
        "customer_type": latest.get("customer_type", "Khách lẻ")
    }
    

    return None

def create_user(user_data: dict):
    """Tạo mới hoặc cập nhật user"""
    db = get_db()
    username = user_data.get("username")
    if username:
        db.collection("users").document(username).set(user_data)

def delete_user(username: str):
    """Xóa user"""
    db = get_db()
    if username:
        db.collection("users").document(username).delete()

def create_user_session(username: str) -> str:
    """Tạo session token mới cho user và lưu vào DB"""
    db = get_db()
    token = str(uuid.uuid4())
    # Lưu token vào document của user
    db.collection("users").document(username).update({
        "session_token": token,
        "last_login": datetime.now()
    })
    return token

def verify_user_session(token: str):
    """Kiểm tra token hợp lệ và trả về user info"""
    if not token:
        return None
    
    db = get_db()
    # Tìm user có session_token khớp
    docs = db.collection("users").where("session_token", "==", token).limit(1).stream()
    
    for doc in docs:
        user_data = doc.to_dict()
        if user_data.get("is_active", True):
            return user_data
            
    return None

def delete_user_session(username: str):
    """Xóa session token khi logout"""
    if not username: 
        return
    db = get_db()
    try:
        db.collection("users").document(username).update({
            "session_token": firestore.DELETE_FIELD
        })
    except Exception:
        pass

def authenticate_user(username, password):
    """
    Xác thực người dùng. 
    Trả về dict user nếu thành công, None nếu thất bại.
    """
    user = get_user(username)
    if user and user.get("is_active", True):
        # So sánh hash
        if user.get("password_hash") == hash_password(password):
            return user
    return None

def update_user_password(username: str, new_password: str):
    """Đổi mật khẩu"""
    if not username:
        return
    db = get_db()
    new_hash = hash_password(new_password)
    db.collection("users").document(username).update({"password_hash": new_hash})

def get_all_users():
    """Lấy danh sách tất cả users"""
    db = get_db()
    docs = db.collection("users").stream()
    return [doc.to_dict() for doc in docs]

# --- 6. SERVICES & ORDERS ---

def get_all_services():
    """Lấy danh sách Menu dịch vụ"""
    db = get_db()
    docs = db.collection("services").where("is_active", "==", True).stream()
    return [doc.to_dict() for doc in docs]

def save_service(service_data: dict):
    """Lưu món ăn/dịch vụ"""
    db = get_db()
    if not service_data.get("id"):
        service_data["id"] = str(uuid.uuid4())[:8]
    db.collection("services").document(service_data["id"]).set(service_data)

def delete_service(service_id: str):
    """Xóa (hoặc ẩn) món ăn"""
    db = get_db()
    # Soft delete: update is_active = False 
    # Nhưng user yêu cầu xóa: Delete luôn hoặc ẩn tùy logic. Ở đây làm ẩn an toàn hơn.
    # Nhưng để đơn giản UI quản lý, ta delete luôn document nếu muốn.
    # Thôi làm soft delete cho an toàn: set is_active=False? 
    # Nhưng get_all_services đang filter is_active=True.
    # Ok, delete thật cho gọn.
    db.collection("services").document(service_id).delete()

def add_service_order(order_data: dict):
    """Tạo order dịch vụ mới"""
    db = get_db()
    if not order_data.get("id"):
        order_data["id"] = str(uuid.uuid4())[:8]
    
    # Auto add timestamp
    if not order_data.get("created_at"):
        order_data["created_at"] = datetime.now()
    
    # 1. Lưu Order
    db.collection("service_orders").document(order_data["id"]).set(order_data)
    return True

def get_orders_by_booking(booking_id: str):
    """Lấy danh sách order của 1 booking"""
    db = get_db()
    docs = db.collection("service_orders").where("booking_id", "==", booking_id).stream()
    return [doc.to_dict() for doc in docs]

def calculate_service_total(booking_id: str):
    """Tính tổng tiền dịch vụ của booking"""
    orders = get_orders_by_booking(booking_id)
    return sum(o.get("total_value", 0) for o in orders)

def get_recent_service_orders(limit=50):
    """Lấy danh sách các order gần đây nhất (In-memory sort for safety)"""
    db = get_db()
    docs = db.collection("service_orders").stream()
    orders = [doc.to_dict() for doc in docs]
    
    # Sort desc by created_at. Handle missing field safe.
    # Firestore datetime is timezone-aware usually, datetime.now() is usually local naive or aware depending on env.
    # We just want relative order.
    def _sort_key(x):
        ts = x.get('created_at')
        if isinstance(ts, datetime):
            return ts.timestamp()
        return 0.0 # Oldest
        
    orders.sort(key=_sort_key, reverse=True)
    return orders[:limit]