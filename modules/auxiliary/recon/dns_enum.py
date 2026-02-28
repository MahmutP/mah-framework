import dns.resolver
from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print
from rich.table import Table

class dns_enum(BaseModule):
    """
    Domain DNS kayıtlarını analiz eden keşif modülü.
    """
    Name = "DNS Enum"
    Description = "Perform DNS enumeration (A, MX, NS, TXT, CNAME) for a given domain."
    Author = "Mahmut P."
    Category = "auxiliary/recon"
    Version = "1.0"

    # 'dnspython' kütüphanesine ihtiyaç duyar
    Requirements = {"python": ["dnspython"]}

    def __init__(self):
        super().__init__()
        self.Options = {
            "DOMAIN": Option("DOMAIN", "", True, "Sorgulanacak hedef domain (örn: example.com)"),
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    def run(self, options: Dict[str, Any]):
        domain = options.get("DOMAIN")
        if not domain:
            print("[bold red][-] Lütfen sorgulanacak bir DOMAIN giriniz.[/bold red]")
            return False

        print(f"[bold cyan][*] '{domain}' için DNS kayıtları aranıyor...[/bold cyan]")
        
        record_types = ["A", "MX", "NS", "TXT", "CNAME"]
        table = Table(title=f"DNS Records for {domain}", show_header=True, header_style="bold magenta")
        table.add_column("Record Type", style="dim", width=12)
        table.add_column("Data")

        found_any = False

        for qtype in record_types:
            try:
                answers = dns.resolver.resolve(domain, qtype)
                for rdata in answers:
                    table.add_row(qtype, rdata.to_text())
                    found_any = True
            except dns.resolver.NoAnswer:
                pass
            except dns.resolver.NXDOMAIN:
                print(f"[bold red][-] Domain '{domain}' bulunamadı (NXDOMAIN).[/bold red]")
                return False
            except dns.exception.Timeout:
                print(f"[bold red][-] DNS sorgusu zaman aşımına uğradı.[/bold red]")
                return False
            except Exception as e:
                pass # Bazen sadece bazı kayıtlar dönmez, döngü devam etsin

        if found_any:
            print()
            print(table)
            return True
        else:
            print("[yellow][!] Hiçbir DNS kaydı bulunamadı.[/yellow]")
            return True
