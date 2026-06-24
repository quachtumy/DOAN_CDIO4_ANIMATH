def format_prompt(prompt_name: str, replacements: dict) -> str:
    """Đọc file prompt txt và điền các biến vào."""
    with open(f"prompts/{prompt_name}.txt", encoding="utf-8") as file:
        prompt_template = file.read()

    for placeholder, value in replacements.items():
        prompt_template = prompt_template.replace(f"{{{placeholder}}}", str(value))
    return prompt_template

def format_previous_reviews(previous_reviews: list) -> str:
    """Gói các nhận xét cũ vào thẻ <review_x>."""
    xml_formatted = [
        f"<review_{idx}>\n{feedback}\n</review_{idx}>"
        for idx, feedback in enumerate(previous_reviews)
    ]
    return "\n".join(xml_formatted)