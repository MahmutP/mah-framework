import shutil 
import random
from pathlib import Path
from core.shared_state import shared_state
from core.command_manager import CommandManager
from core.module_manager import ModuleManager
from core.console import Console as AppConsole
from core.cont import DEFAULT_TERMINAL_WIDTH, LEFT_PADDING, COL_SPACING
from core import logger
from core.banner import print_banner

def print_startup_info(command_manager: CommandManager, module_manager: ModuleManager):
    """Startup bilgisi basmaya yarıyan fonksiyon (Metasploit tarzı).

    Args:
        command_manager (CommandManager): Komut yöneticisi
        module_manager (ModuleManager): Modül yöneticisi.
    """
    from rich.console import Console
    
    console = Console()
    
    # Banner'ı bas
    try:
        print_banner()
    except Exception as e:
        print(f"Banner basılırken hata oluştu: {e}")
        print("Mah Framework") 
    
    # İstatistikleri topla
    total_commands = len(command_manager.get_all_commands())
    categorized_modules = module_manager.get_modules_by_category()
    
    # Tüm kategorileri ve sayılarını dinamik olarak al
    category_counts = {}
    total_modules = 0
    
    for category, modules in categorized_modules.items():
        count = len(modules)
        total_modules += count
        # Kategori adını düzelt (ilk harfi büyük)
        display_name = category.replace("/", " / ").title() if "/" in category else category.capitalize()
        category_counts[display_name] = count
    
    # Metasploit tarzı çıktı
    # Git commit sayısından otomatik versiyon hesapla
    import subprocess
    try:
        commit_count = int(subprocess.check_output(
            ["git", "rev-list", "--count", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=str(Path(__file__).parent)
        ).decode().strip())
        
        # Versiyon hesaplama: commit sayısına göre major.minor.patch
        # Örnek: 134 commits → v1.3.4
        major = commit_count // 100
        minor = (commit_count % 100) // 10
        patch = commit_count % 10
        version = f"v{major}.{minor}.{patch}"
        
        version_line = f"[bold cyan]       =[ Mah Framework {version} ][/bold cyan]"
        
        # Eski format (commits gösterimi):
        # version_line = f"[bold cyan]       =[ Mah Framework - {commit_count} commits ][/bold cyan]"
        
    except Exception:
        version_line = "[bold cyan]       =[ Mah Framework ][/bold cyan]"
    
    # Satır 1: Toplam modül sayısı
    line1 = f"[green]{total_modules}[/green] modules - [yellow]{total_commands}[/yellow] commands"
    
    # Satır 2+: Her kategori dinamik olarak
    category_parts = []
    colors = ["green", "yellow", "magenta", "cyan", "blue", "red"]
    
    for idx, (cat_name, count) in enumerate(sorted(category_counts.items())):
        color = colors[idx % len(colors)]
        category_parts.append(f"[{color}]{count}[/{color}] {cat_name.lower()}")
    
    # Yazdır
    console.print()
    console.print(version_line)
    console.print(f"[dim]+ -- --=[[/dim] {line1} [dim]]=--[/dim]")
    
    # Kategorileri 3'erli grupla (satır başına max 3 kategori)
    for i in range(0, len(category_parts), 3):
        chunk = category_parts[i:i+3]
        console.print(f"[dim]+ -- --=[[/dim] {' - '.join(chunk)} [dim]]=--[/dim]")
    
    console.print()
    console.print("    Yardım için [bold]'help'[/bold] yazın")

def main():
    """Main fonksiyon, objeler tanımlanıyor ve sistem başlatılıyor.
    """
    # Logger'ı başlat
    logger.setup_logger()
    logger.info("Uygulama başlatılıyor...")
    
    print("Uygulama başlatılıyor...")
    command_manager = CommandManager()
    module_manager = ModuleManager()
    shared_state.command_manager = command_manager
    shared_state.module_manager = module_manager
    command_manager.load_commands()
    module_manager.load_modules()
    console = AppConsole(command_manager, module_manager)
    shared_state.console_instance = console
    print_startup_info(command_manager, module_manager)
    logger.info("Uygulama başlatıldı")
    try:
        console.start()
    except Exception as e:
        print(f"Ana konsol döngüsünde kritik hata: {e}")
        logger.critical(f"Ana konsol döngüsünde kritik hata: {e}")
    finally:
        console.shutdown()
if __name__ == "__main__":
    main()