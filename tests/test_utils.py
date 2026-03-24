"""
Unit tests for utils/utils.py - File type detection and text extraction.

These tests verify the magic byte detection fix that prevents the
"EOF marker not found" error when DOCX files are stored with .pdf extension.
"""
import io
import pytest


class TestDetectFileType:
    """Tests for detect_file_type function."""

    def test_detect_pdf_by_magic_bytes(self):
        """PDF files should be detected by %PDF header."""
        from utils.utils import detect_file_type
        
        pdf_header = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3'
        assert detect_file_type(pdf_header) == 'application/pdf'

    def test_detect_docx_by_magic_bytes(self):
        """DOCX files should be detected by PK ZIP header + word/ content."""
        from utils.utils import detect_file_type
        
        # Minimal DOCX-like header (ZIP with word/ marker)
        docx_header = b'PK\x03\x04' + b'\x00' * 100 + b'word/' + b'\x00' * 100
        assert detect_file_type(docx_header) == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

    def test_detect_docx_by_content_types(self):
        """DOCX files should also be detected by [Content_Types].xml marker."""
        from utils.utils import detect_file_type
        
        docx_header = b'PK\x03\x04' + b'\x00' * 10 + b'[Content_Types].xml' + b'\x00' * 100
        assert detect_file_type(docx_header) == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

    def test_detect_plain_zip_without_docx_markers(self):
        """Plain ZIP files without DOCX markers should be detected as ZIP."""
        from utils.utils import detect_file_type
        
        zip_header = b'PK\x03\x04' + b'\x00' * 500  # No word/ or [Content_Types]
        assert detect_file_type(zip_header) == 'application/zip'

    def test_detect_text_file(self):
        """UTF-8 text should be detected as plain text."""
        from utils.utils import detect_file_type
        
        text_content = b'Hello, this is a plain text file.\nWith multiple lines.'
        assert detect_file_type(text_content) == 'text/plain'

    def test_detect_old_doc_format(self):
        """Old .doc files should be detected by OLE header."""
        from utils.utils import detect_file_type
        
        ole_header = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\x00' * 100
        assert detect_file_type(ole_header) == 'application/msword'

    def test_empty_or_short_bytes_returns_octet_stream(self):
        """Very short input should return generic octet-stream."""
        from utils.utils import detect_file_type
        
        assert detect_file_type(b'') == 'application/octet-stream'
        assert detect_file_type(b'AB') == 'application/octet-stream'


class MockFile:
    """Mock file object for testing extract_text_from_file."""
    
    def __init__(self, content: bytes, filename: str, mime_type: str):
        self._content = content
        self.name = filename
        self.type = mime_type
    
    def getvalue(self) -> bytes:
        return self._content


class TestExtractTextFromFile:
    """Tests for extract_text_from_file function."""

    def test_extract_handles_type_mismatch(self):
        """Should use detected type, not declared MIME type."""
        from utils.utils import extract_text_from_file
        
        # Create a minimal DOCX-like content but declare it as PDF
        # This simulates the bug where DOCX files were stored with .pdf extension
        docx_content = b'PK\x03\x04' + b'\x00' * 100 + b'word/' + b'\x00' * 100
        
        mock_file = MockFile(
            content=docx_content,
            filename='test.pdf',  # Wrong extension
            mime_type='application/pdf'  # Wrong MIME type
        )
        
        # Should not raise "EOF marker not found" - should detect as DOCX
        # Note: Will still fail to extract text since it's not a real DOCX,
        # but the error should be different from PDF parse error
        result = extract_text_from_file(mock_file)
        # Empty result is fine - the point is it shouldn't crash with PDF error
        assert isinstance(result, str)

    def test_extract_text_from_plain_text(self):
        """Should extract text from plain text files."""
        from utils.utils import extract_text_from_file
        
        text_content = b'This is a test CV.\nName: John Doe\nSkills: Python, Testing'
        
        mock_file = MockFile(
            content=text_content,
            filename='cv.txt',
            mime_type='text/plain'
        )
        
        result = extract_text_from_file(mock_file)
        assert 'John Doe' in result
        assert 'Python' in result


class TestConfigSingleton:
    """Tests for Config singleton pattern."""

    def test_config_is_singleton_not_callable(self):
        """Config should be used directly, not called as Config()."""
        from config.settings import Config
        
        # Config is already an instance (singleton pattern)
        # Accessing attributes should work
        assert hasattr(Config, 'AIRTABLE_API_KEY') or hasattr(Config, 'airtable_api_key')
        
        # Calling Config() should raise TypeError since it's an instance
        with pytest.raises(TypeError):
            Config()

    def test_config_has_required_attributes(self):
        """Config should have all required attributes for CV routes."""
        from config.settings import Config
        
        # These attributes are used in api/routes/cv.py
        required_attrs = [
            'AIRTABLE_API_KEY',
            'AIRTABLE_BASE_ID', 
            'AIRTABLE_TABLE_ID_HISTORY',
        ]
        
        for attr in required_attrs:
            assert hasattr(Config, attr), f"Config missing required attribute: {attr}"
