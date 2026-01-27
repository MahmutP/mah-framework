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
    """Startup bilgisi basmaya yarıyan fonksiyon.

    Args:
        command_manager (CommandManager): Komut yöneticisi
        module_manager (ModuleManager): Modül yöneticisi.
    """
    try:
        print_banner()
    except Exception as e:
        print(f"Banner basılırken hata oluştu: {e}")
        print("CLI Framework") 
    total_commands = len(command_manager.get_all_commands())
    categorized_modules = module_manager.get_modules_by_category()
    module_categories_info = []
    for category, modules in categorized_modules.items():
        module_categories_info.append((category, len(modules)))
    try:
        terminal_width = shutil.get_terminal_size().columns
    except OSError:
        terminal_width = DEFAULT_TERMINAL_WIDTH
        print(f"Terminal genişliği alınamadı, varsayılan {DEFAULT_TERMINAL_WIDTH} kullanılıyor.")
    max_line_content_len = len(f"-=[Komutlar: {total_commands}]=-")
    for cat_name, count in module_categories_info:
        current_line_content = f"-=[{cat_name}: {count}]=-"
        if len(current_line_content) > max_line_content_len:
            max_line_content_len = len(current_line_content)
    cmd_line_content = f"-=[Komutlar: {total_commands}]=-"
    print(f"{' ' * LEFT_PADDING}{cmd_line_content.ljust(max_line_content_len)}")
    for category, count in sorted(module_categories_info):
        line_content = f"-=[{category}: {count}]=-"
        print(f"{' ' * LEFT_PADDING}{line_content.ljust(max_line_content_len)}")
    print(f"\n{' ' * LEFT_PADDING}Yardım için 'help' yazın")

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