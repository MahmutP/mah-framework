import socket
from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print

class service_version_detector(BaseModule):
    """
    Port üzerindeki servisin versiyonunu tespit etme (banner grabbing) modülü.
    """
    Name = "Service Version Detector"
    Description = "TCP portlarına bağlanarak dönen banner bilgisini okur ve servis versiyonunu tespit etmeye çalışır."
    Author = "Mahmut P."
    Category = "auxiliary/scanner"
    Version = "1.0"

    Requirements = {"python": []}

    def __init__(self):
        super().__init__()
        self.Options = {
            "RHOST": Option("RHOST", "127.0.0.1", True, "Hedef IP adresi"),
            "RPORT": Option("RPORT", 22, True, "Hedef Port"),
            "TIMEOUT": Option("TIMEOUT", 3, False, "Bağlantı zaman aşımı (saniye)"),
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    def run(self, options: Dict[str, Any]):
        rhost = options.get("RHOST")
        rport = int(options.get("RPORT", 22))
        timeout = float(options.get("TIMEOUT", 3))

        print(f"[bold cyan][*] {rhost}:{rport} portunda servis dinleniyor...[/bold cyan]")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((rhost, rport))
                
                # Olası HTTP servisleri için payload yollama (Bazen banner direkt gelmez)
                if rport in [80, 8080, 443]:
                    s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")

                banner = s.recv(1024).decode("utf-8", errors="ignore").strip()

                if banner:
                    print(f"\n[bold green][+] Banner Bulundu ({rhost}:{rport}):[/bold green]")
                    print(f"[green]{banner}[/green]")
                    return True
                else:
                    print(f"[yellow][!] Cihaz bağlandı fakat banner dönmedi.[/yellow]")
                    return True

        except socket.timeout:
            print(f"[bold red][-] {rhost}:{rport} - Bağlantı zaman aşımına uğradı.[/bold red]")
            return False
        except ConnectionRefusedError:
            print(f"[bold red][-] {rhost}:{rport} - Bağlantı reddedildi (Port kapalı olabilir).[/bold red]")
            return False
        except Exception as e:
            print(f"[bold red][-] Beklenmeyen Hata: {str(e)}[/bold red]")
            return False
