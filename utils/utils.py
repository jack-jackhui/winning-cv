# utils.py
from PyPDF2 import PdfReader
from docx import Document
import io
import logging
from fpdf import FPDF
import re

class Struct:
    """Convert dict to object for config"""
    def __init__(self, **entries):
        self.__dict__.update(entries)

def extract_text_from_file(file):
    """Extract text from PDF, DOCX, or TXT files with error handling"""
    try:
        content = []
        file_bytes = file.getvalue()

        if file.type == "application/pdf":
            pdf = PdfReader(io.BytesIO(file_bytes))
            for page in pdf.pages:
                if text := page.extract_text():
                    try:
                        content.append(text.encode('utf-8').decode('utf-8'))
                    except:
                        content.append(text.encode('latin-1', 'replace').decode('latin-1'))
            # Fallback for image-based PDFs
            if not content:
                logging.warning("PDF appears to be image-based - text extraction limited")
                content = ["[PDF content requires OCR extraction]"]

        elif file.type == "text/plain":
            # Handle different encodings
            try:
                text = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text = file_bytes.decode('latin-1')
            content = [text]

        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(io.BytesIO(file_bytes))
            doc_content = []

            # Process paragraphs with proper spacing
            for para in doc.paragraphs:
                if para.text.strip():
                    doc_content.append(para.text + "\n")

            # Process tables with cell separation
            for table in doc.tables:
                for row_idx, row in enumerate(table.rows):
                    row_data = []
                    for cell in row.cells:
                        cell_text = ' '.join([p.text.strip() for p in cell.paragraphs if p.text.strip()])
                        row_data.append(cell_text)
                    doc_content.append(" | ".join(row_data))
                    if row_idx == 0:  # Add header separator
                        doc_content.append("-" * 50)

            content = doc_content  # Assign to main content list

        full_content = "\n".join(content).strip()
        full_content = re.sub(r'\n{3,}', '\n\n', full_content)
        logging.info(f"Extracted {len(full_content)} characters")
        return full_content

    except Exception as e:
        logging.error(f"Text extraction failed: {str(e)}")
        return ""

def create_pdf(content, filename="customized_cv.pdf"):
    """Create a styled PDF document from text content"""
    try:
        pdf = FPDF()
        pdf.set_margins(left=15, top=15, right=15)
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Font configuration
        pdf.add_font('Inter', '', 'fonts/Inter_18pt-Regular.ttf', uni=True)
        pdf.add_font('Inter', 'B', 'fonts/Inter_18pt-Bold.ttf', uni=True)
        font_name = 'Inter'
        base_font_size = 11  # Matches reference PDF size
        line_height = 6  # Tight line spacing from reference
        # Process content
        cleaned_content = re.sub(r'\n{3,}', '\n\n', content.strip())
        in_contact_section = False
        contact_lines = []
        current_section = None
        for line in cleaned_content.split('\n'):
            line = line.strip()
            if not line: continue
            # Title Section
            if line.startswith('# '):
                _handle_title(pdf, line[2:].strip(), font_name)
                in_contact_section = True
                continue
            # Contact Information
            if in_contact_section and line.startswith('**'):
                contact_lines.append(line.replace('**', '').strip())
                continue
            if contact_lines and not line.startswith('**'):
                _process_contact_section(pdf, contact_lines, font_name, base_font_size, line_height)
                contact_lines = []
                in_contact_section = False
                pdf.ln(6)
            # Section Headers
            if line.startswith('## '):
                current_section = line[3:].strip().upper()
                _handle_section_header(pdf, current_section, font_name)
                continue
            # Employment History - Single line format
            if line.startswith('**') and '|' in line:
                _handle_employment_entry(pdf, line, font_name, base_font_size, line_height)
                continue
            # Sub-headers in Key Achievements
            if line.startswith('**') and not '|' in line:
                _handle_subheader(pdf, line, font_name, base_font_size)
                continue
            # Handle all bullet points uniformly
            if line.startswith('-'):
                is_tech = line.startswith('- **')
                _handle_bullet_point(pdf, line, font_name, base_font_size, line_height, is_tech)
                continue
            # Default text formatting
            _handle_text(pdf, line, font_name, base_font_size, line_height)

        if contact_lines:
            _process_contact_section(pdf, contact_lines, font_name, base_font_size, line_height)

        pdf.output(filename)
        return filename

    except Exception as e:
        logging.error(f"PDF creation failed: {str(e)}")
        return None

def _handle_text(pdf, text, font_name, base_font_size, line_height):
    """Improved markdown handling with proper bold formatting"""
    # Split text into segments while preserving order
    segments = re.split(r'(\*\*)', text)
    is_bold = False
    x = pdf.get_x()
    y = pdf.get_y()

    for segment in segments:
        if not segment:
            continue

        if segment == '**':
            is_bold = not is_bold
            continue

        # Set appropriate font
        if is_bold:
            pdf.set_font(font_name, 'B', base_font_size)
        else:
            pdf.set_font(font_name, '', base_font_size)

        # Handle word wrapping
        words = segment.split()
        for word in words:
            word_width = pdf.get_string_width(word + ' ')

            # Check page space
            if x + word_width > pdf.w - pdf.r_margin:
                x = pdf.l_margin
                y += line_height
                if y > pdf.h - 15:
                    pdf.add_page()
                    y = pdf.t_margin

            pdf.set_xy(x, y)
            pdf.cell(word_width, line_height, word + ' ', ln=0)
            x += word_width

    # Move to next line after processing all segments
    pdf.ln(line_height)
    pdf.set_x(pdf.l_margin)


def _handle_bullet_point(pdf, line, font_name, base_font_size, line_height, is_tech_skills=False):
    """Consistent bullet alignment with proper multi-line wrapping and markdown support"""
    bullet_text = line[2:].strip()
    initial_x = pdf.get_x()

    if is_tech_skills and ':' in bullet_text:
        # Technology skills with category bullet
        category, items = re.split(r':\s*', bullet_text, 1)
        category = category.replace('**', '').strip()
        items = items.replace('**', '').strip()
        # Print bullet point, category in bold, and items in regular font
        pdf.set_font(font_name, '', base_font_size)
        pdf.cell(8, line_height, '•', ln=0)
        pdf.set_font(font_name, 'B', base_font_size)
        category_width = pdf.get_string_width(f"{category}: ")
        pdf.cell(category_width, line_height, f"{category}: ", ln=0)
        pdf.set_font(font_name, '', base_font_size)
        pdf.multi_cell(0, line_height, items, ln=1)
    else:
        # Regular bullet points with markdown support
        pdf.set_font(font_name, '', base_font_size)
        pdf.set_x(initial_x + 8)  # Indent for bullet
        pdf.cell(8, line_height, '•', ln=0)  # Print bullet

        # Save position after bullet
        start_x = pdf.get_x()
        start_y = pdf.get_y()

        # Process text with markdown handling
        segments = re.split(r'(\*\*)', bullet_text)
        is_bold = False
        pdf.set_xy(start_x, start_y)

        for segment in segments:
            if not segment:
                continue
            if segment == '**':
                is_bold = not is_bold
                continue

            # Set appropriate font style
            pdf.set_font(font_name, 'B' if is_bold else '', base_font_size)

            # Write segment content
            pdf.write(line_height, segment)

        # Move to next line after bullet content
        pdf.ln(line_height)
        pdf.set_x(initial_x + 8)  # Maintain bullet indentation

    pdf.ln(2)

def _handle_employment_entry(pdf, line, font_name, base_font_size, line_height):
    """Improved company/role layout with page break check"""
    entry = line.replace('**', '').strip()
    company, role = entry.split('|', 1)
    company = company.strip()
    role = role.strip()
    # Check available space
    if pdf.get_y() > pdf.h - 20:
        pdf.add_page()
    # Save original position
    start_x = pdf.get_x()
    start_y = pdf.get_y()
    # Print company name
    pdf.set_font(font_name, 'B', base_font_size)
    company_width = pdf.get_string_width(company) + 2
    pdf.cell(company_width, line_height, company, ln=0)
    # Calculate role position
    role_x = start_x + company_width + 2
    if role_x > pdf.w - 15:  # Prevent overflow
        role_x = start_x
        start_y += line_height
    # Print role with proper wrapping
    pdf.set_font(font_name, '', base_font_size - 1)
    pdf.set_xy(role_x, start_y)
    pdf.multi_cell(0, line_height, role)
    # Maintain vertical alignment
    new_y = max(start_y + line_height, pdf.get_y())
    pdf.set_xy(start_x, new_y)
    pdf.ln(2)

def _process_contact_section(pdf, contact_lines, font_name, font_size, line_height):
    """Properly centered contact information with vertical alignment"""
    # Calculate maximum width of any contact line
    pdf.set_font(font_name, 'B', font_size)
    max_width = max(pdf.get_string_width(line.replace('**', '')) for line in contact_lines)
    # Center all lines horizontally
    start_x = (pdf.w - max_width) / 2
    start_y = pdf.get_y()
    for line in contact_lines:
        pdf.set_xy(start_x, start_y)
        if ':' in line:
            label, value = line.split(':', 1)
            # Calculate combined width
            pdf.set_font(font_name, 'B', font_size)
            label_width = pdf.get_string_width(label + ': ')
            pdf.set_font(font_name, '', font_size)
            value_width = pdf.get_string_width(value.strip())
            total_width = label_width + value_width
            # Center this specific line
            line_x = (pdf.w - total_width) / 2
            pdf.set_x(line_x)
            pdf.set_font(font_name, 'B', font_size)
            pdf.cell(label_width, line_height, label + ': ', ln=0)
            pdf.set_font(font_name, '', font_size)
            pdf.cell(value_width, line_height, value.strip(), ln=1)
        else:
            pdf.set_x(start_x)
            pdf.cell(max_width, line_height, line, ln=1, align='C')
        start_y += line_height  # Maintain vertical spacing
    pdf.ln(4)

def _handle_title(pdf, title_text, font_name):
    """Format the main title section"""
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 8, title_text, 0, 1, 'C')
    pdf.ln(4)

def _handle_subheader(pdf, line, font_name, base_font_size):
    """Format subheaders in Key Achievements section"""
    subheader = line.replace('**', '').strip()
    pdf.set_font(font_name, 'B', base_font_size)
    pdf.multi_cell(0, base_font_size * 0.6, subheader)
    pdf.ln(2)

def _handle_section_header(pdf, title, font_name):
    """Format section headers with consistent spacing"""
    pdf.ln(4)  # Space before header
    pdf.set_font(font_name, 'B', 12)
    pdf.cell(0, 8, title.upper(), 0, 1, 'C')
    pdf.ln(4)  # Space after header



