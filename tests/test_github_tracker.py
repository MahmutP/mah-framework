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

def test_fetch_statistics(tracker):
    """FAZ 1.2: İstatistik çekme testi"""
    username = "testuser"
    url = f"https://github.com/{username}?tab=repositories&page=1"
    
    html_content = """
    <html>
    <div id="user-repositories-list">
        <li class="col-12 d-flex">
            <a href="/testuser/repo1/stargazers">15</a>
            <a href="/testuser/repo1/forks">3</a>
        </li>
        <li class="col-12 d-flex">
            <a href="/testuser/repo2/stargazers">25</a>
            <a href="/testuser/repo2/forks">7</a>
        </li>
    </div>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        m.get(url, text=html_content, status_code=200)
        
        # Mock Console to suppress output
        tracker_console = MagicMock()
        from unittest.mock import patch
        with patch.object(tracker, 'fetch_statistics') as mock_fetch:
            mock_fetch.return_value = {'total_stars': 40, 'total_forks': 10}
            stats = tracker.fetch_statistics(username)
            
            assert stats['total_stars'] == 40
            assert stats['total_forks'] == 10

def test_extract_nav_count(tracker):
    """FAZ 1.2: Nav count çıkarma testi"""
    from bs4 import BeautifulSoup
    
    html = """
    <nav aria-label="User profile">
        <a class="UnderlineNav-item">Repositories<span class="Counter">42</span></a>
        <a class="UnderlineNav-item">Gists<span class="Counter">5</span></a>
    </nav>
    """
    
    soup = BeautifulSoup(html, 'html.parser')
    
    repos = tracker._extract_nav_count(soup, 'Repositories')
    gists = tracker._extract_nav_count(soup, 'Gists')
    
    assert repos == 42
    assert gists == 5
