# tests/test_module_downloader.py
# Modül İndirici (ModuleDownloader) ve Download komutu için birim testleri.

import pytest
import json
import sys
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.module_downloader import ModuleDownloader
from commands.download import Download
from core.shared_state import shared_state


# ==============================================================================
# Yardımcı: Sahte modül dosyası oluşturma
# ==============================================================================

FAKE_MODULE_CONTENT = '''
from core.module import BaseModule
from core.option import Option

class FakeScanner(BaseModule):
    Name = "Fake Scanner"
    Description = "Test amaçlı sahte tarayıcı modülü"
    Author = "TestUser"
    Category = "auxiliary"
    Version = "1.2"
    Requirements = {"python": ["requests"]}

    def run(self, options):
        return True
'''

FAKE_MODULE_V2_CONTENT = '''
from core.module import BaseModule

class FakeScanner(BaseModule):
    Name = "Fake Scanner"
    Description = "Test amaçlı sahte tarayıcı modülü - güncellenmiş"
    Author = "TestUser"
    Category = "auxiliary"
    Version = "2.0"

    def run(self, options):
        return True
'''

NOT_A_MODULE_CONTENT = '''
# Bu dosya bir modül değil
def some_utility():
    return 42
'''


def compute_sha256(file_path: Path) -> str:
    """Test yardımcısı: Dosya SHA256 hash hesapla."""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


# ==============================================================================
# ModuleDownloader Init Testleri
# ==============================================================================

class TestModuleDownloaderInit:
    """ModuleDownloader başlatma testleri."""

    def test_installed_file_created(self, tmp_path):
        """installed_modules.json dosyasının oluşturulduğunu doğrular."""
        installed_file = tmp_path / "installed.json"
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        with patch("core.module_downloader.INSTALLED_MODULES_FILE", str(installed_file)), \
             patch("core.module_downloader.REPOS_DIR", str(repos_dir)):
            downloader = ModuleDownloader(modules_dir=str(modules_dir))

        assert installed_file.exists()

    def test_empty_installed_on_init(self, tmp_path):
        """Başlangıçta kurulu modül listesinin boş olduğunu doğrular."""
        installed_file = tmp_path / "installed.json"
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        with patch("core.module_downloader.INSTALLED_MODULES_FILE", str(installed_file)), \
             patch("core.module_downloader.REPOS_DIR", str(repos_dir)):
            downloader = ModuleDownloader(modules_dir=str(modules_dir))

        assert downloader.installed == {}

    def test_corrupt_json_handled(self, tmp_path):
        """Bozuk JSON dosyasının zararsızca ele alındığını doğrular."""
        installed_file = tmp_path / "installed.json"
        installed_file.write_text("{invalid json")
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        with patch("core.module_downloader.INSTALLED_MODULES_FILE", str(installed_file)), \
             patch("core.module_downloader.REPOS_DIR", str(repos_dir)):
            downloader = ModuleDownloader(modules_dir=str(modules_dir))

        assert downloader.installed == {}


# ==============================================================================
# Depo Tarama (Scan) Testleri
# ==============================================================================

class TestModuleDownloaderScan:
    """Depo tarama ve modül bulma testleri."""

    @pytest.fixture
    def downloader(self, tmp_path):
        """Her test için geçici dosyalarla bir ModuleDownloader oluşturur."""
        installed_file = tmp_path / "installed.json"
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        with patch("core.module_downloader.INSTALLED_MODULES_FILE", str(installed_file)), \
             patch("core.module_downloader.REPOS_DIR", str(repos_dir)):
            dl = ModuleDownloader(modules_dir=str(modules_dir))

        dl.installed_file = installed_file
        dl.repos_dir = repos_dir
        dl.modules_dir = modules_dir
        return dl

    def test_scan_empty_repos(self, downloader):
        """Boş depo dizininde tarama boş liste döner."""
        result = downloader.scan_repos()
        assert result == []

    def test_scan_finds_module(self, downloader):
        """Depodaki modülü bulur."""
        repo_dir = downloader.repos_dir / "testrepo"
        scanner_dir = repo_dir / "auxiliary" / "scanner"
        scanner_dir.mkdir(parents=True)
        (scanner_dir / "fake_scanner.py").write_text(FAKE_MODULE_CONTENT)

        result = downloader.scan_repos()
        assert len(result) == 1
        assert result[0]["name"] == "Fake Scanner"
        assert result[0]["repo"] == "testrepo"
        assert result[0]["version"] == "1.2"

    def test_scan_ignores_non_modules(self, downloader):
        """BaseModule alt sınıfı olmayan dosyaları atlar."""
        repo_dir = downloader.repos_dir / "testrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "utility.py").write_text(NOT_A_MODULE_CONTENT)

        result = downloader.scan_repos()
        assert result == []

    def test_scan_ignores_init_files(self, downloader):
        """__init__.py dosyalarını atlar."""
        repo_dir = downloader.repos_dir / "testrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "__init__.py").write_text(FAKE_MODULE_CONTENT)

        result = downloader.scan_repos()
        assert result == []

    def test_scan_with_search_filter(self, downloader):
        """Arama terimi ile filtreleme çalışır."""
        repo_dir = downloader.repos_dir / "testrepo" / "auxiliary"
        repo_dir.mkdir(parents=True)
        (repo_dir / "fake_scanner.py").write_text(FAKE_MODULE_CONTENT)
        (repo_dir / "other_module.py").write_text(
            FAKE_MODULE_CONTENT.replace("Fake Scanner", "Other Module")
            .replace("FakeScanner", "OtherModule")
        )

        # "Fake" araması sadece ilk modülü döndürmeli
        result = downloader.scan_repos("Fake")
        assert len(result) == 1
        assert result[0]["name"] == "Fake Scanner"

    def test_scan_detects_signature(self, downloader):
        """SHA256 imza dosyası tespit edilir."""
        repo_dir = downloader.repos_dir / "testrepo"
        repo_dir.mkdir(parents=True)
        module_file = repo_dir / "scanner.py"
        module_file.write_text(FAKE_MODULE_CONTENT)

        # İmza dosyası oluştur
        sha256_file = repo_dir / "scanner.sha256"
        sha256_file.write_text(compute_sha256(module_file))

        result = downloader.scan_repos()
        assert len(result) == 1
        assert result[0]["has_signature"] is True


# ==============================================================================
# Modül Kurma (Install) Testleri
# ==============================================================================

class TestModuleDownloaderInstall:
    """Modül kurma testleri."""

    @pytest.fixture
    def downloader(self, tmp_path):
        installed_file = tmp_path / "installed.json"
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        with patch("core.module_downloader.INSTALLED_MODULES_FILE", str(installed_file)), \
             patch("core.module_downloader.REPOS_DIR", str(repos_dir)):
            dl = ModuleDownloader(modules_dir=str(modules_dir))

        dl.installed_file = installed_file
        dl.repos_dir = repos_dir
        dl.modules_dir = modules_dir
        return dl

    @patch("core.module_downloader.subprocess.run")
    def test_install_success(self, mock_pip, downloader):
        """Modül kurulumu başarılı olmalı."""
        # pip mock (bağımlılık kurulumu atlanır)
        mock_pip.return_value = MagicMock(returncode=0)

        # Kaynak modül oluştur
        repo_dir = downloader.repos_dir / "myrepo" / "auxiliary"
        repo_dir.mkdir(parents=True)
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_CONTENT)

        result = downloader.install_module("myrepo/auxiliary/scanner.py")
        assert result is True
        assert "auxiliary/scanner" in downloader.installed

        # Dosyanın kopyalandığını doğrula
        dest_file = downloader.modules_dir / "auxiliary" / "scanner.py"
        assert dest_file.exists()

    def test_install_invalid_identifier(self, downloader):
        """Geçersiz tanımlayıcı formatı başarısız olmalı."""
        result = downloader.install_module("no_slash_here")
        assert result is False

    def test_install_file_not_found(self, downloader):
        """Varolmayan dosya başarısız olmalı."""
        result = downloader.install_module("myrepo/nonexistent.py")
        assert result is False

    def test_install_not_a_module(self, downloader):
        """BaseModule alt sınıfı olmayan dosya başarısız olmalı."""
        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "utility.py").write_text(NOT_A_MODULE_CONTENT)

        result = downloader.install_module("myrepo/utility.py")
        assert result is False

    @patch("core.module_downloader.subprocess.run")
    def test_install_duplicate_blocked(self, mock_pip, downloader):
        """Aynı modülü tekrar kurmak (force=False) başarısız olmalı."""
        mock_pip.return_value = MagicMock(returncode=0)

        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_CONTENT)

        downloader.install_module("myrepo/scanner.py")
        result = downloader.install_module("myrepo/scanner.py")
        assert result is False

    @patch("core.module_downloader.subprocess.run")
    def test_install_force_overwrite(self, mock_pip, downloader):
        """force=True ile mevcut modül üzerine yazılabilmeli."""
        mock_pip.return_value = MagicMock(returncode=0)

        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_CONTENT)

        downloader.install_module("myrepo/scanner.py")
        result = downloader.install_module("myrepo/scanner.py", force=True)
        assert result is True

    @patch("core.module_downloader.subprocess.run")
    def test_install_with_sha256_valid(self, mock_pip, downloader):
        """Geçerli SHA256 imzası ile kurulum başarılı olmalı."""
        mock_pip.return_value = MagicMock(returncode=0)

        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        module_file = repo_dir / "scanner.py"
        module_file.write_text(FAKE_MODULE_CONTENT)

        # Geçerli SHA256 dosyası oluştur
        sha256 = compute_sha256(module_file)
        (repo_dir / "scanner.sha256").write_text(sha256)

        result = downloader.install_module("myrepo/scanner.py")
        assert result is True

    def test_install_with_sha256_invalid(self, downloader):
        """Geçersiz SHA256 imzası ile kurulum başarısız olmalı."""
        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        module_file = repo_dir / "scanner.py"
        module_file.write_text(FAKE_MODULE_CONTENT)

        # Geçersiz SHA256 dosyası
        (repo_dir / "scanner.sha256").write_text("0000000000000000000000000000000000000000000000000000000000000000")

        result = downloader.install_module("myrepo/scanner.py")
        assert result is False


# ==============================================================================
# SHA256 Doğrulama Testleri
# ==============================================================================

class TestModuleDownloaderVerify:
    """SHA256 imza doğrulama testleri."""

    @pytest.fixture
    def downloader(self, tmp_path):
        installed_file = tmp_path / "installed.json"
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        with patch("core.module_downloader.INSTALLED_MODULES_FILE", str(installed_file)), \
             patch("core.module_downloader.REPOS_DIR", str(repos_dir)):
            dl = ModuleDownloader(modules_dir=str(modules_dir))

        dl.installed_file = installed_file
        dl.repos_dir = repos_dir
        dl.modules_dir = modules_dir
        return dl

    @patch("core.module_downloader.subprocess.run")
    def test_verify_valid(self, mock_pip, downloader):
        """Bütünlüğü bozulmamış modül doğrulamayı geçmeli."""
        mock_pip.return_value = MagicMock(returncode=0)

        # Modülü kur
        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_CONTENT)
        downloader.install_module("myrepo/scanner.py")

        result = downloader.verify_module("scanner")
        assert result is True

    @patch("core.module_downloader.subprocess.run")
    def test_verify_invalid(self, mock_pip, downloader):
        """Bütünlüğü bozulmuş modül doğrulamayı geçememeli."""
        mock_pip.return_value = MagicMock(returncode=0)

        # Modülü kur
        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_CONTENT)
        downloader.install_module("myrepo/scanner.py")

        # Dosyayı boz
        dest = downloader.modules_dir / "scanner.py"
        dest.write_text("# TAMPERED CONTENT")

        result = downloader.verify_module("scanner")
        assert result is False

    def test_verify_not_installed(self, downloader):
        """Kurulu olmayan modül doğrulama None dönmeli."""
        result = downloader.verify_module("nonexistent")
        assert result is None


# ==============================================================================
# Versiyon Kontrolü Testleri
# ==============================================================================

class TestModuleDownloaderVersionControl:
    """Versiyon kontrolü ve güncelleme testleri."""

    @pytest.fixture
    def downloader(self, tmp_path):
        installed_file = tmp_path / "installed.json"
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        with patch("core.module_downloader.INSTALLED_MODULES_FILE", str(installed_file)), \
             patch("core.module_downloader.REPOS_DIR", str(repos_dir)):
            dl = ModuleDownloader(modules_dir=str(modules_dir))

        dl.installed_file = installed_file
        dl.repos_dir = repos_dir
        dl.modules_dir = modules_dir
        return dl

    def test_is_newer_version_true(self, downloader):
        """Yeni versiyon doğru tespit edilmeli."""
        assert downloader._is_newer_version("2.0", "1.0") is True
        assert downloader._is_newer_version("1.1", "1.0") is True
        assert downloader._is_newer_version("1.0.1", "1.0.0") is True

    def test_is_newer_version_false(self, downloader):
        """Eski veya aynı versiyon doğru tespit edilmeli."""
        assert downloader._is_newer_version("1.0", "2.0") is False
        assert downloader._is_newer_version("1.0", "1.0") is False

    @patch("core.module_downloader.subprocess.run")
    def test_check_updates_found(self, mock_pip, downloader):
        """Güncelleme varsa tespit edilmeli."""
        mock_pip.return_value = MagicMock(returncode=0)

        # v1.2 kurulu modül
        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_CONTENT)
        downloader.install_module("myrepo/scanner.py")

        # Depodaki modülü v2.0 yap
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_V2_CONTENT)

        updates = downloader.check_updates()
        assert len(updates) == 1
        assert updates[0]["installed_version"] == "1.2"
        assert updates[0]["available_version"] == "2.0"

    @patch("core.module_downloader.subprocess.run")
    def test_check_updates_none(self, mock_pip, downloader):
        """Güncelleme yoksa boş liste."""
        mock_pip.return_value = MagicMock(returncode=0)

        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_CONTENT)
        downloader.install_module("myrepo/scanner.py")

        # Aynı versiyon → güncelleme yok
        updates = downloader.check_updates()
        assert len(updates) == 0

    @patch("core.module_downloader.subprocess.run")
    def test_update_module(self, mock_pip, downloader):
        """Modül güncelleme başarılı olmalı."""
        mock_pip.return_value = MagicMock(returncode=0)

        repo_dir = downloader.repos_dir / "myrepo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_CONTENT)
        downloader.install_module("myrepo/scanner.py")

        # v2 yap ve güncelle
        (repo_dir / "scanner.py").write_text(FAKE_MODULE_V2_CONTENT)
        result = downloader.update_module("scanner")
        assert result is True
        assert downloader.installed["scanner"]["version"] == "2.0"


# ==============================================================================
# Persistence Testleri
# ==============================================================================

class TestModuleDownloaderPersistence:
    """JSON dosyasına kaydetme ve yükleme testleri."""

    @patch("core.module_downloader.subprocess.run")
    def test_save_and_reload(self, mock_pip, tmp_path):
        """Kaydedilen kayıtların yeniden yüklendiğini doğrular."""
        mock_pip.return_value = MagicMock(returncode=0)

        installed_file = tmp_path / "installed.json"
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        # İlk downloader: modül kur
        with patch("core.module_downloader.INSTALLED_MODULES_FILE", str(installed_file)), \
             patch("core.module_downloader.REPOS_DIR", str(repos_dir)):
            dl1 = ModuleDownloader(modules_dir=str(modules_dir))
            dl1.installed_file = installed_file
            dl1.repos_dir = repos_dir
            dl1.modules_dir = modules_dir

            repo_dir = repos_dir / "myrepo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "scanner.py").write_text(FAKE_MODULE_CONTENT)
            dl1.install_module("myrepo/scanner.py")

        # İkinci downloader: dosyadan yükle
        with patch("core.module_downloader.INSTALLED_MODULES_FILE", str(installed_file)), \
             patch("core.module_downloader.REPOS_DIR", str(repos_dir)):
            dl2 = ModuleDownloader(modules_dir=str(modules_dir))

        assert "scanner" in dl2.installed
        assert dl2.installed["scanner"]["repo"] == "myrepo"


# ==============================================================================
# Download Komutu Testleri
# ==============================================================================

class TestDownloadCommand:
    """Download komut sınıfı testleri."""

    def test_command_metadata(self):
        """Komut metadata değerlerinin doğruluğunu kontrol eder."""
        cmd = Download()
        assert cmd.Name == "download"
        assert cmd.Category == "system"
        assert "search" in cmd.Usage
        assert "install" in cmd.Usage
        assert len(cmd.Examples) > 0

    def test_completions_subcommands(self):
        """Alt komut tamamlamalarını doğrular."""
        cmd = Download()
        completions = cmd.get_completions("download ", "")
        assert "search" in completions
        assert "install" in completions
        assert "update" in completions
        assert "list" in completions
        assert "verify" in completions

    def test_completions_partial_subcommand(self):
        """Kısmi alt komut tamamlamalarını doğrular."""
        cmd = Download()
        completions = cmd.get_completions("download se", "se")
        assert "search" in completions
        assert "install" not in completions

    def test_execute_without_downloader(self):
        """ModuleDownloader yüklenmemişse False döner."""
        cmd = Download()
        original = shared_state.module_downloader
        shared_state.module_downloader = None
        result = cmd.execute("list")
        assert result is False
        shared_state.module_downloader = original
