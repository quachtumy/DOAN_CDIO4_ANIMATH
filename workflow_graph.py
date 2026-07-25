from langgraph.graph import StateGraph, START, END
from state import ManimGraphState
import os

# --- Import các Agent cũ của bạn ---
# Giả sử bạn đã có các hàm LLM trong agent_planner, agent_writer, agent_reviewer
from agent_director import generate_video_plan
from agent_writer import generate_initial_code, generate_code_revision
from agent_reviewer import generate_review
from utils.rendering import extract_scene_class_names, run_manim_script, extract_highest_density_frames
from utils.cache_manager import check_video_cache # Import hàm kiểm tra

MODEL_NAME = "gemini-flash-lite-latest" # Flash Lite của bạn

# ==========================================
# CÁC NODE (TRẠM KIỂM SOÁT)
# ==========================================

def check_cache_node(state: ManimGraphState):
    """Trạm kiểm tra bộ nhớ đệm trước khi chạy AI"""
    query = state["user_query"]
    print(f"\n🔍 [HỆ THỐNG]: Đang đối chiếu câu hỏi '{query}' với kho lưu trữ nhúng...")
    
    cached_path = check_video_cache(query)
    return {"cached_video_path": cached_path}

# Router điều phối luồng thông minh sau khi check cache
def route_after_cache(state: ManimGraphState):
    if state.get("cached_video_path"):
        return END # Nếu có cache rồi thì nhảy thẳng ra đích kết thúc, không làm gì thêm!
    return "check_feasibility" # Nếu chưa có cache, tiếp tục quy trình cho AI viết code

def check_feasibility(state: ManimGraphState):
    """Trạm 1: Giống repo, kiểm tra xem yêu cầu có vẽ bằng toán được không"""
    print("[HỆ THỐNG]: Đang kiểm tra tính khả thi...")
    # (Tạm thời bỏ qua logic LLM phức tạp, mặc định cho qua để tiết kiệm token)
    return {"is_feasible": True, "feasibility_reason": "Hợp lệ"}

def generate_description(state: ManimGraphState):
    """Trạm 2: Đạo diễn viết kịch bản chi tiết"""
    query = state["user_query"]
    description = generate_video_plan(MODEL_NAME, query)
    print("\n[ĐẠO DIỄN]: Đã lên kịch bản xong.")
    print(description)
    return {"detailed_description": description}

def generate_initial_manim_code(state: ManimGraphState):
    """Trạm 3: Thợ Code viết bản nháp đầu tiên"""
    description = state["detailed_description"]
    code = generate_initial_code(MODEL_NAME, description)
    return {"current_code": code, "current_cycle": 1}

def test_and_review_code(state: ManimGraphState):
    """Trạm 4: Chạy thử và Mắt thần AI kiểm duyệt"""
    code = state["current_code"]
    cycle = state["current_cycle"]
    description = state["detailed_description"]
    
    print(f"\n[HỆ THỐNG]: Vòng lặp {cycle} - Đang Render để kiểm duyệt...")
    
    # Ghi code ra file tạm
    code_path = "media/output/temp_scene.py"
    with open(code_path, "w", encoding="utf-8") as f:
         f.write(code)
    
    # Render (Tái sử dụng logic cũ của bạn)
    scenes = extract_scene_class_names(code) or ["CustomScene"]
    all_success = True
    combined_logs = ""
    all_frames = []
    current_video_paths = []
    
    for scene in scenes:
        success, logs = run_manim_script(code_path, "media/output", scene)
        combined_logs += f"\n{logs}\n"
        if success:
            video_path = f"media/output/videos/temp_scene/480p15/{scene}.mp4"

            # Chỉ lưu nếu file thực sự tồn tại
            if os.path.exists(video_path):
                current_video_paths.append(video_path)

                frames = extract_highest_density_frames(
                    video_path,
                    f"media/output/frames_{scene}",
                    count=3
                )
                all_frames.extend(frames)
            else:
                all_success = False
                combined_logs += (
                    f"\nKhông tìm thấy file video sau khi render Scene '{scene}'.\n"
                )
        else:
            all_success = False

    total_scenes = len(scenes)
    scenes_rendered = len(current_video_paths)

    success_rate = (
        scenes_rendered / total_scenes * 100
        if total_scenes > 0 else 0
    )
    previous_reviews = []

    if state.get("latest_review"):
        previous_reviews.append(state["latest_review"])
    
    review = generate_review(MODEL_NAME, code, combined_logs, all_frames, previous_reviews, all_success, description, success_rate, scenes_rendered, total_scenes)
    print(f"\n[GIÁM KHẢO]:\n{review}")
    
    is_perfect = "[ALL_PERFECT_APPROVED]" in review.upper()
    
    # ==========================================================
    # [CHỐT CHẶN AN TOÀN MỚI]: KHÔNG CÓ VIDEO THÌ KHÔNG THỂ PERFECT
    # ==========================================================
    if not current_video_paths:
        is_perfect = False
        print("Cảnh báo: LLM duyệt qua nhưng hệ thống không tìm thấy file video (Code bị lỗi Render).")
        # Nếu LLM bị sập hẳn, ta lấy luôn log lỗi của terminal gán làm review cho Coder sửa
        if "SYSTEM_REVIEW_FAILED" in review:
            review = "Hệ thống kiểm duyệt bị lỗi kết nối API. Dưới đây là log lỗi render của terminal, hãy tự đọc và sửa code Manim:\n" + combined_logs
            
    return {
        "latest_review": review, 
        "is_perfect": is_perfect,
        "current_cycle": cycle + 1,
        "video_paths": current_video_paths 
    }

def fix_code_with_llm(state: ManimGraphState):
    """Trạm 5: Thợ code sửa lỗi dựa trên Review"""
    code = state["current_code"]
    review = state["latest_review"]
    description = state["detailed_description"]
    cycle = state["current_cycle"]
    
    new_code = generate_code_revision(MODEL_NAME, code, review, description, cycle)
    return {"current_code": new_code}

# ==========================================
# ĐIỀU PHỐI LUỒNG (ROUTER)
# ==========================================

def route_after_feasibility(state: ManimGraphState):
    if state["is_feasible"]: return "generate_description"
    return END

def route_after_review(state: ManimGraphState):
    if state["is_perfect"]: return END
    if state["current_cycle"] > state["max_cycles"]: return END
    return "fix_code_with_llm"

# ==========================================
# XÂY DỰNG ĐỒ THỊ (THE GRAPH)
# ==========================================

workflow = StateGraph(ManimGraphState)

# Thêm các Trạm vào bản đồ
workflow.add_node("check_cache", check_cache_node)
workflow.add_node("check_feasibility", check_feasibility)
workflow.add_node("generate_description", generate_description)
workflow.add_node("generate_initial_code", generate_initial_manim_code)
workflow.add_node("test_and_review", test_and_review_code)
workflow.add_node("fix_code_with_llm", fix_code_with_llm)

# Nối các Trạm lại với nhau bằng Mũi tên (Edges)
workflow.add_edge(START, "check_cache")
workflow.add_conditional_edges("check_cache", route_after_cache, {
    END: END,
    "check_feasibility": "check_feasibility"
})
workflow.add_conditional_edges(
    "check_feasibility", 
    route_after_feasibility, 
    {
        "generate_description": "generate_description", 
        END: END
    }
)
workflow.add_edge("generate_description", "generate_initial_code")
workflow.add_edge("generate_initial_code", "test_and_review")
workflow.add_conditional_edges("test_and_review", route_after_review, {END: END, "fix_code_with_llm": "fix_code_with_llm"})
workflow.add_edge("fix_code_with_llm", "test_and_review") # Vòng lặp sửa lỗi -> test lại

app_graph = workflow.compile()