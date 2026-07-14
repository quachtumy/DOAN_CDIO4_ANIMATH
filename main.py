import os
import platform
import subprocess
from workflow_graph import app_graph
from utils.rendering import concatenate_videos, extract_scene_class_names # Nhớ có hàm trích xuất class này của bạn
from utils.cache_manager import save_video_to_cache # Import hàm lưu cache

def open_file_automatically(filepath):
    """Hàm phụ trợ: Tự động gọi trình phát video mặc định của hệ điều hành"""
    if not os.path.exists(filepath):
        print(f"Không tìm thấy file để mở: {filepath}")
        return

    print(f"Đang tự động mở video: {os.path.basename(filepath)}...")
    try:
        if platform.system() == 'Windows':
            os.startfile(filepath)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', filepath))
        else:  # Linux
            subprocess.call(('xdg-open', filepath))
    except Exception as e:
        print(f"Không thể tự động mở video. Lỗi: {e}")

def main():
    user_query = "Pytago là gì"
    
    print("="*50)
    print("BẮT ĐẦU QUÁ TRÌNH TẠO VIDEO AI (KIẾN TRÚC LANGGRAPH)")
    print("="*50)
    
    OUTPUT_DIR = "media/output"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    initial_state = {
        "user_query": user_query,
        "current_cycle": 1,
        "max_cycles": 3,
        "is_perfect": False,
        "video_paths": []
    }
    
    # Chạy đồ thị AI để sinh code và render
    final_state = app_graph.invoke(initial_state)
    
    print("\n" + "="*50)
    if final_state["is_perfect"]:
        print("XUẤT SẮC! VIDEO ĐÃ ĐẠT CHUẨN THẨM MỸ.")
    else:
        print("HẾT VÒNG LẶP. Đã lưu phiên bản render cuối cùng.")
    print("="*50)

    # =======================================================================
    # BỘ LỌC THÔNG MINH: CHỈ GỘP CÁC CLASS XUẤT HIỆN TRONG ĐOẠN CODE HIỆN TẠI
    # =======================================================================
    video_paths = final_state.get("video_paths", [])
    
    # Nếu bộ nhớ State bị trống do vòng cuối lỗi, ta chủ động tái cấu trúc lại danh sách video dựa trên mã code
    if not video_paths and final_state.get("current_code"):
        print("Vòng lặp cuối bị lỗi, hệ thống tiến hành phân tích mã nguồn để thu hồi đúng video...")
        
        # 1. Đọc đoạn code cuối cùng xem nó thực sự định nghĩa những Class (Scene) nào
        latest_code = final_state["current_code"]
        active_scenes = extract_scene_class_names(latest_code)
        
        if active_scenes:
            print(f"Các phân cảnh được định nghĩa trong code lần này: {active_scenes}")
            # 2. Quét kiểm tra trên ổ cứng, file nào trùng tên với class trong code hiện tại mới lấy
            recovered_paths = []
            for scene in active_scenes:
                # Tìm kiếm file trong thư mục temp_scene bất kể thư mục độ phân giải (480p15, 1080p60...)
                # Khai báo một vài đường dẫn phổ biến mà Manim hay xuất ra
                possible_paths = [
                    f"{OUTPUT_DIR}/videos/temp_scene/480p15/{scene}.mp4",
                    f"{OUTPUT_DIR}/videos/temp_scene/1080p60/{scene}.mp4",
                    f"{OUTPUT_DIR}/videos/temp_scene/720p30/{scene}.mp4"
                ]
                
                # Trực tiếp kiểm tra xem file có tồn tại vật lý trên ổ cứng không
                for path in possible_paths:
                    if os.path.exists(path):
                        recovered_paths.append(path)
                        break # Tìm thấy ở độ phân giải nào thì dừng phân cảnh đó luôn
            
            video_paths = recovered_paths

    if not video_paths:
        print("Hoàn toàn không tìm thấy video tương ứng với code hiện tại trên ổ cứng.")
        return

    # ==================================================
    # TIẾN HÀNH GỘP ĐÚNG DANH SÁCH ĐÃ LỌC
    # ==================================================
    # ==================================================
    # TIẾN HÀNH GỘP ĐÚNG DANH SÁCH ĐÃ LỌC VÀ KIỂM DUYỆT BỞI CON NGƯỜI
    # ==================================================
    if len(video_paths) > 1:
        print(f"\nSẵn sàng gộp {len(video_paths)} phân cảnh chuẩn xác của lần chạy này...")
        try:
            final_merged_video = concatenate_videos(video_paths, OUTPUT_DIR)
            print(f"Gộp video thành công tại: {final_merged_video}")
            
            # 1. Mở video cho bạn xem trước
            open_file_automatically(final_merged_video)
            
            # 2. CHỐT CHẶN CON NGƯỜI: Dừng chương trình chờ bạn xác nhận
            print("\n" + "!"*50)
            print("👀 HÃY XEM KỸ VIDEO VỪA MỞ TRÊN MÀN HÌNH!")
            print("Video này có giải thích đúng bản chất Toán học và không bị lỗi hình ảnh chứ?")
            approval = input("Bấm 'y' để LƯU VÀO KHO, hoặc phím bất kỳ để TỪ CHỐI: ")
            
            if approval.lower() == 'y':
                save_video_to_cache(user_query, final_merged_video)
                print("[THÀNH CÔNG] Đã phê duyệt và đưa vào kho Cache vĩnh viễn!")
            else:
                print("[TỪ CHỐI] Video có lỗi. Hệ thống KHÔNG lưu vào bộ nhớ.")
            print("!"*50)

        except Exception as e:
            print(f"Lỗi trong quá trình gộp video: {e}")
            open_file_automatically(video_paths[-1])
    else:
        # Tương tự cho trường hợp chỉ có 1 Scene
        print("\nChỉ có 1 phân cảnh hợp lệ, đang mở video...")
        open_file_automatically(video_paths[0])
        
        print("\n" + "!"*50)
        approval = input("Video có đúng kiến thức không? Bấm 'y' để LƯU VÀO KHO, phím khác để TỪ CHỐI: ")
        if approval.lower() == 'y':
            save_video_to_cache(user_query, video_paths[0])
            print("[THÀNH CÔNG] Đã phê duyệt và đưa vào kho Cache vĩnh viễn!")
        else:
            print("[TỪ CHỐI] Video có lỗi. Hệ thống KHÔNG lưu vào bộ nhớ.")

    # Cuối hàm main()
    if final_state.get("cached_video_path"):
        print("\n[SIÊU TỐC]: Câu hỏi trùng khớp hệ thống. Trích xuất video trực tiếp từ kho!")
        open_file_automatically(final_state["cached_video_path"])
        return

if __name__ == "__main__":
    main()