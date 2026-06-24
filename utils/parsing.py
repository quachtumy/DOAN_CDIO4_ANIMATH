import re

def parse_code_block(text: str) -> str:
    """Trích xuất khối mã Python từ câu trả lời của LLM."""
    match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback nếu AI không viết chữ 'python'
    match = re.search(r"```\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
        
    return text.strip()