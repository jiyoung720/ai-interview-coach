def extract_text(message) -> str:
    """Gemini 3+ 모델은 .content가 문자열이 아니라
    [{'type': 'text', 'text': '...', 'extras': {...}}] 형태의 블록 리스트로 나옴.
    thinking 블록은 건너뛰고 text 블록만 이어붙임."""
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )
