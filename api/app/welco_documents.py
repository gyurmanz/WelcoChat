# app/welco_documents.py
"""Text extraction for documents uploaded into a Kaptila Welco knowledge base.
Extracted text is merged into the LLM prompt at answer-time (see
routers/welco.py widget_message) — this module only turns file bytes into
plain text.
"""

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES_PER_INSTANCE = 20
MAX_DOC_CHARS_TOTAL = 60_000


def extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()

    if lower.endswith(".txt"):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")

    if lower.endswith(".pdf"):
        import io
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if lower.endswith(".docx"):
        import io
        import docx

        document = docx.Document(io.BytesIO(content))
        return "\n".join(p.text for p in document.paragraphs)

    if lower.endswith(".doc"):
        raise ValueError("Legacy .doc files aren't supported — please save as .docx, .pdf, or .txt")

    raise ValueError("Unsupported file type — please upload .docx, .pdf, or .txt")
