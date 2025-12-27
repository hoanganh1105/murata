import pandas as pd

def json_to_csv_pandas(json_file_path, csv_file_path):
    """
    Chuyển đổi tệp JSON thành tệp CSV bằng thư viện Pandas.
    """
    try:
        # 1. Đọc tệp JSON trực tiếp vào DataFrame (cấu trúc bảng của Pandas)
        # read_json() là hàm rất mạnh mẽ của Pandas
        df = pd.read_json(json_file_path)

        # 2. Ghi DataFrame ra tệp CSV
        # index=False để không ghi số thứ tự hàng của Pandas vào CSV
        df.to_csv(csv_file_path, index=False, encoding='utf-8')

        print(f"✅ Chuyển đổi thành công với Pandas! Dữ liệu đã được lưu vào: {csv_file_path}")

    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")


# --- CÁCH SỬ DỤNG VÀ THỬ NGHIỆM ---
# Sử dụng tệp 'data.json' đã tạo ở Ví dụ 1
json_to_csv_pandas('tiktok-cancer.json', 'tiktok-cancer.csv')