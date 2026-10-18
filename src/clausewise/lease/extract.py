"""Read a lease PDF.

Two shapes turn up in practice:
- a filled-in Form 18a, where the answers (rent, bond, special terms) live in PDF form FIELDS
  and do not appear in the page text at all; and
- a printed, scanned-to-text or custom lease, where everything is page text.

Both are read. A PDF with almost no extractable text is a scan and is reported as such rather
than checked, because "no problems found" in an unreadable lease would be a lie.
"""

import io
from dataclasses import dataclass, field

from pypdf import PdfReader

FORM_18A_MARKER = "General tenancy agreement (Form 18a)"
_MIN_CHARS_PER_PAGE = 200


class ScannedPdfError(ValueError):
    """The PDF has no usable text layer (a photo or scan). OCR is a later milestone."""


@dataclass(frozen=True)
class LeaseDoc:
    text: str
    fields: dict[str, str] = field(default_factory=dict)  # filled form fields only
    pages: int = 0

    @property
    def is_form_18a(self) -> bool:
        return FORM_18A_MARKER in self.text


def read_lease(pdf: bytes) -> LeaseDoc:
    reader = PdfReader(io.BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    pages = len(reader.pages)
    if len(text.strip()) < _MIN_CHARS_PER_PAGE * max(pages, 1) * 0.5:
        raise ScannedPdfError("this PDF looks like a scan or photo; it has no readable text")

    fields: dict[str, str] = {}
    for name, value in (reader.get_form_text_fields() or {}).items():
        if value and str(value).strip():
            fields[name] = str(value).strip()
    return LeaseDoc(text=text, fields=fields, pages=pages)
