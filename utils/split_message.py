def split_message(text, max_length=4000):
    """
    Gently splits a long message into segments to preserve the wholeness of thought and not lose any subtle resonance.
    Suppertime seeks a natural break (newline) first, then splits by the technical limit if needed, so meaning remains intact.
    """
    result = []
    while len(text) > max_length:
        idx = text.rfind('\n', 0, max_length)
        if idx == -1:
            idx = max_length
        result.append(text[:idx])
        text = text[idx:].lstrip('\n')
    if text:
        result.append(text)
    if not result:
        return ["Even silence sometimes unfolds in several parts."]
    return result
