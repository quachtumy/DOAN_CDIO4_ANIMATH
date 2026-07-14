import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer

# Chỉ định nơi lưu trữ bộ nhớ
CACHE_FILE = "media/video_cache.json"

print("Đang tải mô hình nhúng (Sentence Transformer)...")
encoder_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("Tải mô hình thành công!")

def get_text_embedding(text: str):
    """Đổi câu hỏi ra vector tọa độ chạy 100% OFFLINE trên máy bạn"""
    try:
        # encode trả về numpy array, cần chuyển sang list để lưu vào file JSON
        vector = encoder_model.encode(text)
        return vector.tolist() 
    except Exception as e:
        print(f"Lỗi khi tạo vector: {e}")
        return None

def cosine_similarity(vec1, vec2):
    """Hàm toán học tính độ giống nhau giữa 2 câu nói"""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def load_cache():
    """Đọc file JSON lên bộ nhớ"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_cache(data):
    """Lưu dữ liệu mảng xuống file JSON"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def check_video_cache(user_query: str):
    """Quét cực nhanh xem trong kho JSON đã có câu hỏi nào tương tự chưa"""
    cache_data = load_cache()
    if not cache_data:
        return None
        
    query_vector = get_text_embedding(user_query)
    if not query_vector:
        return None

    best_score = 0
    best_match_path = None

    for item in cache_data:
        score = cosine_similarity(query_vector, item["embedding"])
        if score > best_score:
            best_score = score
            best_match_path = item["video_path"]
            
    # Độ tương đồng tiếng Việt đôi khi nhạy hơn, bạn có thể tinh chỉnh số này (0.90 -> 0.95)
    if best_score >= 0.90:
        print(f"[CACHE HIT]: Tìm thấy video trùng khớp ngữ nghĩa ({round(best_score*100, 2)}%)!")
        return best_match_path
        
    return None

def save_video_to_cache(user_query: str, video_path: str):
    """Lưu câu hỏi mới và vector vào file JSON"""
    cache_data = load_cache()
    query_vector = get_text_embedding(user_query)
    
    if query_vector:
        cache_data.append({
            "query": user_query,
            "video_path": video_path,
            "embedding": query_vector
        })
        save_cache(cache_data)
        print("[CACHE SAVED]: Đã lưu video vào bộ nhớ cục bộ (Local Sentence Transformer).")