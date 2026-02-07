import pytest
import requests_mock
from modules.auxiliary.recon.github_tracker import GitHubTracker
from unittest.mock import MagicMock

@pytest.fixture
def tracker():
    return GitHubTracker()

def test_fetch_profile_info(tracker):
    username = "testuser"
    url = f"https://github.com/{username}"
    
    html_content = """
    <div class="h-card">
        <div class="p-note user-profile-bio"><div>This is a bio</div></div>
        <ul class="vcard-details">
            <li itemprop="homeLocation" class="vcard-detail pt-1 css-truncate css-truncate-target"><span class="p-label">Istanbul, Turkey</span></li>
            <li itemprop="worksFor" class="vcard-detail pt-1 css-truncate css-truncate-target"><span class="p-org"><div>OpenAI</div></span></li>
            <li itemprop="url" class="vcard-detail pt-1 css-truncate css-truncate-target"><a rel="nofollow me" class="Link--primary" href="https://example.com">https://example.com</a></li>
            <li itemprop="social" class="vcard-detail pt-1 css-truncate css-truncate-target"><a class="Link--primary" href="https://twitter.com/testuser">@testuser</a></li>
        </ul>
        <li itemprop="email" class="vcard-detail pt-1 css-truncate css-truncate-target"><a class="Link--primary" href="mailto:test@example.com">test@example.com</a></li>
    </div>
    """
    
    with requests_mock.Mocker() as m:
        m.get(url, text=html_content, status_code=200)
        
        info = tracker.fetch_profile_info(username)
        
        assert info['bio'] == "This is a bio"
        assert info['location'] == "Istanbul, Turkey"
        assert info['company'] == "OpenAI"
        assert info['website'] == "https://example.com"
        assert info['twitter'] == "@testuser"
        assert info['email'] == "test@example.com"

def test_fetch_profile_info_empty(tracker):
    username = "emptyuser"
    url = f"https://github.com/{username}"
    
    html_content = "<html></html>"
    
    with requests_mock.Mocker() as m:
        m.get(url, text=html_content, status_code=200)
        
        info = tracker.fetch_profile_info(username)
        
        assert info['bio'] is None
        assert info['location'] is None
        assert info['company'] is None

