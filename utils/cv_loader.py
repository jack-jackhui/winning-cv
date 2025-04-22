# utils/cv_loader.py
from utils.utils import extract_text_from_file
from utils.logger import setup_logger
import os
import io
import logging

logger = setup_logger(__name__)

def load_cv_content(file_path="user_cv/CV_Jack_HUI_08042025_EL.docx"):
    """Load CV content using unified text extraction"""
    try:
        logger.info(f"Loading CV from: {os.path.abspath(file_path)}")

        if not os.path.exists(file_path):
            logger.error(f"File not found: {os.path.abspath(file_path)}")
            return ""

        # Create file-like object for utils processing
        with open(file_path, 'rb') as f:
            file_bytes = f.read()

        # Create mock FileStorage-like object
        class FileWrapper:
            def __init__(self, content, content_type):
                self.file = io.BytesIO(content)
                self.type = content_type

            def getvalue(self):
                return self.file.getvalue()

        # Detect MIME type from extension
        if file_path.lower().endswith('.docx'):
            file_obj = FileWrapper(file_bytes,
                                   'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        elif file_path.lower().endswith('.pdf'):
            file_obj = FileWrapper(file_bytes, 'application/pdf')

        elif file_path.lower().endswith('.txt') or file_path.lower().endswith('.md'):
            file_obj = FileWrapper(file_bytes, 'text/plain')

        else:
            logger.error("Unsupported file format")
            return ""

        return extract_text_from_file(file_obj)

    except Exception as e:
        logger.error(f"CV load failed: {str(e)}")
        return ""
