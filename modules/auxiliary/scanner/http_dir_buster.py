from core.module import BaseModule
from core.option import Option
from rich import print
import urllib.request
import urllib.error
import concurrent.futures
import os

class HttpDirBuster(BaseModule):
    def __init__(self):
        self.Name = "HTTP Directory Buster"
        self.Description = "Web sunucusunda gizli veya açık dizinleri/dosyaları tespit eder."
        self.Author = "MahmutP & AI"
        self.Category = "auxiliary/scanner"
        
        self.Options = {
            "RHOST": Option(
                name="RHOST",
                value="http://127.0.0.1",
                required=True,
                description="Hedef URL (http:// veya https:// ile başlamalı)"
            ),
            "WORDLIST": Option(
                name="WORDLIST",
                value="config/wordlists/dirs/common.txt",
                required=True,
                description="Kullanılacak kelime listesi dosya yolu"
            ),
            "THREADS": Option(
                name="THREADS",
                value=10,
                required=True,
                description="Eşzamanlı tarama yapacak thread sayısı"
            )
        }
        
        super().__init__()

    def check_url(self, base_url, path):
        """Tek bir URL'i kontrol eder."""
        target_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            req = urllib.request.Request(
                target_url, 
                headers={'User-Agent': 'Mozilla/5.0 (MahFramework)'},
                method='HEAD' # Sadece başlıkları çek, içeriği değil (Daha hızlı)
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                return (path, response.status, target_url)
        except urllib.error.HTTPError as e:
            # 403 Forbidden veya 401 Unauthorized da ilginç olabilir
            if e.code in [401, 403]:
                return (path, e.code, target_url)
            return None
        except Exception:
            return None

    def run(self, options):
        target_url = options.get("RHOST")
        wordlist_path = options.get("WORDLIST")
        try:
            threads = int(options.get("THREADS"))
        except:
            threads = 10

        # Wordlist kontrolü
        if not os.path.exists(wordlist_path):
            print(f"[bold red][!][/bold red] Wordlist dosyası bulunamadı: {wordlist_path}")
            return False

        print(f"[bold blue][*][/bold blue] Hedef: {target_url}")
        print(f"[bold blue][*][/bold blue] Wordlist yükleniyor: {wordlist_path}")
        
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                paths = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"[bold red][!][/bold red] Dosya okunurken hata: {e}")
            return False

        print(f"[bold blue][*][/bold blue] Tarama başlıyor... ({len(paths)} yol, {threads} thread)")

        found_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_url = {executor.submit(self.check_url, target_url, path): path for path in paths}
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                if result:
                    path, status, full_url = result
                    
                    status_color = "green"
                    if status in [401, 403]:
                        status_color = "yellow"
                    elif status >= 500:
                        status_color = "red"
                        
                    print(f"[{status_color}][+] /{path:<20} (Status: {status})[/{status_color}]")
                    found_count += 1

        print(f"\n[bold green]Tarama Tamamlandı![/bold green] Toplam {found_count} dizin/dosya bulundu.")
        return True
