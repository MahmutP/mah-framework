import re
import requests
from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print
from rich.table import Table

class email_harvester(BaseModule):
    """
    Hedef websitesinden e-posta adreslerini toplayan keşif modülü.
    """
    Name = "Email Harvester"
    Description = "Harvest email addresses from a given target domain's homepage."
    Author = "Mahmut P."
    Category = "auxiliary/recon"
    Version = "1.0"

    Requirements = {"python": ["requests"]}

    def __init__(self):
        super().__init__()
        self.Options = {
            "DOMAIN": Option("DOMAIN", "", True, "Sorgulanacak hedef domain (örn: example.com)"),
            "TIMEOUT": Option("TIMEOUT", 10, False, "HTTP istek zaman aşımı (saniye)"),
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    def run(self, options: Dict[str, Any]):
        domain = options.get("DOMAIN")
        timeout = int(options.get("TIMEOUT", 10))
        
        if not domain:
            print("[bold red][-] Lütfen sorgulanacak bir DOMAIN giriniz.[/bold red]")
            return False

        # Add scheme if missing
        url = domain
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{domain}"

        print(f"[bold cyan][*] '{url}' üzerinden e-posta taraması yapılıyor...[/bold cyan]")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            
            # Use regex to find email addresses
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = set(re.findall(email_pattern, response.text))

            if not emails:
                print(f"[yellow][!] '{url}' üzerinde e-posta adresi bulunamadı.[/yellow]")
                return True

            table = Table(title=f"Extracted Emails for {domain}", show_header=True, header_style="bold magenta")
            table.add_column("Email Address", justify="left", style="green")

            for email in sorted(emails):
                table.add_row(email)

            print()
            print(table)
            print(f"[green][+] Toplam {len(emails)} e-posta adresi bulundu.[/green]")
            return True

        except requests.exceptions.Timeout:
            print(f"[bold red][-] Hedefe bağlanılamadı (Zaman aşımı).[/bold red]")
            return False
        except requests.exceptions.ConnectionError:
            print(f"[bold red][-] Bağlantı hatası: Sunucu bulunamadı veya bağlantı koptu.[/bold red]")
            return False
        except Exception as e:
            print(f"[bold red][-] Beklenmeyen bir hata oluştu: {str(e)}[/bold red]")
            return False
