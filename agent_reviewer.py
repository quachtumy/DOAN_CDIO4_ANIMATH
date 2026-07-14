from utils.llm import review_manim_code
from utils.prompt import format_prompt, format_previous_reviews

def generate_review(
    model_name: str, 
    code: str, 
    logs: str, 
    frames: list, 
    previous_reviews: list, 
    success: bool,
    video_data: str,
    success_rate: float = 100.0,
    scenes_rendered: int = 1,
    total_scenes: int = 1
) -> str:
    """Agent Reviewer: Đánh giá mã nguồn động theo tỷ lệ thành công thực tế."""
    
    # 1. Chọn Prompt dựa trên trạng thái thành công toàn cục hoặc một phần
    # Nếu tỷ lệ thành công >= 100%, kích hoạt chế độ thẩm mỹ nâng cao
    use_enhanced = success_rate >= 100.0
    prompt_name = "review_prompt_enhanced" if use_enhanced else "review_prompt"
    mode_text = "Thẩm mỹ & Bố cục (Enhanced Vision)" if use_enhanced else "Sửa lỗi kỹ thuật (Standard Log)"
    
    print(f"\n[AGENT REVIEWER]: Kiểm duyệt [{mode_text}] - Thành công: {scenes_rendered}/{total_scenes} ({success_rate:.1f}%)")
    
    # 2. Gắn biến vào Prompt
    replacements = {
        "previous_reviews": format_previous_reviews(previous_reviews),
        "video_code": code,
        "execution_logs": logs,
        "video_data": video_data, # [NÂNG CẤP] Nạp vào prompt
        "success_rate": f"{success_rate:.1f}",
        "scenes_rendered": scenes_rendered,
        "total_scenes": total_scenes
    }
        
    review_content = format_prompt(prompt_name, replacements)
    
    # 3. Kích hoạt Mắt thần: Gửi kèm ảnh nếu có bất kỳ khung hình nào render thành công
    image_paths = frames if len(frames) > 0 else []
    
    # 4. Gọi LLM vạn năng qua LiteLLM
    review_text = review_manim_code(model_name, review_content, image_paths)
    return review_text