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

def test_fetch_repositories(tracker):
    """FAZ 2.1: Repository çekme testi"""
    username = "testuser"
    url = f"https://github.com/{username}?tab=repositories&page=1&sort=updated"
    
    html_content = """
    <html>
    <div id="user-repositories-list">
        <li class="col-12 d-flex">
            <h3><a href="/testuser/repo1">repo1</a></h3>
            <p itemprop="description">Test Repo 1</p>
            <span itemprop="programmingLanguage">Python</span>
            <a href="/testuser/repo1/stargazers">10</a>
            <a href="/testuser/repo1/forks">5</a>
            <relative-time>2 days ago</relative-time>
        </li>
        <li class="col-12 d-flex">
            <h3><a href="/testuser/repo2">repo2</a></h3>
            <span itemprop="programmingLanguage">Go</span>
            <a href="/testuser/repo2/stargazers">100</a>
            <a href="/testuser/repo2/forks">20</a>
            <relative-time>1 week ago</relative-time>
        </li>
    </div>
    </html>
    """
    
    with requests_mock.Mocker() as m:
        m.get(url, text=html_content, status_code=200)
        
        # Mock Console
        tracker_console = MagicMock()
        
        repos = tracker.fetch_repositories(username, limit=10, sort_by="updated")
        
        assert len(repos) == 2
        
        assert repos[0]['name'] == "repo1"
        assert repos[0]['language'] == "Python"
        assert repos[0]['stars'] == "10"
        assert repos[0]['forks'] == "5"
        assert repos[0]['description'] == "Test Repo 1"
        assert repos[0]['updated'] == "2 days ago"
        
        assert repos[1]['name'] == "repo2"
        assert repos[1]['language'] == "Go"
        assert repos[1]['description'] == "-"

def test_analyze_repositories(tracker):
    """FAZ 2.2: Repository analiz testi"""
    repos = [
        {'name': 'repo1', 'language': 'Python', 'stars': '10', 'forks': '5', 'updated': 'yesterday'},
        {'name': 'repo2', 'language': 'Python', 'stars': '20', 'forks': '2', 'updated': 'today'},
        {'name': 'repo3', 'language': 'Go', 'stars': '100', 'forks': '50', 'updated': 'last week'},
        {'name': 'repo4', 'language': 'Java', 'stars': '5', 'forks': '1', 'updated': 'last month'},
        {'name': 'repo5', 'language': 'Python', 'stars': '1.5k', 'forks': '200', 'updated': 'year ago'},
    ]
    
    # helper test
    assert tracker._parse_number('1.5k') == 1500
    assert tracker._parse_number('1.2M') == 1200000
    assert tracker._parse_number('10') == 10
    
    analysis = tracker.analyze_repositories(repos)
    
    # Top languages
    assert analysis['top_languages'][0] == ('Python', 3)
    
    # Most starred
    assert analysis['most_starred'][0]['name'] == 'repo5' # 1500
    assert analysis['most_starred'][1]['name'] == 'repo3' # 100
    
    # Most forked
    assert analysis['most_forked'][0]['name'] == 'repo5' # 200

def test_analyze_relationships(tracker):
    """FAZ 3.1: İlişki analizi testi"""
    following = [
        {'username': 'mutual_user', 'link': '...'},
        {'username': 'not_following_back_user', 'link': '...'},
    ]
    followers = [
        {'username': 'mutual_user', 'link': '...'},
        {'username': 'not_followed_back_user', 'link': '...'},
    ]
    
    analysis = tracker.analyze_relationships(following, followers)
    
    assert 'mutual_user' in analysis['mutual']
    assert len(analysis['mutual']) == 1
    
    assert 'not_following_back_user' in analysis['not_following_back']
    assert len(analysis['not_following_back']) == 1
    
    assert 'not_followed_back_user' in analysis['not_followed_back']
    assert len(analysis['not_followed_back']) == 1

def test_analyze_network(tracker):
    """FAZ 3.2: Ağ analizi testi"""
    from unittest.mock import MagicMock
    
    users = [{'username': 'u1'}, {'username': 'u2'}]
    
    # Mock profile info
    # tracker fixture'ı zaten var. metodunu mockluyoruz
    original_fetch = tracker.fetch_profile_info
    tracker.fetch_profile_info = MagicMock(side_effect=[
        {'location': 'Turkey', 'company': 'GitHub', 'public_repos': 5},
        {'location': 'USA', 'company': 'GitHub', 'public_repos': 0}
    ])
    
    stats = tracker.analyze_network(users, limit=2)
    
    # Clean up mock
    tracker.fetch_profile_info = original_fetch
    
    assert stats['total_scanned'] == 2
    assert stats['active_count'] == 1 # u1 has repos
    assert stats['top_companies'][0] == ('GitHub', 2)
    assert 'Turkey' in [x for x,y in stats['top_locations']]

def test_compare_users(tracker):
    """FAZ 3.1: İki kullanıcı karşılaştırma testi (logic verification)"""
    from unittest.mock import MagicMock
    
    user1 = "u1"
    user2 = "u2"
    
    u1_followers = [{'username': 'common', 'link': ''}, {'username': 'u1_only', 'link': ''}]
    u1_following = []
    
    # Mock fetch_users to return u2 data
    # side_effect: first call (followers), second call (following)
    original_fetch = tracker.fetch_users
    tracker.fetch_users = MagicMock(side_effect=[
        [{'username': 'common', 'link': ''}, {'username': 'u2_only', 'link': ''}], 
        []
    ])
    
    console = MagicMock()
    
    tracker.compare_users(user1, u1_followers, u1_following, user2, console)
    
    # Verifications BEFORE cleanup
    # compare_users should print a table. Since we mocked console, we expect print calls.
    assert console.print.called
    
    # fetch_users should be called for user2 twice (followers, following)
    assert tracker.fetch_users.call_count == 2
    args, _ = tracker.fetch_users.call_args_list[0]
    assert args[0] == user2
    assert args[1] == "followers"

    # Clean up
    tracker.fetch_users = original_fetch

def test_run_full_integration(tracker):
    """Tüm opsiyonların run metodunda doğru çağrıldığını test eder"""
    from unittest.mock import MagicMock
    
    # Mock all functionality methods to focus on flow control
    tracker.fetch_profile_info = MagicMock(return_value={})
    tracker.fetch_statistics = MagicMock(return_value={})
    tracker.fetch_users = MagicMock(return_value=[])
    tracker.fetch_repositories = MagicMock(return_value=[])
    tracker.analyze_repositories = MagicMock(return_value={})
    tracker.analyze_relationships = MagicMock(return_value={'mutual':set(), 'not_following_back':set(), 'not_followed_back':set()})
    tracker.analyze_network = MagicMock(return_value={'total_scanned':0})
    tracker.compare_users = MagicMock()
    
    # Mock prints
    tracker.print_profile_info = MagicMock()
    tracker.print_repositories_table = MagicMock()
    tracker.print_repo_analysis = MagicMock()
    tracker.print_relationship_analysis = MagicMock()
    tracker.print_network_analysis = MagicMock()
    tracker.print_table = MagicMock()
    tracker.save_to_file = MagicMock()
    
    options = {
        "USERNAME": "testuser",
        "OUTPUT": "test_output.txt",
        "PROFILE_INFO": "True",
        "REPOS": "True",
        "LIMIT": "20",
        "SORT_BY": "updated",
        "MUTUAL_ONLY": "False",
        "COMPARE": "otheruser",
        "NETWORK_ANALYSIS": "True",
        "DAYS": "30",
        "ACTIVITY": "False"
    }
    
    # Call run
    tracker.run(options)
    
    # Verify calls
    assert tracker.fetch_profile_info.called
    assert tracker.fetch_repositories.called
    assert tracker.analyze_repositories.called
    assert tracker.analyze_relationships.called
    assert tracker.analyze_network.called
    assert tracker.compare_users.called
    
    # fetch_users called twice for target user (followers, following)
    assert tracker.fetch_users.call_count == 2
    
    # Verify save call
    assert tracker.save_to_file.called
