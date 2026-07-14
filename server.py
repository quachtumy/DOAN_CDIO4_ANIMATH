import os
import json
import asyncio
import shutil  # THÊM THƯ VIỆN NÀY ĐỂ XÓA FOLDER CŨ
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import các hàm từ hệ thống LangGraph của bạn
from workflow_graph import app_graph
from utils.rendering import concatenate_videos, extract_scene_class_names
from utils.cache_manager import check_video_cache, save_video_to_cache

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "media/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

@app.websocket("/ws/generate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Giao diện đã kết nối thành công!")
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # 1. LẤY CÂU HỎI VÀ MẢNG LỊCH SỬ TỪ GIAO DIỆN
            raw_user_query = payload.get("query", "")
            chat_history = payload.get("history", []) 
            
            if not raw_user_query:
                continue

            print(f"\n[YÊU CẦU MỚI TỪ UI]: {raw_user_query}")
            
            await websocket.send_json({
                "type": "info", 
                "message": f"Mình đã nhận được yêu cầu: '{raw_user_query}'. Đang tiến hành xử lý..."
            })

            # =======================================================================
            # ĐIỂM MỚI: BƠM NGỮ CẢNH LỊCH SỬ VÀO CÂU HỎI CHO LANGGRAPH
            # =======================================================================
            enhanced_query = raw_user_query
            
            if len(chat_history) > 1:
                history_text = "LỊCH SỬ HỘI THOẠI TRƯỚC ĐÓ (Dùng để hiểu các từ ngữ thay thế như 'đó', 'này'):\n"
                for msg in chat_history[:-1]: # Bỏ qua câu cuối vì nó chính là câu hỏi hiện tại
                    role_name = "Người dùng" if msg["role"] == "user" else "AI"
                    history_text += f"- {role_name}: {msg['content']}\n"
                
                history_text += f"\nCÂU HỎI HIỆN TẠI CẦN BẠN GIẢI QUYẾT: {raw_user_query}\n"
                history_text += "(Yêu cầu: Hãy phân tích lịch sử trên để hiểu rõ ý định của câu hỏi hiện tại và tạo video tương ứng)."
                
                enhanced_query = history_text # Ghi đè thành câu hỏi đã nâng cấp
            # =======================================================================

            # --- KIỂM TRA CACHE TỐC ĐỘ CAO ---
            await websocket.send_json({"type": "progress", "step": 1, "message": "Đang kiểm tra kho dữ liệu nhúng (Cache)..."})
            
            # Lưu ý: Cache vẫn dùng câu hỏi gốc (raw_user_query) để tìm kiếm cho chuẩn xác
            cached_video = await asyncio.to_thread(check_video_cache, raw_user_query) 
            
            if cached_video and os.path.exists(cached_video):
                await websocket.send_json({"type": "progress", "step": 4, "message": "⚡ Tìm thấy video trùng khớp trong Cache!"})
                await websocket.send_json({
                    "type": "done",
                    "video_path": cached_video.replace("\\", "/")
                })
                continue

            # =======================================================================
            # BƯỚC DỌN RÁC QUAN TRỌNG: XÓA SẠCH SCENE CŨ TRƯỚC KHI CHẠY AI
            # =======================================================================
            temp_scene_dir = f"{OUTPUT_DIR}/videos/temp_scene"
            if os.path.exists(temp_scene_dir):
                try:
                    shutil.rmtree(temp_scene_dir)
                    print("[DỌN DẸP]: Đã xóa sạch thư mục video nháp cũ.")
                except Exception as e:
                    print(f"Không thể xóa thư mục tạm: {e}")
            os.makedirs(temp_scene_dir, exist_ok=True)

            # --- KHỞI ĐỘNG HỆ THỐNG AI ---
            initial_state = {
                "user_query": enhanced_query, # <--- TRUYỀN CÂU HỎI ĐÃ NÂNG CẤP VÀO LANGGRAPH
                "current_cycle": 1,
                "max_cycles": 3,
                "is_perfect": False,
                "video_paths": []
            }
            
            final_state = initial_state.copy()
            best_video_paths = []
            
            try:
                async for output in app_graph.astream(initial_state):
                    for node_name, node_state in output.items():
                        final_state.update(node_state)
                        
                        # Cập nhật két sắt chống suy thoái AI
                        current_paths = node_state.get("video_paths", [])
                        if current_paths and len(current_paths) >= len(best_video_paths):
                            best_video_paths = current_paths.copy()

                        async def safe_send(step_num, msg):
                            try:
                                await websocket.send_json({"type": "progress", "step": step_num, "message": msg})
                            except:
                                pass 

                        if node_name == "check_feasibility":
                            await safe_send(1, "Bước 1: Phân tích tính khả thi Toán học...")
                        elif node_name == "generate_description":
                            await safe_send(1, "Bước 1: Đạo diễn AI đang lên kịch bản...")
                        elif node_name == "generate_initial_code":
                            await safe_send(2, "Bước 2: Thợ code đang biên dịch mã Manim...")
                        elif node_name == "test_and_review":
                            await safe_send(3, "Bước 3: Đang render video & kiểm duyệt chất lượng...")
                        elif node_name == "fix_code_with_llm":
                            cycle = final_state.get('current_cycle', 1)
                            await safe_send(3, f"Bước 3: Phát hiện lỗi, đang tự động sửa (Vòng {cycle})...")
            except Exception as e:
                print(f"Lỗi Graph: {e}")

            # =======================================================================
            # LOGIC CHUẨN TỪ MAIN.PY: LẤY VIDEO TỪ STATE LANGGRAPH TRƯỚC
            # =======================================================================
            
            # 1. Ưu tiên tuyệt đối lấy danh sách video mà AI vừa báo cáo là đã render xong
            video_paths = final_state.get("video_paths", [])
            
            # (Bảo vệ chống suy thoái) Nếu vòng cuối lỗi làm rỗng danh sách, lấy lại bản tốt nhất đã lưu
            if not video_paths and best_video_paths:
                video_paths = best_video_paths
                print(f"Phục hồi {len(video_paths)} scene từ két sắt an toàn.")

            # 2. BỘ LỌC THÔNG MINH (CHỈ KÍCH HOẠT KHI THỰC SỰ TRỐNG BỘ NHỚ)
            if not video_paths and final_state.get("current_code"):
                print("Vòng lặp cuối bị lỗi, hệ thống tiến hành phân tích mã nguồn để thu hồi đúng video...")
                await websocket.send_json({"type": "progress", "step": 3, "message": "Đang trích xuất danh sách phân cảnh từ mã nguồn..."})
                
                latest_code = final_state["current_code"]
                active_scenes = extract_scene_class_names(latest_code)
                
                if active_scenes:
                    print(f"Các phân cảnh được định nghĩa trong code lần này: {active_scenes}")
                    recovered_paths = []
                    for scene in active_scenes:
                        possible_paths = [
                            f"{OUTPUT_DIR}/videos/temp_scene/480p15/{scene}.mp4",
                            f"{OUTPUT_DIR}/videos/temp_scene/1080p60/{scene}.mp4",
                            f"{OUTPUT_DIR}/videos/temp_scene/720p30/{scene}.mp4"
                        ]
                        
                        for path in possible_paths:
                            if os.path.exists(path):
                                recovered_paths.append(path)
                                break 
                    
                    video_paths = recovered_paths

            # Kiểm tra chốt chặn cuối cùng
            if not video_paths:
                await websocket.send_json({
                    "type": "info", 
                    "message": "Rất tiếc, AI gặp lỗi logic khiến video không thể render thành công. Bạn hãy thử đặt lại câu hỏi nhé."
                })
                await websocket.send_json({"type": "done", "video_path": ""})
                continue

            # ==================================================
            # TIẾN HÀNH GỘP CHÍNH XÁC DANH SÁCH ĐÃ LỌC
            # ==================================================
            await websocket.send_json({"type": "progress", "step": 4, "message": f"Bước 4: Đang gộp {len(video_paths)} phân cảnh chuẩn xác..."})
            
            if len(video_paths) > 1:
                print(f"\nSẵn sàng gộp {len(video_paths)} phân cảnh chuẩn xác của lần chạy này...")
                final_merged_video = await asyncio.to_thread(concatenate_videos, video_paths, OUTPUT_DIR)
            else:
                print("\nChỉ có 1 phân cảnh hợp lệ...")
                final_merged_video = video_paths[0]
                
            # Đưa vào kho Cache vĩnh viễn
            # Đưa vào kho Cache vĩnh viễn
            await asyncio.to_thread(save_video_to_cache, raw_user_query, final_merged_video)
            print("[THÀNH CÔNG] Đã tự động phê duyệt và đưa vào kho Cache vĩnh viễn!")
            
            # Gửi link Video hoàn chỉnh lên cho UI phát hình
            await websocket.send_json({
                "type": "done",
                "video_path": final_merged_video.replace("\\", "/")
            })

    except WebSocketDisconnect:
        print("[WebSocket] Giao diện đã ngắt kết nối.")
    except Exception as e:
        print(f"[LỖI HỆ THỐNG]: {e}")
        try:
            await websocket.send_json({"type": "info", "message": f"Có lỗi máy chủ xảy ra: {str(e)}"})
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    print("Khởi động Animath Backend API tại: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)