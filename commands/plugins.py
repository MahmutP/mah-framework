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
    Usage = "plugins [list|enable|disable|info] [plugin_adı]"
    completer_function = True  # Otomatik tamamlama aktif
    Examples = [
        "plugins list",
        "plugins info 'Audit Logger'",
        "plugins enable 'Audit Logger'",
        "plugins disable 'Audit Logger'"
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

    def get_completions(self, text: str, word_before_cursor: str) -> List[str]:
        """Otomatik tamamlama."""
        parts = text.split()
        
        # parts[0] = "plugins" (komut adı)
        # parts[1] = alt komut (list, enable, disable, info)
        # parts[2] = plugin adı
        
        # Sadece "plugins" yazıldıysa veya alt komut tamamlanıyorsa
        if len(parts) == 1 or (len(parts) == 2 and not text.endswith(' ')):
            subcommands = ["list", "enable", "disable", "info"]
            if len(parts) == 2:
                # Yazılan kısma göre filtrele
                return [s for s in subcommands if s.startswith(parts[1].lower())]
            return subcommands
        
        # "plugins enable " veya "plugins disable " sonrası plugin adı tamamlanacak
        if len(parts) >= 2:
            subcommand = parts[1].lower()
            if subcommand in ["enable", "disable", "info"]:
                if not shared_state.plugin_manager:
                    return []
                plugin_names = list(shared_state.plugin_manager.get_all_plugins().keys())
                # Eğer kısmi isim yazılmışsa filtrele
                if len(parts) == 3 and not text.endswith(' '):
                    return [p for p in plugin_names if p.lower().startswith(parts[2].lower())]
                return plugin_names
            
        return []
