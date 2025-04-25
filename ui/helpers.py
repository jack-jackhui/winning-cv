# ui/helpers.py
import re
import requests

def format_job_description(desc: str) -> str:
    if not desc:
        return ""
    # Replace bullet characters with markdown bullets
    desc = re.sub(r'^[\-\*\u2022]\s*', '- ', desc, flags=re.MULTILINE)
    # Add a newline before bullets if missing
    desc = re.sub(r'([^\n])(\n[\-\*])', r'\1\n\2', desc)
    # Ensure double newlines after periods (for paragraphs)
    desc = re.sub(r'([a-z0-9])\. ([A-Z])', r'\1.\n\n\2', desc)
    # Optional: collapse excessive linebreaks
    desc = re.sub(r'\n{3,}', '\n\n', desc)
    return desc.strip()

def upload_pdf_to_wordpress(
        file_path: str,
        filename: str,
        wp_site: str,
        wp_user: str,
        wp_app_password: str
) -> str:
    """
    Upload a PDF to WordPress Media Library and return its public URL.

    Args:
      file_path: local path to the PDF
      filename:  the filename to appear in WP
      wp_site:   e.g. "https://your‑site.com"
      wp_user:   your WP username (or email)
      wp_app_password: the application password you generated
    Returns:
      source_url of the uploaded media (string)
    """
    media_endpoint = wp_site.rstrip("/") + "/wp-json/wp/v2/media"
    headers = {
        # Instruct WP what filename you're uploading
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    # Basic Auth with username:application_password
    auth = (wp_user, wp_app_password)
    with open(file_path, "rb") as pdf_file:
        files = {
            "file": (filename, pdf_file, "application/pdf")
        }
        resp = requests.post(
            media_endpoint,
            headers=headers,
            auth=auth,
            files=files,
            timeout=30
        )
    resp.raise_for_status()
    data = resp.json()
    # WP returns a JSON blob like:
    #  {
    #    "id": 123,
    #    "source_url": "https://your‑site.com/wp‑content/uploads/2025/04/whatever.pdf",
    #    …
    #  }
    return data["source_url"]

def extract_title_from_jd(text: str) -> str:
    """
    Find the most likely job title using:
    1. Lines containing "job title" markers
    2. First line with title-case pattern
    3. Fallback to first non-empty line
    """
    text = text.strip()

    # Pattern 1: Look for explicit title markers
    TITLE_PATTERNS = [
        r"Job Title:\s*([^:\n.]+)",  # "Job Title: VP of Systems"
        r"Position:\s*([^:\n.]+)",
        r"Role:\s*([^:\n.]+)",
        r"\bHiring\b.*?\b(for|as)\b\s*([^.\n]+)",
        r"\bLooking\b.*?\b(for)\b\s*([^.\n]+)",
        r"\bRequisition\b.*?\b(Title)\b\s*([^.\n]+)",
        r"\bSeeking\b.*?\b(a|an)\b\s*([^.\n]+)",
        r"^#+\s*(.+)$",  # Markdown headers
    ]

    # 1. Try to find the "About the Role" section
    role_section = re.search(
        r'(?i)(About the Role|Role Overview|Position Description)[\s\S]*?(?=\n\s*\n|$)',
        text
    )

    if role_section:
        # 2. Look in first 3 lines of role section
        role_content = role_section.group(0)
        for line in role_content.split('\n')[:3]:
            # 3. Match title patterns with validation
            title_match = re.search(
                r'(?i)(?:looking|seeking|hiring)\s+(?:for|a|an)?\s*([^.:?]+)',
                line
            )
            if title_match:
                candidate = title_match.group(1).strip()
                if is_valid_title(candidate):
                    return format_title(candidate)

    # 4. Fallback to original patterns with validation
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Original patterns with validation
        for pattern in TITLE_PATTERNS:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                candidate = next((g for g in match.groups()[::-1] if g), None)
                if candidate and is_valid_title(candidate):
                    return format_title(candidate)

    # 5. Final fallback to first title-case line
    for line in text.splitlines():
        line = line.strip()
        if line and is_valid_title(line):
            return format_title(line)

    return "Untitled_Job"

def is_valid_title(candidate: str) -> bool:
    """Validate title heuristics"""
    return (
        len(candidate.split()) >= 2 and  # At least 2 words
        any(c.isupper() for c in candidate) and  # Contains uppercase
        not re.search(r'\b(?:join|apply|click|http)\b', candidate, re.I) and
        not re.search(r'[.!?]$', candidate)  # Doesn't end with punctuation
    )
def format_title(title: str) -> str:
    """Clean up title formatting"""
    title = re.sub(r'^\W+|\W+$', '', title)  # Trim edge non-words
    title = re.sub(r'\s+', ' ', title)  # Collapse whitespace
    return title[:80]

def clean_llm_output(content: str) -> str:
    # Do NOT strip content before first header!
    # Convert ALL headers to ## level
    cleaned = re.sub(r'^#{1,6}\s+', '## ', content, flags=re.MULTILINE)

    # If no headers exist, add one for "PROFESSIONAL EXPERIENCE"
    if not re.search(r'^## ', cleaned, flags=re.MULTILINE):
        cleaned = '## PROFESSIONAL EXPERIENCE\n\n' + cleaned

    # Fix lines that start with "** " instead of "**"
    cleaned = re.sub(r'\*\*\s+(\w+:)', r'**\1', cleaned, flags=re.MULTILINE)

    # Remove leading spaces before bolded sub‑headers in KEY ACHIEVEMENTS
    cleaned = re.sub(r'^\s+\*\*', '**', cleaned, flags=re.MULTILINE)
    def _add_pipe(m):
        company = m.group(1).strip()
        rest    = m.group(2).strip()
        return f"**{company}** \\| {rest}"
    # Only lines with years or date range get the pipe (EMPLOYMENT HISTORY)
    cleaned = re.sub(
        r'^\*\*(.+?)\*\*\s+(?!\\\|)(.*?\(\d{4}[\u2013\-–]\d{4,}|Present\))',
        _add_pipe,
        cleaned,
        flags=re.MULTILINE
    )
    # KEY ACHIEVEMENTS: Split subheader | - Bullet to subheader\n- Bullet
    cleaned = re.sub(
        r"^(.*?)\s*\|\s*(- .+)$",
        r"\1\n\2",
        cleaned,
        flags=re.MULTILINE
    )
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

def strip_llm_contact_block(md, contact):
    """
    Remove only the duplicate contact line pattern:
    [NAME] [ADDRESS] [PHONE]
    **
    """
    if not contact.get('name'):
        return md

    # Escape special regex characters in contact info
    name = re.escape(contact['name'])
    address = re.escape(contact.get('address', ''))
    phone = re.escape(contact.get('phone', ''))

    # Build pattern to match: Name + Address + Phone + newline + **
    pattern = (
        r'^'  # Start of line
        rf'{name}.*?'  # Name + any characters
        rf'({address}.*?)?'  # Optional address
        rf'({phone}.*?)?'  # Optional phone
        r'\n'  # Newline
        r'\*\*'  # Double asterisks
        r'\s*'  # Optional whitespace
        r'\n'  # Newline
    )

    return re.sub(pattern, '', md, flags=re.MULTILINE)

def extract_contact_info(cv_text: str) -> dict:
    """
    Look at the first ~10 non‑blank lines of the user's CV text
    and pull out name (line #1), email, phone, github, and address.
    """
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
    info = {}
    if not lines:
        return info
    # 1) Full name is line #1
    info['name'] = lines[0]
    # 2) Scan next few lines for the other pieces
    for line in lines[1:10]:
        # Email
        if '://' not in line and '@' in line:
            m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
            if m:
                info['email'] = m.group(0)
        # Phone (approximate)
        if re.search(r'\+?\d[\d\-\s\(\)]{7,}\d', line):
            info['phone'] = line
        # GitHub
        if 'github.com' in line.lower():
            info['github'] = line
        # Address (comma + number)
        if ',' in line and re.search(r'\d{1,5}\s+\w+', line):
            info['address'] = line
    return info