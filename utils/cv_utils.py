"""
CV text utility functions for job description extraction, formatting, and LLM output cleaning.
"""

import logging
import re

logger = logging.getLogger(__name__)


def extract_title_from_jd(text: str) -> str:
    """
    Find the most likely job title using:
    1. Lines containing "job title" markers
    2. First line with title-case pattern
    3. Fallback to first non-empty line
    """
    text = text.strip()

    TITLE_PATTERNS = [
        r"Job Title:\s*([^:\n.]+)",
        r"Position:\s*([^:\n.]+)",
        r"Role:\s*([^:\n.]+)",
        r"\bHiring\b.*?\b(for|as)\b\s*([^.\n]+)",
        r"\bLooking\b.*?\b(for)\b\s*([^.\n]+)",
        r"\bRequisition\b.*?\b(Title)\b\s*([^.\n]+)",
        r"\bSeeking\b.*?\b(a|an)\b\s*([^.\n]+)",
        r"^#+\s*(.+)$",
    ]

    role_section = re.search(r"(?i)(About the Role|Role Overview|Position Description)[\s\S]*?(?=\n\s*\n|$)", text)

    if role_section:
        role_content = role_section.group(0)
        for line in role_content.split("\n")[:3]:
            title_match = re.search(r"(?i)(?:looking|seeking|hiring)\s+(?:for|a|an)?\s*([^.:?]+)", line)
            if title_match:
                candidate = title_match.group(1).strip()
                if is_valid_title(candidate):
                    return format_title(candidate)

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for pattern in TITLE_PATTERNS:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                candidate = next((g for g in match.groups()[::-1] if g), None)
                if candidate and is_valid_title(candidate):
                    return format_title(candidate)

    for line in text.splitlines():
        line = line.strip()
        if line and is_valid_title(line):
            return format_title(line)

    return "Untitled_Job"


def is_valid_title(candidate: str) -> bool:
    """Validate title heuristics"""
    return (
        len(candidate.split()) >= 2
        and any(c.isupper() for c in candidate)
        and not re.search(r"\b(?:join|apply|click|http)\b", candidate, re.I)
        and not re.search(r"[.!?]$", candidate)
    )


def format_title(title: str) -> str:
    """Clean up title formatting"""
    title = re.sub(r"^\W+|\W+$", "", title)
    title = re.sub(r"\s+", " ", title)
    return title[:80]


def format_job_description(desc: str) -> str:
    if not desc:
        return ""
    desc = re.sub(r"^[\-\*•]\s*", "- ", desc, flags=re.MULTILINE)
    desc = re.sub(r"([^\n])(\n[\-\*])", r"\1\n\2", desc)
    desc = re.sub(r"([a-z0-9])\. ([A-Z])", r"\1.\n\n\2", desc)
    desc = re.sub(r"\n{3,}", "\n\n", desc)
    return desc.strip()


def clean_llm_output(content: str) -> str:
    """Clean LLM-generated CV markdown output."""
    cleaned = re.sub(r"^#{1,6}\s+", "## ", content, flags=re.MULTILINE)

    if not re.search(r"^## ", cleaned, flags=re.MULTILINE):
        cleaned = "## PROFESSIONAL EXPERIENCE\n\n" + cleaned

    cleaned = re.sub(r"\*\*\s+(\w+:)", r"**\1", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s+\*\*", "**", cleaned, flags=re.MULTILINE)

    def _add_pipe(m):
        company = m.group(1).strip()
        rest = m.group(2).strip()
        return f"**{company}** \\| {rest}"

    cleaned = re.sub(
        r"^\*\*(.+?)\*\*\s+(?!\\\|)(.*?\(\d{4}[–\-–]\d{4,}|Present\))", _add_pipe, cleaned, flags=re.MULTILINE
    )
    cleaned = re.sub(r"^(.*?)\s*\|\s*(- .+)$", r"\1\n\2", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def strip_llm_contact_block(md: str, contact: dict) -> str:
    """Remove duplicate contact block pattern [NAME] [ADDRESS] [PHONE] followed by **"""
    if not contact.get("name"):
        return md

    name = re.escape(contact["name"])
    address = re.escape(contact.get("address", ""))
    phone = re.escape(contact.get("phone", ""))

    pattern = (
        r"^"
        rf"{name}.*?"
        rf"({address}.*?)?"
        rf"({phone}.*?)?"
        r"\n"
        r"\*\*"
        r"\s*"
        r"\n"
    )

    return re.sub(pattern, "", md, flags=re.MULTILINE)


def extract_contact_info(cv_text: str) -> dict:
    """
    Extract name, email, phone, github, address from first ~10 CV lines.
    """
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
    info = {}
    if not lines:
        return info
    info["name"] = lines[0]
    for line in lines[1:10]:
        if "://" not in line and "@" in line:
            m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
            if m:
                info["email"] = m.group(0)
        if re.search(r"\+?\d[\d\-\s\(\)]{7,}\d", line):
            info["phone"] = line
        if "github.com" in line.lower():
            info["github"] = line
        if "," in line and re.search(r"\d{1,5}\s+\w+", line):
            info["address"] = line
    return info
