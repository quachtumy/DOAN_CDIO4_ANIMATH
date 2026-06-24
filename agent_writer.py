from utils.llm import generate_manim_code
from utils.prompt import format_prompt
from utils.parsing import parse_code_block

def generate_initial_code(model_name: str, video_data: str) -> str:
    """Kỹ năng 1: Sinh mã Manim lần đầu tiên dựa trên video_data."""
    print(f"\n[AGENT WRITER]: Đang sinh code lần đầu (Model: {model_name})...")
    
    # Lấy prompt từ file init_prompt.txt
    system_prompt = format_prompt("init_prompt", {"video_data": video_data})
    user_prompt = "Start now by creating the code for the video, do not respond with anything else."
    
    raw_response = generate_manim_code(model_name, system_prompt, user_prompt)
    
    # Dọn dẹp markdown
    clean_code = parse_code_block(raw_response)
    return clean_code

def generate_code_revision(model_name: str, current_code: str, review: str, video_data: str, cycle_num: int) -> str:
    """Kỹ năng 2: Sửa lại mã Manim dựa trên Feedback của Agent Reviewer."""
    print(f"\n[AGENT WRITER]: Đang sửa code vòng {cycle_num} dựa trên Feedback (Model: {model_name})...")
    
    # Giữ nguyên bối cảnh kịch bản
    system_prompt = format_prompt("init_prompt", {"video_data": video_data})
    
    # Nạp code lỗi và feedback vào prompt
    revision_prompt = (
        f"Here is the current code:\n\n```python\n{current_code}\n```\n\n"
        f"Here is some feedback on your code:\n\n<review>\n{review}\n</review>\n\n"
        f"Please implement the suggestions and respond with the whole script. Do not leave anything out."
    )
    
    raw_response = generate_manim_code(model_name, system_prompt, revision_prompt)
    
    clean_code = parse_code_block(raw_response)
    return clean_code