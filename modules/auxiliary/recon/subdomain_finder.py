from core.module import BaseModule
from core.option import Option
from rich.table import Table
from rich import print
from rich.progress import track
import socket
import logging
import os

class SubdomainFinder(BaseModule):
    def __init__(self):
        # --- Modül Bilgileri ---
        self.Name = "Subdomain Finder"
        self.Description = "Hedef domain için subdomain (alt alan adı) keşfi yapar (DNS Bruteforce)."
        self.Author = "MahmutP"
        self.Category = "auxiliary/recon"
        
        # --- Seçenekler (Options) ---
        self.Options = {
            "DOMAIN": Option(
                name="DOMAIN",
                value="google.com",
                required=True,
                description="Hedef ana domain (örn: example.com)",
                regex_check=False
            ),
            "WORDLIST": Option(
                name="WORDLIST",
                value="config/wordlists/subdomains/common.txt",
                required=True,
                description="Kullanılacak kelime listesi (wordlist) yolu",
                completion_dir="config/wordlists/subdomains/"
            ),
            "THREADS": Option( # Gelecekte eklenebilir, şimdilik tek thread
                name="THREADS",
                value=1,
                required=False,
                description="Thread sayısı (Şu an aktif değil, tek thread çalışır)"
            )
        }
        
        super().__init__()

    def run(self, options):
        """
        Subdomain Finder ana fonksiyonu.
        """
        domain = options.get("DOMAIN")
        wordlist_path = options.get("WORDLIST")

        # Dosya kontrolü
        if not os.path.exists(wordlist_path):
            print(f"[bold red][!][/bold red] Wordlist dosyası bulunamadı: {wordlist_path}")
            return False

        print(f"[bold blue][*][/bold blue] Hedef: {domain}")
        print(f"[bold blue][*][/bold blue] Wordlist: {wordlist_path}")
        print(f"[bold blue][*][/bold blue] Tarama başlatılıyor...")
        
        found_subdomains = []
        
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                subdomains = [line.strip() for line in f if line.strip()]
            
            # Kullanıcıya ilerleme çubuğu gösterelim
            for sub in track(subdomains, description="Taranıyor..."):
                target = f"{sub}.{domain}"
                try:
                    # DNS sorgusu yap
                    ip_address = socket.gethostbyname(target)
                    
                    # Eğer IP döndüyse subdomain vardır (Wildcard DNS kontrolü yapılmıyor şimdilik)
                    print(f"[green][+][/green] Bulundu: [bold cyan]{target}[/bold cyan] -> {ip_address}")
                    found_subdomains.append((target, ip_address))
                    
                except socket.gaierror:
                    # DNS çözümlenemedi (Normal durum)
                    pass
                except Exception as e:
                    # Diğer hatalar
                    pass
            
            # Sonuçları Tablo Olarak Göster
            if found_subdomains:
                print(f"\n[bold green][✓] Toplam {len(found_subdomains)} subdomain bulundu![/bold green]")
                table = Table(title=f"Subdomain Sonuçları ({domain})", show_header=True, header_style="bold magenta")
                table.add_column("Subdomain", style="cyan")
                table.add_column("IP Adresi", style="white")
                
                for sub, ip in found_subdomains:
                    table.add_row(sub, ip)
                print(table)
            else:
                print(f"\n[bold yellow][!] Hiçbir subdomain bulunamadı.[/bold yellow]")

            return True

        except Exception as e:
            print(f"[bold red][!][/bold red] Hata oluştu: {e}")
            logging.error(f"Subdomain finder hatasi: {e}")
            return False
