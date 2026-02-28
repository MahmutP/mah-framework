import subprocess
from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print

class whois_lookup(BaseModule):
    """
    Domain veya IP adresi için WHOIS sorgusu yapan keşif modülü.
    """
    Name = "WHOIS Lookup"
    Description = "Perform a WHOIS lookup for a given domain or IP address."
    Author = "Mahmut P."
    Category = "recon"
    Version = "1.0"
    
    # 'whois' komutuna ihtiyaç duyar.
    Requirements = {"system": ["whois"]}

    def __init__(self):
        super().__init__()
        self.Options = {
            "DOMAIN": Option("DOMAIN", "", True, "Sorgulanacak hedef domain veya IP (örn: example.com)"),
        }
        # Varsayılan değerleri class attribute olarak ayarla (BaseModule yapısı gereği)
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    def run(self, options: Dict[str, Any]):
        domain = options.get("DOMAIN")
        if not domain:
            print("[bold red][-] Lütfen sorgulanacak bir DOMAIN giriniz.[/bold red]")
            return False

        print(f"[bold cyan][*] '{domain}' için WHOIS sorgusu yapılıyor...[/bold cyan]")

        try:
            # whois komutunu çalıştır
            result = subprocess.run(
                ["whois", domain],
                capture_output=True,
                text=True,
                check=False # Hata döndürse bile capture_output aldığımız için biz işleyeceğiz
            )

            if result.returncode == 0:
                print("\n[bold green][+] WHOIS Sorgu Sonucu:[/bold green]")
                print(result.stdout)
                return True
            else:
                print(f"[bold red][-] WHOIS sorgusu başarısız oldu (Return Code: {result.returncode}).[/bold red]")
                print(result.stderr)
                return False

        except FileNotFoundError:
            print("[bold red][-] 'whois' komutu sistemde bulunamadı. Lütfen kurunuz.[/bold red]")
            return False
        except Exception as e:
            print(f"[bold red][-] Beklenmeyen bir hata oluştu: {str(e)}[/bold red]")
            return False
