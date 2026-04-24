import anthropic
import json
import re

MODEL = "claude-opus-4-5"


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def call_claude_with_pdf(
    system_prompt: str,
    user_prompt: str,
    pdf_b64: str,
) -> str:
    """
    Trimite PDF-ul direct la Claude (metoda preferata).
    Claude citeste nativ PDF-ul fara extragere intermediara.
    """
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": user_prompt,
                    },
                ],
            }
        ],
    )
    return response.content[0].text


def call_claude_with_text(
    system_prompt: str,
    user_prompt: str,
    extracted_text: str,
) -> str:
    """
    Fallback: trimite textul extras din PDF.
    Folosit cand PDF-ul e prea mare sau e scanat.
    """
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"{user_prompt}\n\n--- CONTINUT DOCUMENT ---\n{extracted_text}",
            }
        ],
    )
    return response.content[0].text


def call_claude_with_two_pdfs(
    system_prompt: str,
    user_prompt: str,
    pdf_b64_old: str,
    pdf_b64_new: str,
) -> str:
    """UC 1.3 Syllabus Diff: compara doua PDF-uri."""
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64_old,
                        },
                        "title": "Fisa disciplinei - VECHE",
                    },
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64_new,
                        },
                        "title": "Fisa disciplinei - NOUA",
                    },
                    {
                        "type": "text",
                        "text": user_prompt,
                    },
                ],
            }
        ],
    )
    return response.content[0].text


def parse_json_response(raw: str) -> dict:
    """Extrage JSON din raspunsul Claude, ignorand markdown."""
    raw = raw.strip()
    # elimina ```json ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # incearca sa gaseasca primul bloc JSON valid
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Nu s-a putut parsa JSON din raspuns: {raw[:200]}")
