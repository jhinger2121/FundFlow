import os
import pytest
import requests
from unittest.mock import patch, MagicMock
from csv_downloader.yieldmax_scraper import YieldMaxScraper, get_weekly_folder
from django.conf import settings

@pytest.fixture
def scraper():
    """Fixture to provide an instance of YieldMaxScraper."""
    return YieldMaxScraper()

@patch("requests.get")
def test_download_success(mock_get, scraper):
    """Test successful file download."""
    
    # Mock a successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"Sample CSV Data"
    mock_get.return_value = mock_response

    scraper.download()

    # Ensure the file was created
    assert os.path.exists(scraper.file_path), "File was not created."

    # Read the file content
    with open(scraper.file_path, "rb") as f:
        assert f.read() == b"Sample CSV Data", "File content does not match."

    # Cleanup
    os.remove(scraper.file_path)

@patch("requests.get")
def test_download_failure(mock_get, scraper, caplog):
    """Test handling of failed downloads (non-200 status codes)."""
    
    # Mock a failure response
    mock_response = MagicMock()
    mock_response.status_code = 500  # Simulating a server error
    mock_get.return_value = mock_response

    scraper.download()

    # Check logs for failure message
    assert "Failed to download YieldMax file" in caplog.text

@patch("os.makedirs")
def test_directory_creation(mock_makedirs, scraper):
    """Test that the scraper ensures the directory exists."""
    
    scraper.__init__()  # Re-initialize to trigger directory creation

    # Check if os.makedirs was called
    mock_makedirs.assert_called_with(scraper.base_path, exist_ok=True)

def test_weekly_folder_format():
    """Test if get_weekly_folder returns correct format."""
    
    folder_name = get_weekly_folder()
    assert folder_name.startswith(f"{datetime.today().year}-W"), "Incorrect folder name format."
