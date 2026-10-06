"""
Test suite for PDF Text Extractor
Run with: pytest tests/
"""

import pytest
from pathlib import Path
import tempfile
import fitz
from fastapi.testclient import TestClient
from main import app, FileValidator, PDFExtractorAPI

client = TestClient(app)


class TestHealthCheck:
    """Health check endpoint tests"""
    
    def test_health_check_success(self):
        """Test health check endpoint returns 200"""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestFileValidator:
    """File validation tests"""
    
    def test_valid_pdf_validation(self):
        """Test validation of valid PDF file"""
        # Create a simple valid PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((20, 20), "Test content")
            doc.save(tmp.name)
            doc.close()
            
            # Create file-like object
            class FakeFile:
                def __init__(self, name):
                    self.name = name
                    self.type = 'application/pdf'
                    self.size = Path(name).stat().st_size
            
            fake_file = FakeFile(tmp.name)
            result = FileValidator.validate(fake_file)
            assert result["valid"] is True
            
            # Cleanup
            Path(tmp.name).unlink()
    
    def test_invalid_file_extension(self):
        """Test validation rejects non-PDF files"""
        class FakeFile:
            name = "document.txt"
            type = "text/plain"
            size = 1000
        
        result = FileValidator.validate(FakeFile())
        assert result["valid"] is False
        assert "Only PDF files" in result["error"]
    
    def test_file_too_large(self):
        """Test validation rejects oversized files"""
        class FakeFile:
            name = "large.pdf"
            type = "application/pdf"
            size = 1024 * 1024 * 100  # 100MB
        
        result = FileValidator.validate(FakeFile())
        assert result["valid"] is False
        assert "exceeds the maximum limit" in result["error"]
    
    def test_empty_file(self):
        """Test validation rejects empty files"""
        class FakeFile:
            name = "empty.pdf"
            type = "application/pdf"
            size = 0
        
        result = FileValidator.validate(FakeFile())
        assert result["valid"] is False
        assert "empty" in result["error"]


class TestAPIEndpoints:
    """API endpoint tests"""
    
    def test_extract_api_without_file(self):
        """Test extract endpoint without file"""
        response = client.post("/api/extract")
        assert response.status_code == 422  # Unprocessable Entity


@pytest.fixture
def sample_pdf():
    """Create a sample PDF for testing"""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        doc = fitz.open()
        
        # Page 1
        page1 = doc.new_page()
        page1.insert_text((20, 20), "Sample PDF Content\n\nThis is page 1.\nWith multiple lines.")
        
        # Page 2
        page2 = doc.new_page()
        page2.insert_text((20, 20), "This is page 2.\nMore test content here.")
        
        doc.save(tmp.name)
        doc.close()
        
        yield tmp.name
        
        # Cleanup
        Path(tmp.name).unlink()


class TestExtraction:
    """Text extraction tests"""
    
    def test_extract_from_valid_pdf(self, sample_pdf):
        """Test extraction from valid PDF"""
        with open(sample_pdf, 'rb') as f:
            response = client.post(
                "/api/extract",
                files={"file": (Path(sample_pdf).name, f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert data["status"] == "success"
        assert data["page_count"] == 2
    
    def test_extract_missing_character_count(self, sample_pdf):
        """Test that response includes character count"""
        with open(sample_pdf, 'rb') as f:
            response = client.post(
                "/api/extract",
                files={"file": (Path(sample_pdf).name, f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "character_count" in data
        assert isinstance(data["character_count"], int)
    
    def test_extract_includes_processing_time(self, sample_pdf):
        """Test that response includes processing time"""
        with open(sample_pdf, 'rb') as f:
            response = client.post(
                "/api/extract",
                files={"file": (Path(sample_pdf).name, f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "processing_time" in data
        assert isinstance(data["processing_time"], (int, float))


class TestEnglishFiltering:
    """English text filtering tests"""
    
    def test_filter_removes_non_ascii(self):
        """Test that non-ASCII characters are removed"""
        from main import filter_english
        
        text_with_non_ascii = "Hello world! 你好 مرحبا"
        filtered = filter_english(text_with_non_ascii)
        assert "Hello world!" in filtered
        assert "你好" not in filtered
        assert "مرحبا" not in filtered
    
    def test_filter_preserves_ascii(self):
        """Test that ASCII characters are preserved"""
        from main import filter_english
        
        text = "Hello World 123!@#$%"
        filtered = filter_english(text)
        assert filtered == text


class TestErrorHandling:
    """Error handling tests"""
    
    def test_extract_invalid_file_type(self):
        """Test extraction with invalid file type"""
        response = client.post(
            "/api/extract",
            files={"file": ("test.txt", b"not a pdf", "text/plain")}
        )
        assert response.status_code == 400
    
    def test_extract_corrupted_pdf(self):
        """Test extraction with corrupted PDF"""
        response = client.post(
            "/api/extract",
            files={"file": ("corrupt.pdf", b"not really a pdf", "application/pdf")}
        )
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
