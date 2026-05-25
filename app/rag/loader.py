from pathlib import Path


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix in {".txt", ".md"}:
        return extract_txt_text(path)

    raise ValueError("Tipo de arquivo não suportado. Envie PDF, TXT ou MD.")


def extract_pdf_text(path: Path) -> str:
    import fitz

    with fitz.open(path) as document:
        pages = [page.get_text("text") for page in document]
    return "\n".join(pages).strip()


def extract_txt_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").strip()
