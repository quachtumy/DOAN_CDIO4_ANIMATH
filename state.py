from typing import TypedDict, List, Optional

class ManimGraphState(TypedDict):
    # Dữ liệu đầu vào
    user_query: str

    cached_video_path: Optional[str] # Khai báo biến lưu video cache nếu tìm thấy
    
    # Graph 1: Khả thi & Kịch bản (Planner)
    is_feasible: bool
    feasibility_reason: str
    detailed_description: str
    
    # Graph 2: Code & Review (Coder & Reviewer)
    current_code: str
    current_cycle: int
    max_cycles: int
    latest_review: str
    is_perfect: bool
    
    # Lịch sử và kết quả
    video_paths: List[str]
    error_logs: str