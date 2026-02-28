from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print
from smb.SMBConnection import SMBConnection
import socket

class smb_enum(BaseModule):
    """
    SMB Paylaşım keşif ve deneme modülü.
    """
    Name = "SMB Enumeration"
    Description = "Hedef sistemdeki SMB paylaşımlarını bulur ve anonymous giriş denemesi yapar."
    Author = "Mahmut P."
    Category = "auxiliary/scanner"
    Version = "1.0"

    Requirements = {"python": ["pysmb"]}

    def __init__(self):
        super().__init__()
        self.Options = {
            "RHOST": Option("RHOST", "127.0.0.1", True, "Hedef IP adresi"),
            "RPORT": Option("RPORT", 445, True, "Hedef Port (Genelde 445 veya 139)"),
            "TIMEOUT": Option("TIMEOUT", 5, False, "Bağlantı zaman aşımı (saniye)"),
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    def run(self, options: Dict[str, Any]):
        rhost = options.get("RHOST")
        rport = int(options.get("RPORT", 445))
        timeout = float(options.get("TIMEOUT", 5))

        print(f"[bold cyan][*] {rhost}:{rport} SMB Paylaşımları aranıyor...[/bold cyan]")

        try:
            # Önce portun açık olup olmadığını hızlıca kontrol edelim
            with socket.create_connection((rhost, rport), timeout=timeout):
                pass
        except OSError:
            print(f"[bold red][-] {rhost}:{rport} - Bağlantı reddedildi veya zaman aşımına uğradı. Port kapalı olabilir.[/bold red]")
            return False

        try:
            # pysmb kullanarak list shares
            conn = SMBConnection("", "", "mah-framework", "remote-host", use_ntlm_v2=True)
            connected = conn.connect(rhost, rport, timeout=timeout)
            
            if not connected:
                print(f"[bold red][-] SMB servisine bağlanılamadı.[/bold red]")
                return False

            shares = conn.listShares(timeout=timeout)
            
            print(f"\n[bold green][+] Anonymous erişim başarılı. Paylaşımlar listesi ({rhost}):[/bold green]")
            for share in shares:
                print(f"  [green]- {share.name}[/green] ({share.comments})")
                
            conn.close()
            return True

        except Exception as e:
            # Hata kodu e.clsException = SessionError ise authentication failed demektir.
            if "SessionError" in str(type(e)) or "SessionError" in str(e):
                print(f"[yellow][!] Cihazda SMB açık ancak Anonymous (Guest) erişime izin verilmiyor.[/yellow]")
                return True
            print(f"[bold red][-] SMB Bağlantı Hatası: {e}[/bold red]")
            return False
