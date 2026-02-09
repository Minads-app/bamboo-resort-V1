from pydantic import BaseModel, Field
from typing import Dict, Optional, List
from enum import Enum
from datetime import datetime

# --- 1. CẤU HÌNH GIÁ & LOẠI PHÒNG ---

class PriceConfig(BaseModel):
    """
    Cấu hình giá tiền.
    LƯU Ý: hourly_blocks phải dùng key là STRING (Firestore yêu cầu).
    VD: {"1": 50000, "2": 90000} thay vì {1: 50000}
    """
    hourly_blocks: Dict[str, float] = Field(default_factory=dict)
    overnight_price: float = 0.0
    daily_price: float = 0.0
    extra_adult_surcharge: float = 0.0
    extra_adult_surcharge: float = 0.0
    extra_child_surcharge: float = 0.0
    
    # --- Cấu hình cho phép loại hình thuê ---
    enable_hourly: bool = True
    enable_overnight: bool = True
    enable_daily: bool = True

class RoomType(BaseModel):
    type_code: str
    name: str
    default_adults: int = 2
    default_children: int = 0
    default_children: int = 0
    pricing: PriceConfig
    
    # --- Cấu hình giá Lễ/Tết & Cuối tuần ---
    pricing_weekend: Optional[PriceConfig] = None
    pricing_holiday: Optional[PriceConfig] = None

    def to_dict(self):
        try:
            return self.model_dump()
        except AttributeError:
            return self.dict()

# --- 2. QUẢN LÝ PHÒNG (ROOMS) ---

class RoomStatus(str, Enum):
    AVAILABLE = "Trống"      # Màu xanh
    RESERVED = "Đặt trước"   # Màu cam (Mới)
    PENDING_PAYMENT = "Chờ thanh toán"  # Chờ khách chuyển khoản / upload bill
    OCCUPIED = "Đang ở"      # Màu đỏ
    DIRTY = "Chưa dọn"       # Màu vàng
    MAINTENANCE = "Bảo trì"  # Màu xám

class Room(BaseModel):
    id: str                 # Số phòng: 101, 201
    room_type_code: str     # Link tới RoomType (VD: STD)
    floor: str              # Khu vực / Tầng (VD: Khu A, Tầng 1)
    status: RoomStatus = RoomStatus.AVAILABLE
    note: str = ""
    current_booking_id: Optional[str] = None # Link tới booking đang ở

    def to_dict(self):
        try: return self.model_dump()
        except AttributeError: return self.dict()

# --- 3. QUẢN LÝ ĐẶT PHÒNG (BOOKING) ---

class BookingType(str, Enum):
    HOURLY = "Theo giờ"
    OVERNIGHT = "Qua đêm"
    DAILY = "Theo ngày"

class BookingStatus(str, Enum):
    CONFIRMED = "Đã đặt"     # Khách đặt trước, chưa đến
    CHECKED_IN = "Đang ở"    # Khách đang ở
    COMPLETED = "Hoàn tất"   # Đã thanh toán
    CANCELLED = "Hủy"

class Booking(BaseModel):
    id: Optional[str] = None
    room_id: str
    customer_name: str
    customer_phone: str = ""
    customer_type: str = "Khách lẻ"
    booking_type: BookingType
    
    status: BookingStatus = BookingStatus.CHECKED_IN 
    
    check_in: datetime
    check_out_expected: datetime
    price_original: float = 0.0
    deposit: float = 0.0
    note: str = ""
    
    # Các trường cập nhật khi Check-out
    check_out_actual: Optional[datetime] = None
    total_amount: float = 0.0
    service_fee: float = 0.0  # Phụ thu / Dịch vụ
    payment_method: str = ""

    # --- Trường phục vụ đặt phòng online ---
    is_online: bool = False                           # Booking được tạo từ trang khách tự đặt
    online_payment_type: str = ""                    # "full" hoặc "deposit"
    online_payment_status: str = "pending"           # "pending" / "waiting_confirm" / "confirmed"
    payment_screenshot_b64: Optional[str] = None     # Ảnh chụp màn hình thanh toán (base64)
    payment_screenshot_name: str = ""                # Tên file ảnh
    payment_screenshot_mime: str = ""                # MIME type ảnh

    def to_dict(self):
        try: return self.model_dump()
        except AttributeError: return self.dict()

# --- 4. CẤU HÌNH HỆ THỐNG (SYSTEM CONFIG) ---

class SystemConfig(BaseModel):
    hotel_name: str = "The Bamboo Resort"
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    business_type: str = "Resort" # Homestay, Khách sạn, Resort...
    
    # Các cấu hình khác (nếu cần sync với model)
    holidays: List[str] = Field(default_factory=list)
    holiday_notes: Dict[str, str] = Field(default_factory=dict)
    
    def to_dict(self):
        try: return self.model_dump()
        except AttributeError: return self.dict()

# --- 5. NGƯỜI DÙNG & PHÂN QUYỀN (AUTH) ---

class UserRole(str, Enum):
    ADMIN = "admin"             # Owner/Admin: Full quyền
    MANAGER = "manager"         # Quản lý: Full quyền trừ Nhân viên & Cấu hình nhạy cảm
    ACCOUNTANT = "accountant"   # Kế toán: Xem báo cáo, không sửa cấu hình
    RECEPTIONIST = "receptionist" # Lễ tân: Check-in/out, không xem báo cáo/settings

class User(BaseModel):
    username: str             # Email hoặc Tên đăng nhập
    password_hash: str        # Mật khẩu đã hash
    full_name: str
    role: UserRole = UserRole.RECEPTIONIST
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self):
        try: return self.model_dump()
        except AttributeError: return self.dict()

# --- 6. DỊCH VỤ & ĂN UỐNG (SERVICES) ---

class ServiceCategory(str, Enum):
    FOOD = "Đồ ăn"
    DRINK = "Đồ uống"
    OTHER = "Dịch vụ" # Giặt ủi, Spa, Thuê xe...

class ServiceItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: ServiceCategory = ServiceCategory.DRINK
    price: float = 0.0
    unit: str = "cái" # cái, ly, chai, đĩa, kg...
    is_active: bool = True # Còn bán hay không

    def to_dict(self):
        try: return self.model_dump()
        except AttributeError: return self.dict()

class ServiceOrder(BaseModel):
    id: Optional[str] = None
    booking_id: str
    room_id: str # Lưu thêm để query nhanh theo phòng
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Danh sách món order: [{ "id": "...", "name": "...", "price": 50, "qty": 2, "total": 100 }]
    items: List[Dict] = Field(default_factory=list)
    
    total_value: float = 0.0
    note: str = ""
    
    def to_dict(self):
        try: return self.model_dump()
        except AttributeError: return self.dict()