"""Legal letter generation using Jinja2 templates and ReportLab PDF output."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape

from privacytool.core.logger import get_logger
from privacytool.core.models import PiiProfile

log = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parents[3] / "templates" / "letters"

LetterType = Literal["gdpr", "ccpa", "general"]

_TEMPLATE_MAP: dict[LetterType, str] = {
    "gdpr": "gdpr_article17.j2",
    "ccpa": "ccpa_deletion.j2",
    "general": "general_deletion.j2",
}

_JURISDICTION_MAP: dict[LetterType, str] = {
    "gdpr": "European Union (GDPR)",
    "ccpa": "California, USA (CCPA/CPRA)",
    "general": "General / Unspecified",
}


def _get_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape([]),
        keep_trailing_newline=True,
    )


def render_letter(
    letter_type: LetterType,
    profile: PiiProfile,
    target_site: str,
    urls: list[str],
    target_url: str = "",
) -> str:
    """Render a letter template and return the text content."""
    env = _get_env()
    template_name = _TEMPLATE_MAP[letter_type]
    template = env.get_template(template_name)

    context = {
        "full_name": profile.full_name or "[YOUR NAME]",
        "address": profile.addresses[0] if profile.addresses else "",
        "emails": profile.emails,
        "phones": profile.phones,
        "dob": profile.dob,
        "date": date.today().isoformat(),
        "target_site": target_site,
        "target_url": target_url,
        "urls": urls,
        "jurisdiction": _JURISDICTION_MAP[letter_type],
        "version": "0.1.0",
    }
    return template.render(**context)


def save_txt(text: str, output_path: str | Path) -> None:
    """Write letter text to a .txt file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(text, encoding="utf-8")
    log.info("Letter saved to %s", output_path)


def save_pdf(text: str, output_path: str | Path) -> None:
    """Render letter text to a PDF using ReportLab."""
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as exc:
        raise ImportError("reportlab is required for PDF output: pip install reportlab") from exc

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )
    styles = getSampleStyleSheet()
    story = []
    for line in text.splitlines():
        if line.strip():
            para_style = styles["BodyText"]
            story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;"), para_style))
        else:
            story.append(Spacer(1, 0.15 * inch))

    doc.build(story)
    log.info("PDF letter saved to %s", output_path)


def generate_letter(
    letter_type: LetterType,
    profile: PiiProfile,
    target_site: str,
    urls: list[str],
    output_dir: str | Path,
    target_url: str = "",
    formats: list[str] | None = None,
) -> dict[str, str]:
    """Generate a letter in one or more formats.

    Returns a dict mapping format name to output path.
    """
    if formats is None:
        formats = ["txt", "pdf"]

    text = render_letter(letter_type, profile, target_site, urls, target_url)

    output_dir = Path(output_dir)
    safe_site = target_site.replace("/", "_").replace(".", "_")
    base_name = f"{letter_type}_{safe_site}_{date.today().isoformat()}"

    results: dict[str, str] = {}
    if "txt" in formats:
        txt_path = output_dir / f"{base_name}.txt"
        save_txt(text, txt_path)
        results["txt"] = str(txt_path)
    if "pdf" in formats:
        pdf_path = output_dir / f"{base_name}.pdf"
        save_pdf(text, pdf_path)
        results["pdf"] = str(pdf_path)

    return results
