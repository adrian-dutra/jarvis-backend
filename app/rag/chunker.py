def split_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("overlap deve ser menor que chunk_size")

    cleaned_text = " ".join(text.split())
    if not cleaned_text:
        return []

    chunks: list[str] = []
    step = chunk_size - overlap

    for start in range(0, len(cleaned_text), step):
        chunk = cleaned_text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(cleaned_text):
            break

    return chunks
