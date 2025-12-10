from selenium import webdriver
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pickle
import csv

browser = webdriver.Chrome()
browser.get("http://facebook.com")

# 1. LOAD COOKIE
try:
    cookies = pickle.load(open("my_cookie.pkl", "rb"))
    for cookie in cookies:
        browser.add_cookie(cookie)
    browser.get("http://facebook.com") # Refresh để nhận cookie
    sleep(3)
except Exception as e:
    print("Lỗi load cookie:", e)

# 2. XỬ LÝ ĐĂNG NHẬP (Chỉ nhập tay nếu chưa vào được)
try:
    # Kiểm tra xem có ô nhập email không. Nếu cookie sống thì lệnh này sẽ lỗi và nhảy xuống except
    txtUser = browser.find_element(By.ID, "email") 
    
    # Nếu tìm thấy ô email, nghĩa là chưa đăng nhập -> Nhập tay
    print("Cookie lỗi hoặc hết hạn, đang đăng nhập tay...")
    txtUser.send_keys("")
    txtPassword = browser.find_element(By.ID, "pass")
    txtPassword.send_keys("")
    txtPassword.send_keys(Keys.ENTER)
    sleep(5)
except:
    print("Đã đăng nhập thành công (bằng cookie)!")

# --- CHUẨN BỊ TÌM KIẾM ---
print("Chuẩn bị tìm kiếm...")
sleep(2)

tu_khoa = "y tế"  
search_url = f"https://www.facebook.com/search/posts/?q={tu_khoa}"

browser.get(search_url)
sleep(5) 

# --- CÀO DỮ LIỆU ---
scraped_data = set()
count = 0 

with open('ket_qua_tim_kiem.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Nội dung bài viết"])

    so_lan_cuon = 10 
    for i in range(so_lan_cuon):
        print(f"--- Đang cuộn trang lần {i+1} ---")
        
        # === CHIẾN THUẬT TÌM THẺ ĐA NĂNG ===
        # Cách 1: Tìm theo chuẩn chung (Newsfeed thường dùng)
        posts = browser.find_elements(By.XPATH, "//div[@role='article']")
        
        # Cách 2: Nếu Cách 1 không thấy, tìm theo danh sách hiển thị (Trang Search thường dùng)
        if len(posts) == 0:
            # aria-posinset là thuộc tính đánh số thứ tự bài viết (1, 2, 3...)
            posts = browser.find_elements(By.XPATH, "//div[@aria-posinset]")
        
        # Cách 3: Tìm theo thẻ bao quát nhất (Dự phòng cuối cùng)
        if len(posts) == 0:
             # Tìm các thẻ div có class chứa chữ 'x1yzt' (thường là class bao bài viết - hên xui)
             # Hoặc tìm thẻ div chứa text "Bình luận" để xác định đó là bài viết
             posts = browser.find_elements(By.XPATH, "//div[contains(text(), 'Bình luận')]/ancestor::div[3]")

        print(f"-> Tìm thấy {len(posts)} thẻ tiềm năng...")

        if not posts:
            print("Vẫn chưa thấy bài nào, đợi 5s rồi thử lại...")
            sleep(5)
            # Cuộn nhẹ một chút để mồi
            browser.execute_script("window.scrollBy(0, 300);")
            continue

        for post in posts:
            try:
                # Lấy nội dung
                content = post.text
                
                # LOGIC LỌC:
                # 1. Phải dài hơn 50 ký tự (tránh lấy nhầm nút like, menu...)
                # 2. Chưa từng lưu trước đó
                if len(content) > 50 and content not in scraped_data:
                    # Kiểm tra kỹ hơn: Bài viết thường phải có chữ "Thích" hoặc "Bình luận" hoặc "Chia sẻ"
                    # Điều này giúp loại bỏ các div rác không phải bài viết
                    if "Thích" in content or "Bình luận" in content or "Like" in content:
                        scraped_data.add(content)
                        writer.writerow([content])
                        count += 1
                        print(f"--> [ĐÃ LƯU BÀI {count}]: {content[:40]}...")
            except Exception as e:
                # Lỗi thường gặp: StaleElementReferenceException (do trang web vừa render lại)
                continue

        # Cuộn trang xuống cuối
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # QUAN TRỌNG: Trang Search load chậm hơn Newsfeed, cần nghỉ lâu hơn
        sleep(7)

print(f"Hoàn thành! Đã lấy được {count} bài viết về '{tu_khoa}'.")
browser.close()