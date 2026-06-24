# main.py (Bản cập nhật hoàn hảo)
import os
import shutil
from video_data import VIDEO_DATA
from agent_director import generate_video_plan
from agent_writer import generate_initial_code, generate_code_revision
from agent_reviewer import generate_review
from utils.rendering import extract_scene_class_names, run_manim_script, extract_highest_density_frames, concatenate_videos

MANIM_MODEL = "gemini-flash-lite-latest"  
REVIEW_MODEL = "gemini-flash-lite-latest"
MAX_CYCLES = 3
OUTPUT_DIR = "media/output"
ARTIFACTS_DIR = os.path.join(OUTPUT_DIR, "artifacts") # Thêm thư mục lưu vết

def main():
    # 1. BẠN CHỈ CẦN NHẬP YÊU CẦU NGẮN GỌN VÀO ĐÂY
    user_request = "Minh hoạ định lý Pytago bằng cách chia mỗi hình vuông thành các ô vuông nhỏ, rồi các ô vuông của cạnh a, b sẽ bay đến lấp đầy hình vuông cạnh c."
    
    print("="*50)
    print("🚀 BẮT ĐẦU QUÁ TRÌNH TẠO VIDEO AI")
    print("="*50)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    # 2. GỌI TÁC NHÂN ĐẠO DIỄN LÊN KỊCH BẢN CHI TIẾT
    video_data = generate_video_plan(MANIM_MODEL, user_request)
    
    print("\n" + "-"*50)
    print("[KỊCH BẢN CHI TIẾT ĐÃ ĐƯỢC TẠO RA]:")
    print(video_data)
    print("-"*50 + "\n")
    
    current_code = generate_initial_code(MANIM_MODEL, video_data)
    previous_reviews = []
    
    # [NÂNG CẤP 1] Biến lưu trữ bản code hoạt động tốt gần nhất
    working_code = None 
    final_video_paths = []
    
    for cycle in range(1, MAX_CYCLES + 1):
        print(f"\n[{'-'*15} VÒNG LẶP {cycle}/{MAX_CYCLES} {'-'*15}]")
        
        # [NÂNG CẤP 2] Lưu vết Artifacts (Bản nháp của từng vòng)
        artifact_path = os.path.join(ARTIFACTS_DIR, f"cycle_{cycle}_code.py")
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(current_code)
            
        code_path = os.path.join(OUTPUT_DIR, "temp_scene.py")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(current_code)
            
        scene_names = extract_scene_class_names(current_code)
        if not scene_names:
            scene_names = ["CustomScene"]
            
        all_success = True
        combined_logs = ""
        all_frames = []
        current_cycle_videos = []
        scenes_rendered_count = 0
        
        for scene in scene_names:
            print(f"[HỆ THỐNG]: Đang render Phân cảnh: {scene}...")
            success, logs = run_manim_script(code_path, OUTPUT_DIR, scene)
            combined_logs += f"\n--- Logs cho Scene {scene} ---\n{logs}\n"
            
            if success:
                scenes_rendered_count += 1
                video_path = os.path.join(OUTPUT_DIR, "videos", "temp_scene", "480p15", f"{scene}.mp4")
                if os.path.exists(video_path):
                    current_cycle_videos.append(video_path)
                    frame_out_dir = os.path.join(OUTPUT_DIR, f"frames_{scene}")
                    frames = extract_highest_density_frames(video_path, frame_out_dir, count=3)
                    all_frames.extend(frames)
            else:
                all_success = False

        # [NÂNG CẤP 1 - Xử lý Fallback]
        if all_success:
            working_code = current_code # Cập nhật code an toàn nhất
            final_video_paths = current_cycle_videos # Lưu lại các video thành công
            print(f"[HỆ THỐNG]: Render thành công. Đã lưu bản backup an toàn.")
            
        success_rate = (scenes_rendered_count / len(scene_names)) * 100.0
        
        review = generate_review(
            REVIEW_MODEL, current_code, combined_logs, all_frames, previous_reviews, 
            all_success, video_data, success_rate, scenes_rendered_count, len(scene_names)
        )
        print(f"\n[GIÁM KHẢO PHÁN QUYẾT]:\n{review}")
        
        # Lưu log review vào artifacts
        with open(os.path.join(ARTIFACTS_DIR, f"cycle_{cycle}_review.txt"), "w", encoding="utf-8") as f:
            f.write(review)
        
        if all_success and "[ALL_PERFECT_APPROVED]" in review.upper():
            break
            
        previous_reviews.append(review)
        if cycle < MAX_CYCLES:
            current_code = generate_code_revision(MANIM_MODEL, current_code, review, video_data, cycle + 1)
        else:
            print("\n[HỆ THỐNG]: Đã đạt giới hạn số vòng lặp.")

    # [XỬ LÝ KẾT QUẢ CUỐI CÙNG DỰA TRÊN FALLBACK]
    print("\n" + "="*50)
    if working_code is not None:
        print("🎉 QUÁ TRÌNH HOÀN TẤT VỚI MÃ NGUỒN AN TOÀN!")
        complete_video = concatenate_videos(final_video_paths, OUTPUT_DIR)
        print(f"🎬 File video tổng hợp lưu tại: {complete_video}")
        
        # Lưu bản code chuẩn cuối cùng
        with open(os.path.join(OUTPUT_DIR, "final_working_code.py"), "w", encoding="utf-8") as f:
            f.write(working_code)
    else:
        print("❌ THẤT BẠI: AI không thể tạo ra mã nguồn chạy được sau tất cả các vòng lặp.")
        print(f"Bạn có thể xem log lỗi tại thư mục: {ARTIFACTS_DIR}")
    print("="*50)

if __name__ == "__main__":
    main()