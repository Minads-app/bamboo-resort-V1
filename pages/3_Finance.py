import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta

from src.db import get_completed_bookings, get_all_rooms, get_all_room_types
from src.ui import apply_sidebar_style, create_custom_sidebar_menu

st.set_page_config(page_title="Báo cáo doanh thu", layout="wide")
apply_sidebar_style()
create_custom_sidebar_menu()
st.title("📊 Finance - Báo cáo doanh thu")

st.caption("Nguồn dữ liệu: collection `bookings` (chỉ tính các booking đã trả phòng / có `check_out_actual`).")

rooms = get_all_rooms()
room_types = get_all_room_types()
room_map = {r.get("id"): r for r in rooms}
type_map = {t.get("type_code"): t for t in room_types}

with st.container(border=True):
    c1, c2, c3 = st.columns([1.2, 1.2, 1])

    with c1:
        preset = st.selectbox(
            "Khoảng thời gian",
            ["Hôm nay", "7 ngày gần nhất", "Tháng này", "Tháng trước", "Tùy chọn"],
            index=2,
        )

    today = date.today()
    if preset == "Hôm nay":
        start_d, end_d = today, today
    elif preset == "7 ngày gần nhất":
        start_d, end_d = today - timedelta(days=6), today
    elif preset == "Tháng này":
        start_d, end_d = today.replace(day=1), today
    elif preset == "Tháng trước":
        first_this_month = today.replace(day=1)
        last_prev_month = first_this_month - timedelta(days=1)
        start_d, end_d = last_prev_month.replace(day=1), last_prev_month
    else:
        start_d, end_d = None, None

    with c2:
        if preset == "Tùy chọn":
            d_from = st.date_input("Từ ngày", value=today.replace(day=1), format="DD/MM/YYYY")
            d_to = st.date_input("Đến ngày", value=today, format="DD/MM/YYYY")
        else:
            d_from = st.date_input("Từ ngày", value=start_d, format="DD/MM/YYYY")
            d_to = st.date_input("Đến ngày", value=end_d, format="DD/MM/YYYY")

    with c3:
        group_mode = st.radio("Nhóm theo", ["Ngày", "Tháng"], horizontal=True)

start_dt = datetime.combine(d_from, time.min)
end_dt = datetime.combine(d_to, time.max)

bookings = get_completed_bookings(start_dt=start_dt, end_dt=end_dt)

def _safe_dt(x):
    if isinstance(x, datetime):
        return x.replace(tzinfo=None) if x.tzinfo else x
    return None

rows = []
missing_ts = 0
for b in bookings:
    out_actual = _safe_dt(b.get("check_out_actual"))
    if out_actual is None:
        missing_ts += 1
        continue

    room_id = b.get("room_id", "")
    room_type_code = ""
    room_type_name = ""
    room_doc = room_map.get(room_id) or {}
    room_type_code = room_doc.get("room_type_code", "") or b.get("room_type_code", "")
    if room_type_code:
        room_type_name = type_map.get(room_type_code, {}).get("name", room_type_code)

    total_amount = b.get("total_amount")
    if total_amount is None:
        # dữ liệu cũ có thể chỉ có price_original
        total_amount = b.get("price_original", 0.0)

    payment_method = b.get("payment_method") or "Chưa rõ"

    rows.append(
        {
            "booking_id": b.get("id") or b.get("booking_id") or "",
            "room_id": room_id,
            "room_type_code": room_type_code,
            "room_type_name": room_type_name,
            "customer_name": b.get("customer_name", ""),
            "check_in": _safe_dt(b.get("check_in")),
            "check_out_actual": out_actual,
            "total_amount": float(total_amount or 0.0),
            "payment_method": payment_method,
            "note": b.get("note", ""),
            "status": b.get("status", ""),
        }
    )

df = pd.DataFrame(rows)

if df.empty:
    st.info("Không có dữ liệu doanh thu trong khoảng đã chọn.")
    if missing_ts > 0:
        st.caption(f"Ghi chú: có {missing_ts} booking được đánh dấu hoàn tất nhưng thiếu `check_out_actual` nên không tính doanh thu.")
    st.stop()

total_revenue = float(df["total_amount"].sum())
num_bills = int(len(df))
avg_bill = float(total_revenue / num_bills) if num_bills else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Tổng doanh thu", f"{total_revenue:,.0f} đ")
m2.metric("Số bill", f"{num_bills}")
m3.metric("TB / bill", f"{avg_bill:,.0f} đ")
m4.metric("Khoảng ngày", f"{d_from.strftime('%d/%m/%Y')} → {d_to.strftime('%d/%m/%Y')}")

st.divider()

df = df.sort_values("check_out_actual")
df["date"] = df["check_out_actual"].dt.date
df["month"] = df["check_out_actual"].dt.to_period("M").astype(str)

group_key = "date" if group_mode == "Ngày" else "month"
ts = df.groupby(group_key, as_index=False)["total_amount"].sum().rename(columns={"total_amount": "revenue"})

col_chart, col_top = st.columns([1.6, 1])
with col_chart:
    st.subheader("Doanh thu theo thời gian")
    st.line_chart(ts.set_index(group_key)["revenue"])

with col_top:
    st.subheader("Top phòng theo doanh thu")
    top_rooms = (
        df.groupby("room_id", as_index=False)["total_amount"]
        .sum()
        .sort_values("total_amount", ascending=False)
        .head(10)
        .rename(columns={"total_amount": "revenue"})
    )
    st.dataframe(top_rooms, use_container_width=True, hide_index=True)

st.subheader("Doanh thu theo loại phòng")
by_type = (
    df.groupby(["room_type_name"], as_index=False)["total_amount"]
    .sum()
    .sort_values("total_amount", ascending=False)
    .rename(columns={"total_amount": "revenue"})
)
st.bar_chart(by_type.set_index("room_type_name")["revenue"])
st.dataframe(by_type, use_container_width=True, hide_index=True)

st.subheader("Doanh thu theo phương thức thanh toán")
by_pay = (
    df.groupby(["payment_method"], as_index=False)["total_amount"]
    .sum()
    .sort_values("total_amount", ascending=False)
    .rename(columns={"total_amount": "revenue"})
)
st.bar_chart(by_pay.set_index("payment_method")["revenue"])
st.dataframe(by_pay, use_container_width=True, hide_index=True)

with st.expander("Xem chi tiết danh sách bill"):
    show_cols = [
        "check_out_actual",
        "booking_id",
        "room_id",
        "room_type_name",
        "customer_name",
        "total_amount",
        "payment_method",
        "note",
    ]
    st.dataframe(
        df[show_cols].sort_values("check_out_actual", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

csv = df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Tải CSV (doanh thu)",
    data=csv,
    file_name=f"finance_{d_from.strftime('%Y%m%d')}_{d_to.strftime('%Y%m%d')}.csv",
    mime="text/csv",
    use_container_width=True,
)

if missing_ts > 0:
    st.caption(f"Ghi chú: có {missing_ts} booking thiếu `check_out_actual` nên đã bị loại khỏi báo cáo.")