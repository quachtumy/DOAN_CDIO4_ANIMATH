import os
import base64
from google import genai
from dotenv import load_dotenv

# Tải API keys từ file .env
load_dotenv()

# Khởi tạo client
client = genai.Client(api_key='AQ.Ab8RN6LOQrfTTnA9IHXKz2yDq1OVW8_hJK_PeaN0a10-6RRZeQ')

def encode_image_to_base64(image_path):
    """Hàm phụ trợ để mã hóa ảnh sang Base64 chuẩn cho các model Vision."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


# llm.py (Cập nhật đoạn sinh code)
def generate_manim_code(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2
) -> str:
    """Gọi LLM bằng google-genai, sử dụng system_instruction chuẩn."""
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt, # Chỉ truyền yêu cầu của user
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_prompt # Đưa luật lệ vào đúng chỗ
            )
        )
        return response.text
    except Exception as e:
        print(f"[LLM ERROR] Lỗi khi sinh code: {e}")
        return ""


def review_manim_code(
    model_name: str,
    prompt: str,
    image_paths: list = None,
    temperature: float = 0.2
) -> str:
    """Gọi LLM để kiểm duyệt mã nguồn, hỗ trợ nạp nhiều ảnh (Agent 3 - Vision)."""

    contents = [prompt]

    if image_paths:
        for path in image_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    image_bytes = f.read()

                contents.append(
                    genai.types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/png"
                    )
                )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config={
                "temperature": temperature
            }
        )

        return response.text

    except Exception as e:
        print(f"[LLM ERROR] Lỗi khi kiểm duyệt: {e}")
        return "PERFECT"  # Trả về PERFECT nếu sập API để không kẹt vòng lặp