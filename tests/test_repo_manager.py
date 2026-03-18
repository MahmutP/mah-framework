# tests/test_repo_manager.py
# Uzak modül deposu yönetim sistemi (RepoManager) için birim testleri.

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.repo_manager import RepoManager
from commands.repo import Repo
from core.shared_state import shared_state


# ==============================================================================
# RepoManager Testleri
# ==============================================================================

class TestRepoManagerInit:
    """RepoManager başlatma testleri."""

    def test_repos_file_created(self, tmp_path):
        """Repos.json dosyasının oluşturulduğunu doğrular."""
        repos_file = tmp_path / "repos.json"
        repos_dir = tmp_path / "repos"

        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager = RepoManager()

        assert repos_file.exists()
        assert repos_dir.exists()

    def test_repos_dir_created(self, tmp_path):
        """Repos dizininin oluşturulduğunu doğrular."""
        repos_file = tmp_path / "repos.json"
        repos_dir = tmp_path / "repos"

        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager = RepoManager()

        assert repos_dir.is_dir()

    def test_empty_repos_on_init(self, tmp_path):
        """Başlangıçta depo listesinin boş olduğunu doğrular."""
        repos_file = tmp_path / "repos.json"
        repos_dir = tmp_path / "repos"

        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager = RepoManager()

        assert manager.repos == {}


class TestRepoManagerAddRemove:
    """Depo ekleme ve silme testleri."""

    @pytest.fixture
    def repo_manager(self, tmp_path):
        """Her test için geçici dosyalarla bir RepoManager oluşturur."""
        repos_file = tmp_path / "repos.json"
        repos_dir = tmp_path / "repos"

        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager = RepoManager()
        
        # Kalıcı patch: save/load sırasında Path'lerin doğru olması için
        manager.repos_file = repos_file
        manager.repos_dir = repos_dir
        return manager

    def test_add_repo_success(self, repo_manager):
        """Geçerli URL ile depo ekleme başarılı olmalı."""
        result = repo_manager.add_repo("testrepo", "https://github.com/user/repo.git")
        assert result is True
        assert "testrepo" in repo_manager.repos
        assert repo_manager.repos["testrepo"]["url"] == "https://github.com/user/repo.git"
        assert repo_manager.repos["testrepo"]["status"] == "added"

    def test_add_repo_duplicate_name(self, repo_manager):
        """Aynı isimde depo ekleme başarısız olmalı."""
        repo_manager.add_repo("duperepo", "https://github.com/user/repo1.git")
        result = repo_manager.add_repo("duperepo", "https://github.com/user/repo2.git")
        assert result is False

    def test_add_repo_invalid_url(self, repo_manager):
        """Geçersiz URL ile depo ekleme başarısız olmalı."""
        result = repo_manager.add_repo("badrepo", "ftp://invalid.url/repo")
        assert result is False
        assert "badrepo" not in repo_manager.repos

    def test_add_repo_empty_name(self, repo_manager):
        """Boş isim ile depo ekleme başarısız olmalı."""
        result = repo_manager.add_repo("", "https://github.com/user/repo.git")
        assert result is False

    def test_add_repo_gitlab_url(self, repo_manager):
        """GitLab URL'si ile depo ekleme başarılı olmalı."""
        result = repo_manager.add_repo("gitlab", "https://gitlab.com/user/repo.git")
        assert result is True

    def test_add_repo_ssh_url(self, repo_manager):
        """SSH URL'si ile depo ekleme başarılı olmalı."""
        result = repo_manager.add_repo("sshrepo", "git@github.com:user/repo.git")
        assert result is True

    def test_remove_repo_success(self, repo_manager):
        """Kayıtlı depoyu silme başarılı olmalı."""
        repo_manager.add_repo("todelete", "https://github.com/user/repo.git")
        result = repo_manager.remove_repo("todelete")
        assert result is True
        assert "todelete" not in repo_manager.repos

    def test_remove_repo_not_found(self, repo_manager):
        """Kayıtlı olmayan depoyu silme başarısız olmalı."""
        result = repo_manager.remove_repo("nonexistent")
        assert result is False

    def test_remove_repo_cleans_directory(self, repo_manager):
        """Depo silindiğinde klonlanmış dizinin de silindiğini doğrular."""
        repo_manager.add_repo("dirrepo", "https://github.com/user/repo.git")
        
        # Klonlanmış dizini simüle et
        repo_path = repo_manager.repos_dir / "dirrepo"
        repo_path.mkdir(parents=True, exist_ok=True)
        (repo_path / "test.py").touch()

        result = repo_manager.remove_repo("dirrepo")
        assert result is True
        assert not repo_path.exists()


class TestRepoManagerListQuery:
    """Listeleme ve sorgulama testleri."""

    @pytest.fixture
    def repo_manager(self, tmp_path):
        repos_file = tmp_path / "repos.json"
        repos_dir = tmp_path / "repos"

        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager = RepoManager()

        manager.repos_file = repos_file
        manager.repos_dir = repos_dir
        return manager

    def test_list_repos_empty(self, repo_manager):
        """Boş liste döndürüldüğünü doğrular."""
        assert repo_manager.list_repos() == {}

    def test_list_repos_with_entries(self, repo_manager):
        """Eklenen depoların listelendiğini doğrular."""
        repo_manager.add_repo("repo1", "https://github.com/user/repo1.git")
        repo_manager.add_repo("repo2", "https://github.com/user/repo2.git")
        repos = repo_manager.list_repos()
        assert len(repos) == 2
        assert "repo1" in repos
        assert "repo2" in repos

    def test_get_repo_existing(self, repo_manager):
        """Var olan depo bilgisini döndürür."""
        repo_manager.add_repo("myrepo", "https://github.com/user/repo.git")
        info = repo_manager.get_repo("myrepo")
        assert info is not None
        assert info["url"] == "https://github.com/user/repo.git"

    def test_get_repo_nonexistent(self, repo_manager):
        """Olmayan depo için None döndürür."""
        info = repo_manager.get_repo("nosuchrepo")
        assert info is None

    def test_get_repo_names(self, repo_manager):
        """Depo isimlerini liste olarak döndürür."""
        repo_manager.add_repo("alpha", "https://github.com/a/alpha.git")
        repo_manager.add_repo("beta", "https://github.com/b/beta.git")
        names = repo_manager.get_repo_names()
        assert "alpha" in names
        assert "beta" in names
        assert len(names) == 2


class TestRepoManagerPersistence:
    """JSON dosyasına kaydetme ve yükleme testleri."""

    def test_save_and_reload(self, tmp_path):
        """Kaydedilen depoların yeniden yüklendiğini doğrular."""
        repos_file = tmp_path / "repos.json"
        repos_dir = tmp_path / "repos"

        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager1 = RepoManager()
            manager1.repos_file = repos_file
            manager1.repos_dir = repos_dir
            manager1.add_repo("persist", "https://github.com/user/persist.git")

        # Yeni bir manager oluştur ve dosyadan yükle
        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager2 = RepoManager()

        assert "persist" in manager2.repos
        assert manager2.repos["persist"]["url"] == "https://github.com/user/persist.git"

    def test_corrupt_json_handled(self, tmp_path):
        """Bozuk JSON dosyasının zararsızca ele alındığını doğrular."""
        repos_file = tmp_path / "repos.json"
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir(parents=True, exist_ok=True)

        # Bozuk JSON yaz
        repos_file.write_text("{invalid json")

        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager = RepoManager()

        assert manager.repos == {}


class TestRepoManagerUpdate:
    """Depo güncelleme (clone/pull) testleri. Git işlemleri mock'lanır."""

    @pytest.fixture
    def repo_manager(self, tmp_path):
        repos_file = tmp_path / "repos.json"
        repos_dir = tmp_path / "repos"

        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager = RepoManager()

        manager.repos_file = repos_file
        manager.repos_dir = repos_dir
        return manager

    @patch("core.repo_manager.subprocess.run")
    def test_clone_repo(self, mock_run, repo_manager):
        """Git clone işleminin çağrıldığını doğrular."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        repo_manager.add_repo("cloneme", "https://github.com/user/repo.git")
        result = repo_manager.update_repo("cloneme")

        assert result is True
        assert mock_run.called
        assert repo_manager.repos["cloneme"]["status"] == "cloned"

    @patch("core.repo_manager.subprocess.run")
    def test_pull_repo(self, mock_run, repo_manager):
        """Git pull işleminin çağrıldığını doğrular (dizin mevcutsa)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.", stderr="")

        repo_manager.add_repo("pullme", "https://github.com/user/repo.git")

        # Klonlanmış dizin simülasyonu
        repo_path = repo_manager.repos_dir / "pullme"
        repo_path.mkdir(parents=True, exist_ok=True)
        (repo_path / ".git").mkdir()

        result = repo_manager.update_repo("pullme")
        assert result is True
        assert repo_manager.repos["pullme"]["status"] == "updated"

    def test_update_nonexistent_repo(self, repo_manager):
        """Kayıtlı olmayan depoyu güncelleme başarısız olmalı."""
        result = repo_manager.update_repo("nosuchrepo")
        assert result is False

    def test_update_all_empty(self, repo_manager):
        """Kayıtlı depo yokken tüm güncelleme başarısız olmalı."""
        result = repo_manager.update_repo()
        assert result is False

    @patch("core.repo_manager.subprocess.run")
    def test_clone_failure(self, mock_run, repo_manager):
        """Clone hatası durumunda status 'error' olmalı."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="fatal: repo not found")

        repo_manager.add_repo("failrepo", "https://github.com/user/nonexistent.git")
        result = repo_manager.update_repo("failrepo")

        assert result is False
        assert repo_manager.repos["failrepo"]["status"] == "error"


class TestRepoManagerURLValidation:
    """URL doğrulama testleri."""

    @pytest.fixture
    def repo_manager(self, tmp_path):
        repos_file = tmp_path / "repos.json"
        repos_dir = tmp_path / "repos"

        with patch("core.repo_manager.REPOS_FILE", str(repos_file)), \
             patch("core.repo_manager.REPOS_DIR", str(repos_dir)):
            manager = RepoManager()

        manager.repos_file = repos_file
        manager.repos_dir = repos_dir
        return manager

    def test_valid_github_https(self, repo_manager):
        assert repo_manager._validate_url("https://github.com/user/repo.git") is True

    def test_valid_gitlab_https(self, repo_manager):
        assert repo_manager._validate_url("https://gitlab.com/user/repo.git") is True

    def test_valid_bitbucket_https(self, repo_manager):
        assert repo_manager._validate_url("https://bitbucket.org/user/repo.git") is True

    def test_valid_github_ssh(self, repo_manager):
        assert repo_manager._validate_url("git@github.com:user/repo.git") is True

    def test_valid_generic_https(self, repo_manager):
        assert repo_manager._validate_url("https://custom-git.example.com/repo.git") is True

    def test_invalid_ftp(self, repo_manager):
        assert repo_manager._validate_url("ftp://bad.url/repo") is False

    def test_invalid_random_string(self, repo_manager):
        assert repo_manager._validate_url("not a url at all") is False


# ==============================================================================
# Repo Komutu Testleri
# ==============================================================================

class TestRepoCommand:
    """Repo komut sınıfı metadata testleri."""

    def test_command_metadata(self):
        """Komut metadata değerlerinin doğruluğunu kontrol eder."""
        cmd = Repo()
        assert cmd.Name == "repo"
        assert cmd.Category == "system"
        assert "add" in cmd.Usage
        assert len(cmd.Examples) > 0

    def test_completions_subcommands(self):
        """Alt komut tamamlamalarını doğrular."""
        cmd = Repo()
        completions = cmd.get_completions("repo ", "")
        assert "add" in completions
        assert "update" in completions
        assert "list" in completions
        assert "remove" in completions

    def test_completions_partial_subcommand(self):
        """Kısmi alt komut tamamlamalarını doğrular."""
        cmd = Repo()
        completions = cmd.get_completions("repo up", "up")
        assert "update" in completions
        assert "add" not in completions

    def test_execute_without_repo_manager(self):
        """RepoManager yüklenmemişse False döner."""
        cmd = Repo()
        shared_state.repo_manager = None
        result = cmd.execute("list")
        assert result is False
