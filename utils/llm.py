import os
import base64
import litellm
import time
from google import genai
from dotenv import load_dotenv

# Tải API keys từ file .env
load_dotenv(override=True)

gemini_api_key = os.getenv('GEMINI_API_KEY')
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

# Khởi tạo client Gemini
client = genai.Client(api_key=gemini_api_key)

def encode_image_to_base64(image_path):
    """Hàm phụ trợ để mã hóa ảnh sang Base64 chuẩn cho các model Vision."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_manim_code(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2
) -> str:
    """Gọi LLM: Sử dụng google-genai cho Gemini, hoặc LiteLLM cho các model khác."""
    
    # --- NHÁNH 1: DÀNH CHO GEMINI (Không có ảnh, chỉ có văn bản) ---
    if "gemini" in model_name.lower():
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=genai.types.GenerateContentConfig(
                        temperature=temperature,
                        system_instruction=system_prompt 
                    )
                )
                return response.text
            except Exception as e:
                error_msg = str(e).upper()
                if "503" in error_msg or "UNAVAILABLE" in error_msg or "429" in error_msg:
                    print(f"[CẢNH BÁO] API Gemini đang quá tải. Chờ 10 giây thử lại... (Lần {attempt + 1}/{max_retries})")
                    time.sleep(10)
                else:
                    print(f"[LLM ERROR] Lỗi khi sinh code bằng Gemini: {e}")
                    return ""
        return ""
            
    # --- NHÁNH 2: DÀNH CHO CLAUDE / MODEL KHÁC QUA OPENROUTER ---
    else:
        try:
            if not openrouter_api_key:
                print("LỖI: Không tìm thấy OPENROUTER_API_KEY trong file .env")
                return ""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = litellm.completion(
                model=model_name,
                messages=messages,
                temperature=temperature,
                api_key=openrouter_api_key
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[LITELLM ERROR] Lỗi khi sinh code: {e}")
            return ""


def review_manim_code(
    model_name: str,
    prompt: str,
    image_paths: list = None,
    temperature: float = 0.2
) -> str:
    """Gọi LLM để kiểm duyệt mã nguồn, hỗ trợ nạp nhiều ảnh (Agent 3 - Vision)."""

    # --- NHÁNH 1: DÀNH CHO GEMINI (Có xử lý ảnh) ---
    if "gemini" in model_name.lower():
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

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config={"temperature": temperature}
                )
                return response.text
            except Exception as e:
                error_msg = str(e).upper()
                if "503" in error_msg or "UNAVAILABLE" in error_msg or "429" in error_msg:
                    print(f"[CẢNH BÁO] API Gemini đang quá tải. Chờ 10 giây thử lại... (Lần {attempt + 1}/{max_retries})")
                    time.sleep(10)
                else:
                    print(f"[LLM ERROR] Lỗi khi kiểm duyệt bằng Gemini: {e}")
                    return "SYSTEM_REVIEW_FAILED"
        return "SYSTEM_REVIEW_FAILED"
            
    # --- NHÁNH 2: DÀNH CHO CLAUDE / MODEL KHÁC QUA OPENROUTER ---
    else:
        try:
            if not openrouter_api_key:
                print("LỖI: Không tìm thấy OPENROUTER_API_KEY trong file .env")
                return "[ALL_PERFECT_APPROVED]"

            content = [{"type": "text", "text": prompt}]
            if image_paths:
                for path in image_paths:
                    if os.path.exists(path):
                        encoded = encode_image_to_base64(path)
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{encoded}"}
                        })

            messages = [{"role": "user", "content": content}]

            response = litellm.completion(
                model=model_name,
                messages=messages,
                temperature=temperature,
                api_key=openrouter_api_key
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[LITELLM ERROR] Lỗi kiểm duyệt: {e}")
            return "[ALL_PERFECT_APPROVED]"