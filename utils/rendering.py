import os
import subprocess
import cv2
import re

def extract_scene_class_names(code: str) -> list:
    """Trích xuất tất cả tên Class kế thừa từ Scene trong code.
    Giống với cách file rendering.py của repo gốc quét mã nguồn."""
    matches = re.findall(r"class\s+([A-Za-z0-9_]+)\(.*?Scene.*?\):", code)
    return matches

def run_manim_script(code_path: str, output_dir: str, scene_name: str) -> tuple:
    """Chạy lệnh Manim ngầm, bắt log lỗi và thiết lập thời gian timeout."""
    # Tạo thư mục chứa media nếu chưa có
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = [
        "manim", 
        "-pql",            # Chất lượng thấp (480p15) để vòng lặp test diễn ra cực nhanh
        code_path, 
        scene_name, 
        "--media_dir", output_dir
    ]
    
    try:
        # Chạy ngầm subprocess, giống cách execute_code() của repo gốc hoạt động
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=400  # Giới hạn 400 giây để chống treo máy nếu AI viết vòng lặp vô hạn
        )
        success = result.returncode == 0
        
        # Nếu lỗi, lấy 2000 ký tự cuối của log đỏ để không làm tràn Token của AI
        logs = result.stderr[-2000:] if not success else "Execution successful. No errors."
        return success, logs
        
    except subprocess.TimeoutExpired:
        return False, "Error: TimeoutExpired - Quá thời gian 400 giây. Code có thể bị lặp vô hạn (always_redraw kẹt)."
    except Exception as e:
        return False, f"System Error: {str(e)}"

def extract_video_frames(video_path: str, output_dir: str, count: int = 3) -> list:
    """Dùng OpenCV cắt video thành các khung hình để Agent 3 (Vision) chấm điểm."""
    if not os.path.exists(video_path):
        return []

    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames <= 0:
        return []

    frame_paths = []
    
    # Tính toán vị trí cắt khung hình (Lấy các khoảng cách đều nhau ở giữa video)
    # Cắt bỏ frame 0 vì Manim thường bắt đầu bằng màn hình đen
    frame_indices = [int(total_frames * i / (count + 1)) for i in range(1, count + 1)]
    
    for idx, frame_idx in enumerate(frame_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            # Lưu ảnh ra file png
            path = os.path.join(output_dir, f"frame_{idx}.png")
            cv2.imwrite(path, frame)
            frame_paths.append(path)
            
    cap.release()
    return frame_paths

# Thêm vào cuối file rendering.py

def extract_highest_density_frames(video_path: str, output_dir: str, count: int = 3) -> list:
    """
    [Trụ cột 4] Thuật toán quét toàn bộ video, dùng toán Laplacian để tìm ra 
    các khung hình có mật độ chi tiết/đường nét phức tạp nhất (nhiều chữ/hình khối nhất).
    """
    if not os.path.exists(video_path):
        return []

    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    
    frame_scores = []
    frame_idx = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Bỏ qua vài frame đầu tiên (thường là màn hình đen chuyển cảnh)
        if frame_idx > 5:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Dùng biến thiên Laplacian để tính độ sắc nét và mật độ chi tiết của frame
            score = cv2.Laplacian(gray, cv2.CV_64F).var()
            frame_scores.append((score, frame_idx, frame))
        frame_idx += 1
    
    # Sắp xếp các khung hình theo điểm số chi tiết từ cao xuống thấp
    frame_scores.sort(key=lambda x: x[0], reverse=True)
    
    # Lấy ra N khung hình có mật độ cao nhất nhưng phải cách xa nhau về thời gian (tránh trùng lặp ảnh)
    selected_frames = []
    used_indices = set()
    
    for score, idx, frame in frame_scores:
        # Đảm bảo khung hình được chọn không quá sát các khung hình đã chọn trước đó
        if all(abs(idx - u_idx) > 15 for u_idx in used_indices):
            selected_frames.append(frame)
            used_indices.add(idx)
        if len(selected_frames) == count:
            break
            
    cap.release()
    
    # Lưu các khung hình chất lượng nhất ra file
    frame_paths = []
    for i, frame in enumerate(selected_frames):
        path = os.path.join(output_dir, f"highest_density_{i}.png")
        cv2.imwrite(path, frame)
        frame_paths.append(path)
        
    return frame_paths


def concatenate_videos(video_paths: list, output_dir: str) -> str:
    """
    [Trụ cột 5] Sử dụng ffmpeg thông qua subprocess để nối tất cả các file phân cảnh 
    thành một video sản phẩm hoàn chỉnh cuối cùng.
    """
    if not video_paths:
        return ""
    
    if len(video_paths) == 1:
        return video_paths[0] # Chỉ có 1 scene thì không cần nối
        
    concat_file_path = os.path.join(output_dir, "video_list.txt")
    final_output_path = os.path.join(output_dir, "final_complete_video.mp4")
    
    # Tạo file text chứa danh sách video theo chuẩn định dạng ffmpeg demuxer
    with open(concat_file_path, "w", encoding="utf-8") as f:
        for path in video_paths:
            # ffmpeg yêu cầu đường dẫn tuyệt đối hoặc fix dấu gạch chéo
            abs_path = os.path.abspath(path).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")
            
    # Lệnh ghép video không re-encode (cực nhanh và giữ nguyên chất lượng)
    cmd = [
        "ffmpeg", "-y", 
        "-f", "concat", 
        "-safe", "0", 
        "-i", concat_file_path, 
        "-c", "copy", 
        final_output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Dọn dẹp file cấu hình tạm
        if os.path.exists(concat_file_path):
            os.remove(concat_file_path)
        return final_output_path
    except Exception as e:
        print(f"[HỆ THỐNG ERROR]: Không thể ghép các phân cảnh video: {e}")
        return video_paths[0] # Fallback trả về file đầu tiên