from typing import Any, List
import os
from core.command import Command
from rich import print
from prompt_toolkit.history import FileHistory

class History(Command):
    """Geçmiş komutları listeleme komutu."""
    
    Name = "history"
    Description = "Kullanılan komutların geçmişini listeler."
    Category = "system"
    Aliases = ["hist"]
    Usage = "history [limit]"
    Examples = [
        "history          # Tüm geçmişi gösterir",
        "history 20       # Son 20 komutu gösterir"
    ]
    
    def execute(self, *args: str, **kwargs: Any) -> bool:
        # Framework root dizinini bul (commands klasörünün bir üstü)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        history_file = os.path.join(base_dir, ".mah_history")
        
        if not os.path.exists(history_file):
            print("[bold yellow]Henüz hiç komut geçmişi yok.[/bold yellow]")
            return True
            
        try:
            # FileHistory formatını parse et (+ ile başlayan satırlar komuttur)
            commands = []
            with open(history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('+'):
                        commands.append(line[1:]) # '+' işaretini kaldır
            
            if not commands:
                print("[bold yellow]Henüz hiç komut geçmişi yok.[/bold yellow]")
                return True
            
            limit = len(commands)
            if args:
                try:
                    limit = int(args[0])
                except ValueError:
                    print(f"[bold red]Hata:[/bold red] Geçersiz limit değeri: {args[0]}")
                    return False
            
            # İstenen sayıda son komutu al
            start_index = max(0, len(commands) - limit)
            commands_to_show = commands[start_index:]
            
            print(f"[bold cyan]Komut Geçmişi ({len(commands_to_show)}/{len(commands)}):[/bold cyan]")
            for i, cmd in enumerate(commands_to_show, start=start_index + 1):
                # 4 haneli hizalama ile yazdır (1.  komut)
                print(f"[green]{i:<4}[/green] {cmd}")
                
            return True
            
        except Exception as e:
            print(f"[bold red]Hata:[/bold red] Geçmiş okunamadı: {e}")
            return False
