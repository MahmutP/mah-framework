# Uzak modül deposu yönetim komutu.
# Kullanıcının framework konsolundan uzak depoları eklemesini, güncellemesini,
# listelemesini ve silmesini sağlar.

from typing import List
from rich import print
from core.command import Command
from core.shared_state import shared_state
from core import logger


class Repo(Command):
    """
    Uzak modül deposu yönetim komutu.
    
    GitHub/GitLab gibi uzak kaynaklardan modül deposu ekleme, güncelleme,
    listeleme ve silme işlemlerini sağlar.
    """

    Name = "repo"
    Description = "Uzak modül deposu yönetim komutu"
    Category = "system"
    Usage = "repo [add|update|list|remove] [argümanlar]"
    Examples = [
        "repo list                                    # Kayıtlı depoları listele",
        "repo add myrepo https://github.com/user/repo # Yeni depo ekle",
        "repo update                                  # Tüm depoları güncelle",
        "repo update myrepo                           # Tek depoyu güncelle",
        "repo remove myrepo                           # Depoyu sil",
    ]

    def __init__(self):
        super().__init__()
        self.completer_function = self.get_completions

    def execute(self, *args, **kwargs) -> bool:
        """
        repo komutunun ana yürütme metodu.
        Alt komutu belirler ve ilgili işlemi çağırır.
        """
        # RepoManager kontrolü
        if not shared_state.repo_manager:
            print("[bold red]Hata:[/bold red] Depo Yöneticisi (RepoManager) yüklenemedi.")
            return False

        # Alt komut yoksa veya 'list' ise, depoları listele
        if not args or args[0].lower() == "list":
            self._list_repos()
            return True

        subcommand = args[0].lower()

        if subcommand == "add":
            if len(args) < 3:
                print("[bold red]Hata:[/bold red] Kullanım: repo add <ad> <url>")
                print("   Örnek: repo add myrepo https://github.com/user/repo.git")
                return False
            return shared_state.repo_manager.add_repo(args[1], args[2])

        elif subcommand == "update":
            repo_name = args[1] if len(args) > 1 else None
            return shared_state.repo_manager.update_repo(repo_name)

        elif subcommand == "remove":
            if len(args) < 2:
                print("[bold red]Hata:[/bold red] Kullanım: repo remove <ad>")
                print("   Örnek: repo remove myrepo")
                return False
            return shared_state.repo_manager.remove_repo(args[1])

        elif subcommand == "info":
            if len(args) < 2:
                print("[bold red]Hata:[/bold red] Kullanım: repo info <ad>")
                return False
            self._show_info(args[1])
            return True

        else:
            print(f"[bold red]Hata:[/bold red] Bilinmeyen alt komut: {subcommand}")
            print("   Kullanılabilir alt komutlar: add, update, list, remove, info")
            return False

    def _list_repos(self) -> None:
        """Kayıtlı tüm depoları tablo olarak gösterir."""
        if not shared_state.repo_manager:
            return

        repos = shared_state.repo_manager.list_repos()
        if not repos:
            print("\n[dim]Kayıtlı depo bulunamadı.[/dim]")
            print("   Yeni depo eklemek için: [bold]repo add <ad> <url>[/bold]\n")
            return

        print("\nRemote Repositories")
        print("-------------------\n")

        # Başlık satırı
        print(f"   {'İsim':<20} {'Durum':<12} {'Son Güncelleme':<22} URL")
        print(f"   {'----':<20} {'-----':<12} {'--------------':<22} ---")

        for name, info in repos.items():
            status = info.get("status", "bilinmiyor")

            # Durum renklendirme
            status_display = status.ljust(12)
            if status == "cloned" or status == "updated":
                status_colored = f"[green]{status_display}[/green]"
            elif status == "added":
                status_colored = f"[yellow]{status_display}[/yellow]"
            elif status == "error":
                status_colored = f"[red]{status_display}[/red]"
            else:
                status_colored = f"[dim]{status_display}[/dim]"

            # Son güncelleme
            updated_at = info.get("updated_at")
            if updated_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated_at)
                    updated_str = dt.strftime("%Y-%m-%d %H:%M").ljust(22)
                except (ValueError, TypeError):
                    updated_str = "—".ljust(22)
            else:
                updated_str = "—".ljust(22)

            url = info.get("url", "—")
            name_padded = name.ljust(20)

            print(f"   {name_padded} {status_colored} {updated_str} {url}")

        print(f"\n   Toplam: {len(repos)} depo\n")

    def _show_info(self, name: str) -> None:
        """Tek bir deponun ayrıntılı bilgilerini gösterir."""
        if not shared_state.repo_manager:
            return

        repo = shared_state.repo_manager.get_repo(name)
        if not repo:
            print(f"[bold red]Hata:[/bold red] '{name}' adında kayıtlı bir depo bulunamadı.")
            return

        print(f"\n[bold cyan]Depo Detayları: {name}[/bold cyan]")
        print("-" * 50)
        print(f"[bold]URL:[/bold]            {repo.get('url', '—')}")
        print(f"[bold]Durum:[/bold]          {repo.get('status', '—')}")
        print(f"[bold]Eklenme:[/bold]        {repo.get('added_at', '—')}")
        print(f"[bold]Son Güncelleme:[/bold] {repo.get('updated_at', '—')}")

        # Klonlanmış dizin bilgisi
        from pathlib import Path
        from core.cont import REPOS_DIR
        repo_path = Path(REPOS_DIR) / name.strip().lower()
        if repo_path.exists():
            # Dizindeki dosya sayısı
            file_count = sum(1 for _ in repo_path.rglob('*') if _.is_file())
            print(f"[bold]Yerel Dizin:[/bold]    {repo_path}")
            print(f"[bold]Dosya Sayısı:[/bold]   {file_count}")
        else:
            print(f"[bold]Yerel Dizin:[/bold]    [dim]Henüz klonlanmadı[/dim]")

        print("-" * 50)

    def get_completions(self, text: str, word_before_cursor: str) -> List[str]:
        """Otomatik tamamlama desteği."""
        parts = text.split()

        # "repo" yazıldıysa alt komut öner
        if len(parts) == 1 or (len(parts) == 2 and not text.endswith(' ')):
            subcommands = ["add", "update", "list", "remove", "info"]
            if len(parts) == 2:
                return [s for s in subcommands if s.startswith(parts[1].lower())]
            return subcommands

        # "repo update ", "repo remove ", "repo info " sonrası depo adı tamamla
        if len(parts) >= 2:
            subcommand = parts[1].lower()
            if subcommand in ["update", "remove", "info"]:
                if not shared_state.repo_manager:
                    return []
                repo_names = shared_state.repo_manager.get_repo_names()
                if len(parts) == 3 and not text.endswith(' '):
                    return [r for r in repo_names if r.startswith(parts[2].lower())]
                return repo_names

        return []
