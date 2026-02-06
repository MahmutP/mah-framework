# Güncelleme kontrolü komutu
# Remote repo ile karşılaştırarak yeni versiyon olup olmadığını kontrol eder
import subprocess
from pathlib import Path
from typing import Any

from core.command import Command
from core import logger
from rich import print


class CheckUpdateCommand(Command):
    """Güncelleme kontrolü yapan komut.
    
    Remote repository ile lokal commit sayısını karşılaştırarak
    yeni bir güncelleme olup olmadığını kontrol eder.
    """
    
    Name = "checkupdate"
    Description = "Yeni güncelleme olup olmadığını kontrol eder."
    Category = "system"
    Aliases = ["update", "check"]
    Usage = "checkupdate"
    Examples = [
        "checkupdate              # Uzak repo ile karşılaştırır",
        "update                   # 'checkupdate' için alias",
        "check                    # 'checkupdate' için alias"
    ]
    
    def _get_commit_count(self, ref: str) -> int | None:
        """Belirtilen referans için commit sayısını döndürür.
        
        Args:
            ref: Git referansı (HEAD, origin/main, vb.)
            
        Returns:
            Commit sayısı veya hata durumunda None
        """
        try:
            result = subprocess.check_output(
                ["git", "rev-list", "--count", ref],
                stderr=subprocess.DEVNULL,
                cwd=str(Path(__file__).parent.parent)
            ).decode().strip()
            return int(result)
        except Exception:
            return None
    
    def _commits_to_version(self, commits: int) -> str:
        """Commit sayısını versiyon string'ine çevirir.
        
        Args:
            commits: Commit sayısı
            
        Returns:
            Versiyon string'i (örn: v1.3.6)
        """
        major = commits // 100
        minor = (commits % 100) // 10
        patch = commits % 10
        return f"v{major}.{minor}.{patch}"
    
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Güncelleme kontrolünü çalıştırır.
        
        Çalışma mantığı:
            1. Lokal commit sayısını al
            2. Remote'u fetch et
            3. Remote commit sayısını al
            4. Karşılaştır ve sonucu göster
        
        Returns:
            bool: Başarılı olup olmadığı
        """
        print("\n[bold cyan]🔄 Güncelleme Kontrolü[/bold cyan]\n")
        
        # 1. Lokal commit sayısını al
        local_commits = self._get_commit_count("HEAD")
        
        if local_commits is None:
            print("[bold red]✗[/bold red] Git repository bulunamadı veya hata oluştu.")
            logger.error("Güncelleme kontrolü: Git repository bulunamadı")
            return False
        
        local_version = self._commits_to_version(local_commits)
        print(f"[*] Mevcut versiyon: [bold]{local_version}[/bold] ({local_commits} commits)")
        
        # 2. Remote'u fetch et
        print("[*] Uzak sunucu kontrol ediliyor...")
        try:
            subprocess.run(
                ["git", "fetch", "--quiet"],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                cwd=str(Path(__file__).parent.parent),
                timeout=10
            )
        except subprocess.TimeoutExpired:
            print("[bold yellow]⚠[/bold yellow] Bağlantı zaman aşımına uğradı.")
            logger.warning("Güncelleme kontrolü: Fetch zaman aşımı")
            return False
        except Exception as e:
            print(f"[bold yellow]⚠[/bold yellow] Uzak sunucuya bağlanılamadı: {e}")
            logger.warning(f"Güncelleme kontrolü: Fetch hatası - {e}")
            return False
        
        # 3. Remote commit sayısını al
        remote_commits = self._get_commit_count("origin/main")
        
        if remote_commits is None:
            # origin/master dene
            remote_commits = self._get_commit_count("origin/master")
        
        if remote_commits is None:
            print("[bold yellow]⚠[/bold yellow] Uzak branch bulunamadı.")
            logger.warning("Güncelleme kontrolü: Remote branch bulunamadı")
            return False
        
        remote_version = self._commits_to_version(remote_commits)
        print(f"[*] Uzak versiyon:   [bold]{remote_version}[/bold] ({remote_commits} commits)")
        
        # 4. Karşılaştır
        print()
        if remote_commits > local_commits:
            diff = remote_commits - local_commits
            print(f"[bold yellow]⚠ Güncelleme mevcut![/bold yellow]")
            print(f"    {diff} yeni commit var.")
            print(f"    Güncellemek için:")
            print(f"    1. [bold]git pull[/bold]")
            print(f"    2. [bold]pip3 install -r requirements.txt[/bold]")
            logger.info(f"Güncelleme mevcut: {local_version} → {remote_version}")
        elif remote_commits < local_commits:
            diff = local_commits - remote_commits
            print(f"[bold magenta]ℹ Lokal versiyon daha yeni![/bold magenta]")
            print(f"    {diff} commit push edilmedi.")
            print(f"    Push için: [bold]git push[/bold]")
        else:
            print(f"[bold green]✓ Güncel![/bold green]")
            print(f"    En son sürümü kullanıyorsunuz.")
            logger.info("Güncelleme kontrolü: Güncel")
        
        print()
        return True
