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
        # Kategori adını düzelt - alt kategorileri birleştir (auxiliary/scanner → auxiliary)
        top_level_category = category.split("/")[0] if "/" in category else category
        display_name = top_level_category.capitalize()
        
        # Aynı üst kategorideki modülleri birleştir
        if display_name in category_counts:
            category_counts[display_name] += count
        else:
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
    
    # 7 günde bir güncelleme hatırlatıcısı
    _show_update_reminder(console)


def _show_update_reminder(console):
    """7 günde bir güncelleme hatırlatıcısı gösterir.
    
    Son hatırlatma tarihini config/last_update_reminder.txt dosyasında saklar.
    7 gün geçtiyse kullanıcıya checkupdate komutunu hatırlatır.
    """
    import json
    from datetime import datetime, timedelta
    
    reminder_file = Path(__file__).parent / "config" / "last_update_reminder.txt"
    reminder_days = 7  # Kaç günde bir hatırlat
    
    try:
        should_remind = False
        
        if reminder_file.exists():
            last_reminder = datetime.fromisoformat(reminder_file.read_text().strip())
            if datetime.now() - last_reminder > timedelta(days=reminder_days):
                should_remind = True
        else:
            should_remind = True
        
        if should_remind:
            console.print()
            console.print("[dim]💡 Tip: Güncellemeleri kontrol etmek için [bold]'checkupdate'[/bold] yazın[/dim]")
            
            # Tarihi güncelle
            reminder_file.parent.mkdir(parents=True, exist_ok=True)
            reminder_file.write_text(datetime.now().isoformat())
            
    except Exception:
        pass  # Hata olursa sessizce geç

def main():
    """Main fonksiyon, objeler tanımlanıyor ve sistem başlatılıyor.
    """
    import argparse
    
    # Argüman ayrıştırıcı
    parser = argparse.ArgumentParser(description="Mah Framework - Modüler Güvenlik Aracı")
    parser.add_argument("-q", "--quiet", action="store_true", 
                        help="Sessiz mod - banner ve başlangıç bilgisi gösterilmez")
    parser.add_argument("-r", "--resource", type=str, metavar="DOSYA",
                        help="Başlangıçta çalıştırılacak resource (.rc) dosyası")
    parser.add_argument("-x", "--execute", type=str, metavar="KOMUTLAR",
                        help="Başlangıçta çalıştırılacak komutlar (noktalı virgül ile ayır)")
    args = parser.parse_args()
    
    # Logger'ı başlat
    logger.setup_logger()
    logger.info("Uygulama başlatılıyor...")
    
    if not args.quiet:
        print("Uygulama başlatılıyor...")
    
    command_manager = CommandManager()
    module_manager = ModuleManager()
    shared_state.command_manager = command_manager
    shared_state.module_manager = module_manager
    command_manager.load_commands()
    module_manager.load_modules()
    console = AppConsole(command_manager, module_manager)
    shared_state.console_instance = console
    
    # Sessiz mod değilse banner ve bilgi göster
    if not args.quiet:
        print_startup_info(command_manager, module_manager)
    
    # Resource dosyası belirtildiyse çalıştır
    if args.resource:
        from pathlib import Path
        resource_path = Path(args.resource)
        if resource_path.exists():
            # Resource komutunu al ve çalıştır
            resource_cmd = command_manager.get_all_commands().get("resource")
            if resource_cmd:
                resource_cmd.run_resource_file(resource_path)
            else:
                print(f"[bold red]Hata:[/bold red] resource komutu bulunamadı")
        else:
            print(f"[bold red]Hata:[/bold red] Resource dosyası bulunamadı: {args.resource}")
    
    # -x ile komut belirtildiyse çalıştır
    if args.execute:
        print(f"\n[bold cyan]⚡ Komutlar çalıştırılıyor...[/bold cyan]\n")
        commands = args.execute.split(";")
        for cmd_line in commands:
            cmd_line = cmd_line.strip()
            if not cmd_line:
                continue
            
            print(f"[bold yellow]>[/bold yellow] {cmd_line}")
            
            parts = cmd_line.split()
            if not parts:
                continue
            
            command_name = parts[0].lower()
            command_args = parts[1:] if len(parts) > 1 else []
            
            # Komutu çöz (alias kontrolü dahil)
            resolved_name, _ = command_manager.resolve_command(command_name)
            
            if not resolved_name:
                print(f"[bold red]  ✗ Bilinmeyen komut: {command_name}[/bold red]")
                continue
            
            # Komutu al ve çalıştır
            cmd_obj = command_manager.get_all_commands().get(resolved_name)
            if cmd_obj:
                try:
                    cmd_obj.execute(*command_args)
                except Exception as e:
                    print(f"[bold red]  ✗ Hata: {e}[/bold red]")
            else:
                print(f"[bold red]  ✗ Komut objesi bulunamadı: {resolved_name}[/bold red]")
        
        print()
    
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