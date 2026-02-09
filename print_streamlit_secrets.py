import json
import os

try:
    if not os.path.exists("firebase_key.json"):
        print("Lỗi: Không tìm thấy file 'firebase_key.json'.")
        exit(1)

    with open("firebase_key.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n" + "="*50)
    print("COPY ĐOẠN DƯỚI ĐÂY VÀO PHẦN SECRETS CỦA STREAMLIT CLOUD")
    print("="*50 + "\n")
    
    print("[firebase]")
    for key, value in data.items():
        if key == "private_key":
            # Xử lý xuống dòng cho private key trong TOML
            # Cách an toàn nhất là dùng triple quotes cho chuỗi nhiều dòng
            formatted_value = value.replace('"', '\\"')
            print(f'{key} = """{value}"""')
        else:
            print(f'{key} = "{value}"')

    print("\n" + "="*50)
    print("XONG! Hãy copy toàn bộ nội dung trong khung [firebase]... bao gồm cả dấu ngoặc.")
    input("Nhấn Enter để thoát...")

except Exception as e:
    print(f"Có lỗi xảy ra: {e}")
    input("Nhấn Enter để thoát...")
