from typing import Any, List
from core.command import Command
from core.shared_state import shared_state
from rich import print

class Record(Command):
    """Makro kayıt komutu.
    
    Kullanıcı komutlarını bir listeye kaydeder ve dosyaya yazar.
    """
    Name = "record"
    Description = "Kullanıcı komutlarını kaydeder ve dosyaya yazar (.rc formatında)."
    Category = "system"
    Aliases = ["makro"]
    Usage = "record <start|stop|status> [dosya_yolu]"
    Examples = [
        "record start             # Kaydı başlatır",
        "record stop my_script.rc # Kaydı durdurur ve dosyaya kaydeder",
        "record stop              # Kaydı durdurur ve ekrana basar",
        "record status            # Kayıt durumunu gösterir"
    ]
    
    def __init__(self):
        super().__init__()
        self.completer_function = self._record_completer

    def _record_completer(self, text: str, word_before_cursor: str) -> List[str]:
        """Record komutu otomatik tamamlaması."""
        parts = text.split()
        
        # Eğer 'record ' yazılmışsa (veya 'record s' gibi)
        if len(parts) == 1 and text.endswith(' '):
            return ["start", "stop", "status"]
            
        if len(parts) == 2 and not text.endswith(' '):
            options = ["start", "stop", "status"]
            current_input = parts[1]
            return [opt for opt in options if opt.startswith(current_input)]
            
        return []
    
    def execute(self, *args: str, **kwargs: Any) -> bool:
        if not args:
            print("[bold red]Hata:[/bold red] Alt komut gerekli (start, stop, status).")
            print(f"Kullanım: {self.Usage}")
            return False
            
        subcommand = args[0].lower()
        
        if subcommand == "start":
            if shared_state.is_recording:
                print("[bold yellow]Uyarı:[/bold yellow] Zaten kayıt yapılıyor.")
                return False
            
            shared_state.is_recording = True
            shared_state.recorded_commands = []
            print("[bold green]✔ Makro kaydı başlatıldı.[/bold green]")
            print("Çalıştırdığınız komutlar kaydedilecek. Durdurmak için [bold cyan]record stop <dosya>[/bold cyan] kullanın.")
            return True
            
        elif subcommand == "stop":
            if not shared_state.is_recording:
                print("[bold yellow]Uyarı:[/bold yellow] Kayıt zaten durdurulmuş.")
                return False
            
            shared_state.is_recording = False
            commands = shared_state.recorded_commands
            
            # Dosya adı verilmişse kaydet
            if len(args) > 1:
                filename = args[1]
                
                # Dosya uzantısı kontrolü (opsiyonel)
                if not filename.endswith('.rc'):
                    filename += '.rc'
                    
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        for cmd in commands:
                            f.write(f"{cmd}\n")
                    
                    print(f"[bold green]✔ Kayıt durduruldu ve '{filename}' dosyasına yazıldı.[/bold green]")
                    print(f"Toplam {len(commands)} komut kaydedildi.")
                except Exception as e:
                    print(f"[bold red]Hata:[/bold red] Dosya yazılamadı: {e}")
                    return False
            else:
                print("[bold yellow]⚠ Kayıt durduruldu.[/bold yellow] (Dosya adı belirtilmedi)")
                if commands:
                    print(f"[bold cyan]Kaydedilen Komutlar ({len(commands)}):[/bold cyan]")
                    for cmd in commands:
                         print(f"  {cmd}")
                else:
                    print("Hiçbir komut kaydedilmedi.")
            
            # Temizle
            shared_state.recorded_commands = []
            return True
            
        elif subcommand == "status":
            if shared_state.is_recording:
                print(f"[bold green]● Kayıt DEVAM EDİYOR.[/bold green]")
                print(f"Şu ana kadar kaydedilen komut sayısı: {len(shared_state.recorded_commands)}")
            else:
                print("[dim]Kaydedilen komut yok (durmuş).[/dim]")
            return True
            
        else:
            print(f"[bold red]Hata:[/bold red] Bilinmeyen alt komut: {subcommand}")
            return False
