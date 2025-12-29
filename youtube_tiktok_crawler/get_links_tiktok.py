from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os

# --- CẤU HÌNH ---
KEYWORD = "Cam kết 100%"      # Từ khóa
MAX_LINKS = 10      # Số link cần lấy
OUTPUT_FILE = 'input_links_tiktok.txt' 

def get_tiktok_links_drission(keyword, max_count):
    print(f"🚀 Khởi động DrissionPage tìm kiếm: {keyword}")

    # 1. Cấu hình trình duyệt
    co = ChromiumOptions()
    co.set_argument('--mute-audio') # Tắt tiếng video
    
    # --- QUAN TRỌNG: Lưu Profile để nhớ đăng nhập ---
    # Tạo folder UserData để lưu cookies, lần sau chạy sẽ không cần đăng nhập lại
    current_folder = os.path.dirname(os.path.abspath(__file__))
    user_data_path = os.path.join(current_folder, 'User_Data_TikTok')
    co.set_user_data_path(user_data_path)
    
    page = ChromiumPage(co)
    
    try:
        # 2. Truy cập TikTok Search
        url = f"https://www.tiktok.com/search?q={keyword}"
        print(f"🔗 Đang vào: {url}")
        page.get(url)
        
        # --- QUAN TRỌNG: Chờ xử lý thủ công ---
        # Kiểm tra xem có bị lỗi "Something went wrong" không
        if "Something went wrong" in page.html or "Login" in page.title:
            print("\n" + "!"*50)
            print("⚠️ PHÁT HIỆN TIKTOK CHẶN HOẶC YÊU CẦU ĐĂNG NHẬP!")
            print("👉 Hãy thao tác TRÊN TRÌNH DUYỆT vừa mở:")
            print("   1. Đăng nhập tài khoản TikTok của bạn (Google/Facebook...).")
            print("   2. Hoặc tải lại trang (F5) nếu chỉ lỗi mạng.")
            print("   3. Đảm bảo danh sách video đã hiện ra.")
            input("✅ Sau khi thấy video hiện ra, BẤM ENTER TẠI ĐÂY để tool chạy tiếp...")
            print("!"*50 + "\n")
        else:
            time.sleep(3) 
        
        found_links = []
        print("🔄 Bắt đầu cuộn trang và quét link...")
        
        # Vòng lặp quét
        retry_scroll = 0
        while len(found_links) < max_count:
            # Lấy tất cả thẻ 'a' có chứa link video
            video_elements = page.eles('tag:a@@href:video') 
            
            for ele in video_elements:
                link = ele.attr('href')
                if link and "tiktok.com" in link and "/video/" in link:
                    if link not in found_links:
                        found_links.append(link)
                        print(f"   ✅ [{len(found_links)}/{max_count}] {link}")
                        
                    if len(found_links) >= max_count:
                        break
            
            if len(found_links) >= max_count:
                break

            # Logic cuộn trang
            prev_height = page.run_js('return document.body.scrollHeight')
            page.scroll.to_bottom()
            time.sleep(2)
            curr_height = page.run_js('return document.body.scrollHeight')
            
            if prev_height == curr_height:
                retry_scroll += 1
                print("   ⚠️ Không thấy nội dung mới, thử cuộn lại...")
                # Nếu cuộn 3 lần mà không thấy gì, có thể do TikTok bắt verify
                if retry_scroll >= 3:
                    print("🛑 Đã hết video hoặc bị chặn cuộn.")
                    break
            else:
                retry_scroll = 0

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        
    finally:
        print("👋 Đóng trình duyệt.")
        page.quit()
        
    return found_links

# --- CHẠY TOOL ---
if __name__ == "__main__":
    # Xóa nội dung file cũ (nếu muốn ghi mới hoàn toàn)
    # open(OUTPUT_FILE, 'w').close() 

    links = get_tiktok_links_drission(KEYWORD, MAX_LINKS)
    
    print(f"\n🎉 KẾT QUẢ: Đã lấy được {len(links)} link.")
    
    if links:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            for link in links:
                f.write(link + "\n")
        print(f"📝 Đã lưu vào '{OUTPUT_FILE}'.")
        print("👉 Chạy 'crawler_youtube.py' (nhớ đổi tên file input trong code đó) để tải!")