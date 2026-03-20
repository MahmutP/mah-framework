from typing import List, Optional
from rich.table import Table
from rich import print
from core.command import Command
from core.shared_state import shared_state
from core import logger


class Plugins(Command):
    Name = "plugins"
    Description = "Plugin yönetim komutu"
    Category = "core"
    Usage = "plugins [list|enable|disable|info|search|install|update|remove] [argümanlar]"
    def __init__(self):
        super().__init__()
        self.completer_function = self.get_completions # Otomatik tamamlama aktif
    Examples = [
        "plugins list",
        "plugins info 'Audit Logger'",
        "plugins enable 'Audit Logger'",
        "plugins disable 'Audit Logger'",
        "plugins search             # Uzak depolarda eklenti ara",
        "plugins install repo/name  # Uzak depodan eklenti kur",
        "plugins update name        # Kurulu bir eklentiyi güncelle",
        "plugins remove name        # Kurulu bir eklentiyi sil"
    ]

    def execute(self, *args, **kwargs) -> bool:
        if not shared_state.plugin_manager:
            print("[bold red]Hata:[/bold red] Plugin Manager yüklenemedi.")
            return False

        if not args or args[0] == "list":
            self._list_plugins()
            return True
        
        subcommand = args[0].lower()
        
        if subcommand == "enable":
            if len(args) < 2:
                print("[bold red]Hata:[/bold red] Plugin adı belirtilmedi.")
                return False
            self._enable_plugin(args[1])
            return True
        
        elif subcommand == "disable":
            if len(args) < 2:
                print("[bold red]Hata:[/bold red] Plugin adı belirtilmedi.")
                return False
            self._disable_plugin(args[1])
            return True
        
        elif subcommand == "info":
            if len(args) < 2:
                print("[bold red]Hata:[/bold red] Plugin adı belirtilmedi.")
                return False
            self._show_info(args[1])
            return True
        
        elif subcommand == "search":
            search_term = " ".join(args[1:]) if len(args) > 1 else None
            self._search_plugins(search_term)
            return True
            
        elif subcommand == "install":
            if len(args) < 2:
                print("[bold red]Hata:[/bold red] Kullanım: plugins install <depo>/<eklenti_yolu>")
                return False
            force = "--force" in args
            return shared_state.plugin_downloader.install_plugin(args[1], force=force) if shared_state.plugin_downloader else False
            
        elif subcommand == "update":
            if not shared_state.plugin_downloader:
                print("[bold red]Hata:[/bold red] Eklenti Yöneticisi başlatılamamış.")
                return False
            if len(args) > 1:
                return shared_state.plugin_downloader.update_plugin(args[1])
            else:
                self._check_updates()
                return True
                
        elif subcommand == "remove":
            if len(args) < 2:
                print("[bold red]Hata:[/bold red] Lütfen silinecek plugin adını belirtin.")
                return False
            return shared_state.plugin_downloader.remove_plugin(args[1]) if shared_state.plugin_downloader else False
            
        else:
            print(f"[bold red]Hata:[/bold red] Bilinmeyen alt komut: {subcommand}")
            return False

    def _list_plugins(self) -> None:
        """Tüm plugin'leri listeler (Metasploit tarzı)."""
        if not shared_state.plugin_manager:
            return

        plugins = shared_state.plugin_manager.get_all_plugins()
        if not plugins:
            print("Yüklü plugin bulunamadı.")
            return

        print("\nPlugins")
        print("-------")
        print()
        # Başlık satırları (veri satırlarıyla aynı genişlikte)
        print(f"   {'İsim':<24} {'Versiyon':<10} {'Durum':<8} Açıklama")
        print(f"   {'----':<24} {'--------':<10} {'-----':<8} --------")
        
        for name, plugin in plugins.items():
            # Durum metnini ayrı hesapla (hizalama için)
            status_color = "[green]Aktif[/green]" if plugin.Enabled else "[red]Pasif[/red]"
            
            # Sabit genişliklerle hizalama (Rich markup olmadan hesapla)
            name_padded = plugin.Name.ljust(24)
            version_padded = plugin.Version.ljust(10)
            status_padded = "Aktif".ljust(8) if plugin.Enabled else "Pasif".ljust(8)
            
            # Rich renklendirme için status_color kullan ama hizalama için padded değer
            if plugin.Enabled:
                print(f"   {name_padded} {version_padded} [green]{status_padded}[/green] {plugin.Description}")
            else:
                print(f"   {name_padded} {version_padded} [red]{status_padded}[/red] {plugin.Description}")
        
        print()

    def _enable_plugin(self, plugin_name: str) -> None:
        """Plugin'i etkinleştirir."""
        if not shared_state.plugin_manager:
            return
            
        # İsim eşleşmesi için (case-insensitive olabilir)
        target_plugin = None
        for name in shared_state.plugin_manager.get_all_plugins():
            if name.lower() == plugin_name.lower():
                target_plugin = name
                break
        
        if not target_plugin:
            print(f"[bold red]Hata:[/bold red] Plugin bulunamadı: {plugin_name}")
            return

        if shared_state.plugin_manager.enable_plugin(target_plugin):
            print(f"[bold green]Başarılı:[/bold green] '{target_plugin}' etkinleştirildi.")
        else:
            print(f"[bold red]Hata:[/bold red] '{target_plugin}' etkinleştirilemedi.")

    def _disable_plugin(self, plugin_name: str) -> None:
        """Plugin'i devre dışı bırakır."""
        if not shared_state.plugin_manager:
            return

        # İsim eşleşmesi
        target_plugin = None
        for name in shared_state.plugin_manager.get_all_plugins():
            if name.lower() == plugin_name.lower():
                target_plugin = name
                break
        
        if not target_plugin:
            print(f"[bold red]Hata:[/bold red] Plugin bulunamadı: {plugin_name}")
            return

        if shared_state.plugin_manager.disable_plugin(target_plugin):
            print(f"[bold green]Başarılı:[/bold green] '{target_plugin}' devre dışı bırakıldı.")
        else:
            print(f"[bold red]Hata:[/bold red] '{target_plugin}' devre dışı bırakılamadı.")

    def _show_info(self, plugin_name: str) -> None:
        """Plugin detaylarını gösterir."""
        if not shared_state.plugin_manager:
            return

        # İsim eşleşmesi
        target_name = None
        for name in shared_state.plugin_manager.get_all_plugins():
            if name.lower() == plugin_name.lower():
                target_name = name
                break
        
        if target_name:
            plugin = shared_state.plugin_manager.get_plugin(target_name)
        else:
            plugin = None

        if not plugin:
            print(f"[bold red]Hata:[/bold red] Plugin bulunamadı: {plugin_name}")
            return

        print(f"\n[bold cyan]Plugin Detayları: {plugin.Name}[/bold cyan]")
        print("-" * 50)
        print(f"[bold]Açıklama:[/bold] {plugin.Description}")
        print(f"[bold]Yazar:[/bold]    {plugin.Author}")
        print(f"[bold]Versiyon:[/bold] {plugin.Version}")
        status = "[green]Aktif[/green]" if plugin.Enabled else "[red]Pasif[/red]"
        print(f"[bold]Durum:[/bold]    {status}")
        print(f"[bold]Öncelik:[/bold]  {plugin.Priority}")
        
        hooks = plugin.get_hooks()
        if hooks:
            print("\n[bold]Kayıtlı Hook'lar:[/bold]")
            for hook in hooks:
                print(f"  - {hook.value}")
        else:
            print("\n[dim]Hook kaydı yok.[/dim]")
        
        print("-" * 50)

    def _search_plugins(self, search_term=None) -> None:
        """Uzak depolardaki eklentileri arar."""
        if not shared_state.plugin_downloader:
            return

        if search_term:
            print(f"\n[bold cyan]🔍 Aranıyor:[/bold cyan] '{search_term}'\n")
        else:
            print("\n[bold cyan]📦 Tüm depo eklentileri taranıyor...[/bold cyan]\n")

        plugins = shared_state.plugin_downloader.scan_repos(search_term)

        if not plugins:
            print("[dim]Eşleşen eklenti bulunamadı.[/dim]")
            return

        by_repo = {}
        for mod in plugins:
            repo = mod["repo"]
            if repo not in by_repo:
                by_repo[repo] = []
            by_repo[repo].append(mod)

        total = 0
        for repo_name, repo_plugins in by_repo.items():
            print(f"[bold green]📁 {repo_name}[/bold green]")
            print(f"   {'Eklenti':<35} {'Versiyon':<10} {'Yazar':<15} {'İmza':<6} Açıklama")
            print(f"   {'-------':<35} {'-------':<10} {'-----':<15} {'----':<6} --------")

            for mod in repo_plugins:
                name_path = f"{repo_name}/{mod['relative_path']}"
                if len(name_path) > 34:
                    name_path = "..." + name_path[-31:]

                sig = "[green]✓[/green]" if mod["has_signature"] else "[dim]—[/dim]"
                desc = mod["description"][:40] if mod["description"] else "—"

                print(f"   {name_path:<35} {mod['version']:<10} {mod['author']:<15} {sig:<6} {desc}")
                total += 1

            print()

        print(f"   Toplam: {total} eklenti bulundu\n")

    def _check_updates(self) -> None:
        """Kurulu eklentilerin güncellemelerini kontrol eder."""
        if not shared_state.plugin_downloader:
            return

        print("\n[bold cyan]🔄 Güncelleme kontrolü yapılıyor...[/bold cyan]\n")
        updates = shared_state.plugin_downloader.check_updates()

        if not updates:
            print("[bold green]✓[/bold green] Tüm eklentiler güncel.\n")
            return

        print(f"[bold yellow]⚠ {len(updates)} eklenti için güncelleme mevcut:[/bold yellow]\n")
        print(f"   {'Eklenti':<35} {'Kurulu':<10} {'Mevcut':<10} Kaynak")
        print(f"   {'-------':<35} {'------':<10} {'------':<10} ------")

        for upd in updates:
            mod_display = upd["plugin"]
            if len(mod_display) > 34:
                mod_display = "..." + mod_display[-31:]

            print(f"   {mod_display:<35} {upd['installed_version']:<10} [green]{upd['available_version']}[/green]{'':<4} {upd['repo']}")

        print(f"\n   Güncellemek için: [bold]plugins update <eklenti_yolu>[/bold]\n")

    def get_completions(self, text: str, word_before_cursor: str) -> List[str]:
        """Otomatik tamamlama."""
        parts = text.split()
        
        # parts[0] = "plugins" (komut adı)
        # parts[1] = alt komut (list, enable, disable, info, vb.)
        
        if len(parts) == 1 or (len(parts) == 2 and not text.endswith(' ')):
            subcommands = ["list", "enable", "disable", "info", "search", "install", "update", "remove"]
            if len(parts) == 2:
                # Yazılan kısma göre filtrele
                return [s for s in subcommands if s.startswith(parts[1].lower())]
            return subcommands
        
            
        # Alt komut sonrası isim tamamlama
        if len(parts) >= 2:
            subcommand = parts[1].lower()
            if subcommand in ["enable", "disable", "info", "remove", "update"]:
                if not shared_state.plugin_manager:
                    return []
                plugin_names = list(shared_state.plugin_manager.get_all_plugins().keys())
                
                # Update ve remove için yüklü dosya listesinden de ekle (eğer yüklenemeyen varsa)
                if subcommand in ["remove", "update"] and shared_state.plugin_downloader:
                    dl_names = shared_state.plugin_downloader.get_installed_plugin_keys()
                    plugin_names = list(set(plugin_names + dl_names))
                    
                if len(parts) == 3 and not text.endswith(' '):
                    return [p for p in plugin_names if p.lower().startswith(parts[2].lower())]
                return plugin_names
            
        return []
