from utils.llm import generate_manim_code
from utils.prompt import format_prompt

def generate_video_plan(model_name: str, user_request: str) -> str:
    """Agent 0 (Đạo diễn): Phân tích yêu cầu ngắn và sinh ra kịch bản chi tiết."""
    print(f"\n[AGENT ĐẠO DIỄN]: Đang phân tích yêu cầu và viết kịch bản chi tiết (Model: {model_name})...")
    
    # System prompt định hình vai trò
    system_prompt = "You are an expert Manim Animation Director and Prompt Engineer."
    
    # Nạp yêu cầu của người dùng vào khuôn mẫu prompt
    user_prompt = format_prompt("direct_prompt", {"user_request": user_request})
    
    # Gọi LLM (Tái sử dụng hàm generate_manim_code vì nó gọi text cơ bản)
    detailed_video_data = generate_manim_code(model_name, system_prompt, user_prompt)
    
    return detailed_video_data.strip()