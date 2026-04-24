import base64
import pdfplumber
import io


def extract_text_pdfplumber(pdf_bytes: bytes) -> str:
    """Extrage text din PDF folosind pdfplumber (fara API)."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            t = page.extract_text()
            if t:
                text_parts.append(f"--- Pagina {i+1} ---\n{t}")
    return "\n\n".join(text_parts)


def pdf_to_base64(pdf_bytes: bytes) -> str:
    """Converteste PDF la base64 pentru trimitere directa la Claude API."""
    return base64.standard_b64encode(pdf_bytes).decode("utf-8")


def is_text_pdf(pdf_bytes: bytes, min_chars: int = 200) -> bool:
    """Verifica daca PDF-ul contine text extractibil (nu e scanat)."""
    text = extract_text_pdfplumber(pdf_bytes)
    return len(text.strip()) >= min_chars
