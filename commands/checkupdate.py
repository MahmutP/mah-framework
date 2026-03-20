# Güncelleme kontrolü komutu
# Remote repo ile karşılaştırarak yeni versiyon olup olmadığını kontrol eder
import subprocess
from pathlib import Path
from typing import Any
import argparse
import datetime
import shutil

from core.command import Command
from core import logger
from rich import print


class CheckUpdateCommand(Command):
    """Güncelleme kontrolü ve self-update yapan komut.
    
    Remote repository ile lokal commit sayısını karşılaştırarak
    yeni bir güncelleme olup olmadığını kontrol eder,
    gerekirse changelog gösterir, sistemin yedeğini alır
    ve güncellemeyi otomatik kurar.
    """
    
    Name = "checkupdate"
    Description = "Güncelleme kontrolü yapar. (--apply ile günceller, --backup ile yedekler)"
    Category = "system"
    Aliases = ["update", "check"]
    Usage = "checkupdate [-a | --apply] [-b | --backup]"
    Examples = [
        "checkupdate              # Sadece uzak repo ile karşılaştırarak güncellemeleri kontrol eder",
        "checkupdate -a           # Varsa yeni güncellemeyi otomatik olarak uygular (self-update)",
        "checkupdate -b           # Güncellemeden bağımsız olarak tüm projenin yedeğini alır",
        "checkupdate -a -b        # Güncellemeyi uygulamadan önce projenin yedeğini alır"
    ]
    
    def __init__(self):
        super().__init__()
        self.completer_function = self._checkupdate_completer

    def _checkupdate_completer(self, text: str, word_before_cursor: str) -> list[str]:
        """checkupdate komutu için argüman otomatik tamamlama."""
        options = ["-a", "--apply", "-b", "--backup"]
        if word_before_cursor:
            return sorted([opt for opt in options if opt.startswith(word_before_cursor)])
        return sorted(options)
    
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

    def _get_changelog(self, local_ref: str, remote_ref: str) -> list[str]:
        """İki referans arasındaki commit loglarını (changelog) döndürür."""
        try:
            result = subprocess.check_output(
                ["git", "log", f"{local_ref}..{remote_ref}", "--oneline"],
                stderr=subprocess.DEVNULL,
                cwd=str(Path(__file__).parent.parent)
            ).decode().strip()
            
            if not result:
                return []
                
            return [line.strip() for line in result.split('\n') if line.strip()]
        except Exception as e:
            logger.error(f"Changelog alınamadı: {e}")
            return []

    def _create_backup(self) -> bool:
        """Framework dizininin .git hariç yedeğini alır."""
        try:
            framework_dir = Path(__file__).parent.parent
            backup_dir = framework_dir / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"mah_framework_backup_{timestamp}"
            backup_path = backup_dir / backup_name
            
            print(f"[*] Yedek oluşturuluyor: [bold]{backup_dir.name}/{backup_name}.zip[/bold]...")
            
            shutil.make_archive(
                str(backup_path),
                'zip',
                str(framework_dir)
            )
            
            print(f"[bold green]✓[/bold green] Yedekleme başarıyla tamamlandı.")
            logger.info(f"Framework yedeği alındı: {backup_path}.zip")
            return True
        except Exception as e:
            print(f"[bold red]✗[/bold red] Yedekleme başarısız oldu: {e}")
            logger.error(f"Yedekleme hatası: {e}")
            return False
            
    def _apply_update(self) -> bool:
        """Git üzerinden güncellemeyi indirip uygular."""
        print("[*] Güncelleme indiriliyor (git pull)...")
        try:
            framework_dir = str(Path(__file__).parent.parent)
            result = subprocess.run(
                ["git", "pull"],
                cwd=framework_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"[bold green]✓[/bold green] Kod güncellendi.")
                
                print("[*] Bağımlılıklar güncelleniyor (pip install -r requirements.txt)...")
                subprocess.run(
                    ["pip3", "install", "-r", "requirements.txt"],
                    cwd=framework_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"[bold green]✓[/bold green] Güncelleme başarıyla uygulandı!")
                logger.info("Otomatik güncelleme (self-update) başarıyla tamamlandı.")
                return True
            else:
                print(f"[bold red]✗[/bold red] Güncelleme indirilemedi: {result.stderr}")
                logger.error(f"Git pull hatası: {result.stderr}")
                return False
        except Exception as e:
            print(f"[bold red]✗[/bold red] Beklenmeyen bir hata oluştu: {e}")
            logger.error(f"Self-update beklenmeyen hata: {e}")
            return False

    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Güncelleme kontrolünü ve opsiyonel işlemleri çalıştırır.
        
        Çalışma mantığı:
            1. Argümanları kontrol et
            2. Lokal ve remote commit sayısını alıp karşılaştır
            3. Fark varsa changelog göster
            4. İstenmişse yedek al ve/veya güncellemeyi uygula
        
        Returns:
            bool: Başarılı olup olmadığı
        """
        parser = argparse.ArgumentParser(prog="checkupdate", add_help=False)
        parser.add_argument("-a", "--apply", action="store_true", help="Güncellemeyi otomatik indir ve kur")
        parser.add_argument("-b", "--backup", action="store_true", help="Zorunlu yedek al")
        
        try:
            parsed_args, unknown = parser.parse_known_args(args)
        except argparse.ArgumentError:
            print("[bold red]✗[/bold red] Geçersiz argüman. (Kullanım: checkupdate [-a] [-b])")
            return False

        print("\n[bold cyan]🔄 Güncelleme Sistemi[/bold cyan]\n")
        
        if parsed_args.backup:
            self._create_backup()
            print()
            
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
        remote_branch = "origin/main"
        
        if remote_commits is None:
            # origin/master dene
            remote_commits = self._get_commit_count("origin/master")
            remote_branch = "origin/master"
        
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
            print(f"    {diff} yeni commit var.\n")
            
            # Changelog göster
            changelog = self._get_changelog("HEAD", remote_branch)
            if changelog:
                print("    [bold underline]Yeni Özellikler / Değişiklikler (Changelog):[/bold underline]")
                for log in changelog[:10]:
                    print(f"      - {log}")
                if len(changelog) > 10:
                    print(f"      - ... (ve {len(changelog) - 10} commit daha)")
                print()
                
            if parsed_args.apply:
                if not parsed_args.backup:
                    print("[*] Otomatik güncelleme başlatılıyor...\n")
                self._apply_update()
            else:
                print(f"    Güncellemek için:")
                print(f"    - [bold]checkupdate --apply[/bold] komutunu kullanın")
                print(f"    - Ya da manuel: [bold]git pull[/bold] ve [bold]pip3 install -r requirements.txt[/bold]")
            
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

