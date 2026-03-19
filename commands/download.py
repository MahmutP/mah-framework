# Modül indirme ve yönetim komutu.
# Kullanıcının framework konsolundan uzak depolardaki modülleri aramasını,
# indirmesini, güncellemesini ve doğrulamasını sağlar.

from typing import List
from rich import print
from core.command import Command
from core.shared_state import shared_state
from core import logger


class Download(Command):
    """
    Modül İndirme ve Yönetim Komutu.

    Klonlanmış uzak depolardan modül arama, indirme (kurma), güncelleme,
    listeleme ve SHA256 imza doğrulama işlemlerini sağlar.
    """

    Name = "download"
    Description = "Uzak depolardan modül indirme ve yönetim komutu"
    Category = "system"
    Usage = "download [search|install|update|list|verify] [argümanlar]"
    Examples = [
        "download search nmap                           # Depolarda 'nmap' modülü ara",
        "download install myrepo/auxiliary/scanner/x.py  # Modül indir ve kur",
        "download update                                 # Güncellenebilir modülleri kontrol et",
        "download update auxiliary/scanner/x              # Tek modülü güncelle",
        "download list                                   # Kurulu (indirilen) modülleri listele",
        "download verify auxiliary/scanner/x              # SHA256 doğrulama",
    ]

    def __init__(self):
        super().__init__()
        self.completer_function = self.get_completions

    def execute(self, *args, **kwargs) -> bool:
        """
        download komutunun ana yürütme metodu.
        Alt komutu belirler ve ilgili işlemi çağırır.
        """
        # ModuleDownloader kontrolü
        if not shared_state.module_downloader:
            print("[bold red]Hata:[/bold red] Modül İndirici (ModuleDownloader) yüklenemedi.")
            return False

        # Alt komut yoksa veya 'list' ise, kurulu modülleri listele
        if not args or args[0].lower() == "list":
            self._list_installed()
            return True

        subcommand = args[0].lower()

        if subcommand == "search":
            search_term = " ".join(args[1:]) if len(args) > 1 else None
            self._search_modules(search_term)
            return True

        elif subcommand == "install":
            if len(args) < 2:
                print("[bold red]Hata:[/bold red] Kullanım: download install <depo>/<modül_yolu>")
                print("   Örnek: download install myrepo/auxiliary/scanner/my_scanner.py")
                return False
            force = "--force" in args
            module_id = args[1]
            return shared_state.module_downloader.install_module(module_id, force=force)

        elif subcommand == "update":
            if len(args) > 1:
                # Tek modül güncelle
                return shared_state.module_downloader.update_module(args[1])
            else:
                # Tüm modüllerin güncelleme kontrolü
                self._check_updates()
                return True

        elif subcommand == "verify":
            if len(args) < 2:
                print("[bold red]Hata:[/bold red] Kullanım: download verify <modül_yolu>")
                print("   Örnek: download verify auxiliary/scanner/my_scanner")
                return False
            result = shared_state.module_downloader.verify_module(args[1])
            return result is True

        else:
            print(f"[bold red]Hata:[/bold red] Bilinmeyen alt komut: {subcommand}")
            print("   Kullanılabilir alt komutlar: search, install, update, list, verify")
            return False

    def _search_modules(self, search_term=None) -> None:
        """Uzak depolardaki modülleri arar ve listeler."""
        if not shared_state.module_downloader:
            return

        if search_term:
            print(f"\n[bold cyan]🔍 Aranıyor:[/bold cyan] '{search_term}'\n")
        else:
            print("\n[bold cyan]📦 Tüm depo modülleri taranıyor...[/bold cyan]\n")

        modules = shared_state.module_downloader.scan_repos(search_term)

        if not modules:
            print("[dim]Eşleşen modül bulunamadı.[/dim]")
            if not search_term:
                print("   Depo eklemek için: [bold]repo add <ad> <url>[/bold]")
                print("   Depoları güncellemek için: [bold]repo update[/bold]")
            return

        # Modülleri depoya göre grupla
        by_repo = {}
        for mod in modules:
            repo = mod["repo"]
            if repo not in by_repo:
                by_repo[repo] = []
            by_repo[repo].append(mod)

        total = 0
        for repo_name, repo_modules in by_repo.items():
            print(f"[bold green]📁 {repo_name}[/bold green]")
            print(f"   {'Modül':<35} {'Versiyon':<10} {'Yazar':<15} {'İmza':<6} Açıklama")
            print(f"   {'-----':<35} {'-------':<10} {'-----':<15} {'----':<6} --------")

            for mod in repo_modules:
                name_path = f"{repo_name}/{mod['relative_path']}"
                # Uzun yolları kısalt
                if len(name_path) > 34:
                    name_path = "..." + name_path[-31:]

                sig = "[green]✓[/green]" if mod["has_signature"] else "[dim]—[/dim]"
                desc = mod["description"][:40] if mod["description"] else "—"

                print(f"   {name_path:<35} {mod['version']:<10} {mod['author']:<15} {sig:<6} {desc}")
                total += 1

            print()

        print(f"   Toplam: {total} modül bulundu\n")

    def _list_installed(self) -> None:
        """Kurulu (indirilen) modülleri listeler."""
        if not shared_state.module_downloader:
            return

        installed = shared_state.module_downloader.list_installed()

        if not installed:
            print("\n[dim]Kurulu (indirilen) modül bulunamadı.[/dim]")
            print("   Modül aramak için: [bold]download search <terim>[/bold]")
            print("   Modül kurmak için: [bold]download install <depo>/<modül>[/bold]\n")
            return

        print("\nInstalled Modules (Downloaded)")
        print("------------------------------\n")

        print(f"   {'Modül':<35} {'Versiyon':<10} {'Kaynak Depo':<15} Kurulum Tarihi")
        print(f"   {'-----':<35} {'-------':<10} {'-----------':<15} --------------")

        for mod_key, info in installed.items():
            version = info.get("version", "?")
            repo = info.get("repo", "?")

            installed_at = info.get("installed_at", "—")
            if installed_at and installed_at != "—":
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(installed_at)
                    installed_at = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    installed_at = "—"

            mod_display = mod_key
            if len(mod_display) > 34:
                mod_display = "..." + mod_display[-31:]

            print(f"   {mod_display:<35} {version:<10} {repo:<15} {installed_at}")

        print(f"\n   Toplam: {len(installed)} modül\n")

    def _check_updates(self) -> None:
        """Kurulu modüllerin güncelleme kontrolünü yapar."""
        if not shared_state.module_downloader:
            return

        print("\n[bold cyan]🔄 Güncelleme kontrolü yapılıyor...[/bold cyan]\n")

        updates = shared_state.module_downloader.check_updates()

        if not updates:
            print("[bold green]✓[/bold green] Tüm kurulu modüller güncel.\n")
            return

        print(f"[bold yellow]⚠ {len(updates)} modül için güncelleme mevcut:[/bold yellow]\n")

        print(f"   {'Modül':<35} {'Kurulu':<10} {'Mevcut':<10} Kaynak")
        print(f"   {'-----':<35} {'------':<10} {'------':<10} ------")

        for upd in updates:
            mod_display = upd["module"]
            if len(mod_display) > 34:
                mod_display = "..." + mod_display[-31:]

            print(f"   {mod_display:<35} {upd['installed_version']:<10} [green]{upd['available_version']}[/green]{'':<4} {upd['repo']}")

        print(f"\n   Güncellemek için: [bold]download update <modül_yolu>[/bold]\n")

    def get_completions(self, text: str, word_before_cursor: str) -> List[str]:
        """Otomatik tamamlama desteği."""
        parts = text.split()

        # "download" yazıldıysa alt komut öner
        if len(parts) == 1 or (len(parts) == 2 and not text.endswith(' ')):
            subcommands = ["search", "install", "update", "list", "verify"]
            if len(parts) == 2:
                return [s for s in subcommands if s.startswith(parts[1].lower())]
            return subcommands

        # "download update/verify" sonrası modül adı tamamla
        if len(parts) >= 2:
            subcommand = parts[1].lower()
            if subcommand in ["update", "verify"]:
                if not shared_state.module_downloader:
                    return []
                module_keys = shared_state.module_downloader.get_installed_module_keys()
                if len(parts) == 3 and not text.endswith(' '):
                    return [k for k in module_keys if k.startswith(parts[2].lower())]
                return module_keys

        return []
