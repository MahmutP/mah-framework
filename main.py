import shutil 
import random
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
    from rich.panel import Panel
    from rich.text import Text
    
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
    
    # Kategori sayılarını hesapla
    exploit_count = 0
    auxiliary_count = 0
    payload_count = 0
    scanner_count = 0
    other_count = 0
    total_modules = 0
    
    for category, modules in categorized_modules.items():
        count = len(modules)
        total_modules += count
        cat_lower = category.lower()
        
        if "exploit" in cat_lower:
            exploit_count += count
        elif "auxiliary" in cat_lower or "scanner" in cat_lower:
            auxiliary_count += count
            if "scanner" in cat_lower:
                scanner_count += count
        elif "payload" in cat_lower:
            payload_count += count
        else:
            other_count += count
    
    # Metasploit tarzı çıktı
    version_line = "[bold cyan]       =[ Mah Framework v1.0-dev ][/bold cyan]"
    
    # Satır 1: exploits ve auxiliary
    line1_parts = []
    if exploit_count > 0:
        line1_parts.append(f"[green]{exploit_count}[/green] exploit{'s' if exploit_count != 1 else ''}")
    if auxiliary_count > 0:
        line1_parts.append(f"[green]{auxiliary_count}[/green] auxiliary")
    if total_modules > 0:
        line1_parts.append(f"[green]{total_modules}[/green] modules")
    
    # Satır 2: payloads ve commands
    line2_parts = []
    if payload_count > 0:
        line2_parts.append(f"[yellow]{payload_count}[/yellow] payloads")
    line2_parts.append(f"[yellow]{total_commands}[/yellow] commands")
    
    # Satır 3: scanners (varsa)
    line3_parts = []
    if scanner_count > 0:
        line3_parts.append(f"[magenta]{scanner_count}[/magenta] scanner{'s' if scanner_count != 1 else ''}")
    
    # Yazdır
    console.print()
    console.print(version_line)
    
    if line1_parts:
        console.print(f"[dim]+ -- --=[[/dim] {' - '.join(line1_parts)} [dim]]=--[/dim]")
    if line2_parts:
        console.print(f"[dim]+ -- --=[[/dim] {' - '.join(line2_parts)} [dim]]=--[/dim]")
    if line3_parts:
        console.print(f"[dim]+ -- --=[[/dim] {' - '.join(line3_parts)} [dim]]=--[/dim]")
    
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