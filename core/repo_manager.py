# core/repo_manager.py
# Uzak modül depolarını yönetmek için kullanılan sınıf.
# GitHub/GitLab gibi uzak kaynaklardan depo ekleme, güncelleme, listeleme ve silme işlemlerini sağlar.

import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any

from core.cont import REPOS_FILE, REPOS_DIR
from core import logger
from rich import print


class RepoManager:
    """
    Uzak Modül Deposu Yönetim Sınıfı (RepoManager).
    
    Görevleri:
    1. Uzak depoları (GitHub/GitLab) kayıt altına almak.
    2. Depoları yerel diske klonlamak ve güncellemek.
    3. Depo bilgilerini JSON dosyasında kalıcı olarak saklamak.
    4. Depo silme ve listeleme işlemlerini yönetmek.
    """

    def __init__(self) -> None:
        """
        RepoManager başlatıcı metod.
        Yapılandırma dosyasını ve depo dizinini hazırlar.
        """
        self.repos_file = Path(REPOS_FILE)
        self.repos_dir = Path(REPOS_DIR)
        self.repos: Dict[str, Dict[str, Any]] = {}

        # Gerekli dosya ve dizinleri oluştur.
        self._ensure_repos_file()
        self._ensure_repos_dir()

        # Mevcut depo kayıtlarını yükle.
        self.load_repos()

    def _ensure_repos_file(self) -> None:
        """
        Depo yapılandırma dosyasının (repos.json) varlığını kontrol eder.
        Yoksa boş bir JSON dosyası oluşturur.
        """
        if not self.repos_file.exists():
            self.repos_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.repos_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4)
            logger.info(f"Depo yapılandırma dosyası oluşturuldu: {REPOS_FILE}")

    def _ensure_repos_dir(self) -> None:
        """
        Depoların klonlanacağı dizinin varlığını kontrol eder.
        Yoksa oluşturur.
        """
        if not self.repos_dir.exists():
            self.repos_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Depo dizini oluşturuldu: {REPOS_DIR}")

    def load_repos(self) -> None:
        """
        Depo yapılandırma dosyasını okur ve belleğe yükler.
        """
        try:
            with open(self.repos_file, 'r', encoding='utf-8') as f:
                self.repos = json.load(f)
            logger.info(f"{len(self.repos)} depo kaydı yüklendi")
        except FileNotFoundError:
            logger.warning(f"Depo dosyası bulunamadı: {REPOS_FILE}. Yeni dosya oluşturuluyor.")
            self._ensure_repos_file()
            self.repos = {}
        except json.JSONDecodeError as e:
            logger.error(f"Depo dosyası okunamadı '{REPOS_FILE}': {e}")
            print(f"[bold red]Hata:[/bold red] Depo yapılandırma dosyası bozuk: {e}")
            self.repos = {}

    def save_repos(self) -> None:
        """
        Mevcut depo kayıtlarını JSON dosyasına kaydeder.
        """
        try:
            with open(self.repos_file, 'w', encoding='utf-8') as f:
                json.dump(self.repos, f, indent=4, ensure_ascii=False)
        except PermissionError:
            print(f"[bold red]Hata:[/bold red] Depo dosyası yazma izni hatası: {REPOS_FILE}")
            logger.exception("Depo dosyası yazma izni hatası")
        except IOError as e:
            print(f"[bold red]Hata:[/bold red] Depo dosyası yazma hatası: {e}")
            logger.exception("Depo dosyası yazma hatası")

    def _validate_url(self, url: str) -> bool:
        """
        Depo URL'sinin geçerli bir Git deposu URL'si olup olmadığını doğrular.

        Args:
            url (str): Doğrulanacak URL.

        Returns:
            bool: Geçerli ise True, değilse False.
        """
        # HTTPS ve SSH formatlarını destekle
        valid_prefixes = (
            "https://github.com/",
            "https://gitlab.com/",
            "https://bitbucket.org/",
            "git@github.com:",
            "git@gitlab.com:",
            "git@bitbucket.org:",
            "http://",
            "https://",
        )
        return url.startswith(valid_prefixes)

    def add_repo(self, name: str, url: str) -> bool:
        """
        Yeni bir uzak depo ekler.

        Args:
            name (str): Deponun yerel adı (benzersiz tanımlayıcı).
            url (str): Deponun uzak URL'si.

        Returns:
            bool: Ekleme başarılı ise True, aksi halde False.
        """
        # İsim kontrolü
        if not name or not name.strip():
            print("[bold red]Hata:[/bold red] Depo adı boş olamaz.")
            return False

        name = name.strip().lower()

        # Aynı isimde depo var mı?
        if name in self.repos:
            print(f"[bold red]Hata:[/bold red] '{name}' adında bir depo zaten kayıtlı.")
            print(f"   Mevcut URL: {self.repos[name]['url']}")
            return False

        # URL doğrulama
        if not self._validate_url(url):
            print(f"[bold red]Hata:[/bold red] Geçersiz depo URL'si: {url}")
            print("   Desteklenen formatlar: https://github.com/..., git@github.com:...")
            return False

        # Depo kaydını oluştur
        self.repos[name] = {
            "url": url,
            "added_at": datetime.now().isoformat(),
            "updated_at": None,
            "status": "added"
        }

        self.save_repos()
        logger.info(f"Yeni depo eklendi: {name} -> {url}")
        print(f"[bold green]✓[/bold green] Depo eklendi: [bold]{name}[/bold]")
        print(f"   URL: {url}")
        print(f"\n   Depoyu klonlamak için: [bold]repo update {name}[/bold]")
        return True

    def remove_repo(self, name: str) -> bool:
        """
        Kayıtlı bir depoyu siler.
        Depo dizini de (klonlanmış dosyalar) silinir.

        Args:
            name (str): Silinecek deponun adı.

        Returns:
            bool: Silme başarılı ise True, aksi halde False.
        """
        name = name.strip().lower()

        if name not in self.repos:
            print(f"[bold red]Hata:[/bold red] '{name}' adında kayıtlı bir depo bulunamadı.")
            return False

        # Klonlanmış dizini temizle
        repo_path = self.repos_dir / name
        if repo_path.exists():
            try:
                shutil.rmtree(repo_path)
                logger.info(f"Depo dizini silindi: {repo_path}")
            except Exception as e:
                print(f"[bold yellow]⚠[/bold yellow] Depo dizini silinirken hata: {e}")
                logger.exception(f"Depo dizini silme hatası: {repo_path}")

        # Kayıttan sil
        del self.repos[name]
        self.save_repos()

        logger.info(f"Depo silindi: {name}")
        print(f"[bold green]✓[/bold green] Depo silindi: [bold]{name}[/bold]")
        return True

    def list_repos(self) -> Dict[str, Dict[str, Any]]:
        """
        Kayıtlı tüm depoları döndürür.

        Returns:
            Dict[str, Dict[str, Any]]: Depo adı -> Depo bilgileri sözlüğü.
        """
        return self.repos

    def update_repo(self, name: Optional[str] = None) -> bool:
        """
        Bir depoyu veya tüm depoları günceller (klonla / pull).
        
        Eğer depo henüz klonlanmamışsa `git clone`, zaten mevcutsa `git pull` yapar.

        Args:
            name (str, optional): Güncellenecek deponun adı. 
                                   None ise tüm depolar güncellenir.

        Returns:
            bool: İşlem başarılı ise True, aksi halde False.
        """
        if name:
            name = name.strip().lower()
            if name not in self.repos:
                print(f"[bold red]Hata:[/bold red] '{name}' adında kayıtlı bir depo bulunamadı.")
                return False
            return self._update_single_repo(name)
        else:
            # Tüm depoları güncelle
            if not self.repos:
                print("[bold yellow]⚠[/bold yellow] Kayıtlı depo bulunamadı.")
                return False

            print(f"[bold cyan]🔄 {len(self.repos)} depo güncelleniyor...[/bold cyan]\n")
            all_success = True
            for repo_name in self.repos:
                if not self._update_single_repo(repo_name):
                    all_success = False
                print()  # Depo aralarında boşluk

            return all_success

    def _update_single_repo(self, name: str) -> bool:
        """
        Tek bir depoyu günceller.

        Args:
            name (str): Güncellenecek deponun adı.

        Returns:
            bool: Başarılı ise True.
        """
        repo_info = self.repos[name]
        url = repo_info["url"]
        repo_path = self.repos_dir / name

        if repo_path.exists() and (repo_path / ".git").exists():
            # Depo zaten klonlanmış, git pull yap
            return self._pull_repo(name, repo_path)
        else:
            # Depo henüz klonlanmamış, git clone yap
            return self._clone_repo(name, url, repo_path)

    def _clone_repo(self, name: str, url: str, dest: Path) -> bool:
        """
        Depoyu uzak kaynaktan klonlar.

        Args:
            name (str): Depo adı.
            url (str): Uzak URL.
            dest (Path): Klonlanacak hedef dizin.

        Returns:
            bool: Başarılı ise True.
        """
        print(f"[bold cyan]📥 Klonlanıyor:[/bold cyan] {name} ({url})")

        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, str(dest)],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                self.repos[name]["status"] = "cloned"
                self.repos[name]["updated_at"] = datetime.now().isoformat()
                self.save_repos()
                print(f"[bold green]✓[/bold green] Başarıyla klonlandı: [bold]{name}[/bold]")
                logger.info(f"Depo klonlandı: {name} -> {dest}")
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else "Bilinmeyen hata"
                print(f"[bold red]✗[/bold red] Klonlama başarısız: {error_msg}")
                self.repos[name]["status"] = "error"
                self.save_repos()
                logger.error(f"Depo klonlama hatası ({name}): {error_msg}")
                return False

        except subprocess.TimeoutExpired:
            print(f"[bold yellow]⚠[/bold yellow] Zaman aşımı: {name}")
            logger.warning(f"Depo klonlama zaman aşımı: {name}")
            return False
        except FileNotFoundError:
            print("[bold red]✗[/bold red] Git bulunamadı. Lütfen Git'in kurulu olduğundan emin olun.")
            logger.error("Git komutu bulunamadı")
            return False
        except Exception as e:
            print(f"[bold red]✗[/bold red] Beklenmeyen hata: {e}")
            logger.exception(f"Depo klonlama hatası: {name}")
            return False

    def _pull_repo(self, name: str, repo_path: Path) -> bool:
        """
        Mevcut bir depoyu günceller (git pull).

        Args:
            name (str): Depo adı.
            repo_path (Path): Deponun yerel dizini.

        Returns:
            bool: Başarılı ise True.
        """
        print(f"[bold cyan]🔄 Güncelleniyor:[/bold cyan] {name}")

        try:
            result = subprocess.run(
                ["git", "pull", "--ff-only"],
                capture_output=True,
                text=True,
                cwd=str(repo_path),
                timeout=60
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                self.repos[name]["status"] = "updated"
                self.repos[name]["updated_at"] = datetime.now().isoformat()
                self.save_repos()

                if "Already up to date" in output or "Already up-to-date" in output:
                    print(f"[bold green]✓[/bold green] Zaten güncel: [bold]{name}[/bold]")
                else:
                    print(f"[bold green]✓[/bold green] Güncellendi: [bold]{name}[/bold]")

                logger.info(f"Depo güncellendi: {name}")
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else "Bilinmeyen hata"
                print(f"[bold red]✗[/bold red] Güncelleme başarısız: {error_msg}")
                self.repos[name]["status"] = "error"
                self.save_repos()
                logger.error(f"Depo güncelleme hatası ({name}): {error_msg}")
                return False

        except subprocess.TimeoutExpired:
            print(f"[bold yellow]⚠[/bold yellow] Zaman aşımı: {name}")
            logger.warning(f"Depo güncelleme zaman aşımı: {name}")
            return False
        except Exception as e:
            print(f"[bold red]✗[/bold red] Beklenmeyen hata: {e}")
            logger.exception(f"Depo güncelleme hatası: {name}")
            return False

    def get_repo(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Belirtilen depo bilgilerini döndürür.

        Args:
            name (str): Depo adı.

        Returns:
            Optional[Dict[str, Any]]: Depo bilgileri veya None.
        """
        return self.repos.get(name.strip().lower())

    def get_repo_names(self) -> List[str]:
        """
        Kayıtlı tüm depo isimlerini döndürür.

        Returns:
            List[str]: Depo isimleri listesi.
        """
        return list(self.repos.keys())
