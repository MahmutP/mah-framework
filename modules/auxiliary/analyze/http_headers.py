from core.module import BaseModule
from core.option import Option
from rich.table import Table
from rich import print
import requests
import logging

class HttpHeaderAnalyzer(BaseModule):
    def __init__(self):
        # --- Modül Bilgileri ---
        self.Name = "HTTP Header Analyzer"
        self.Description = "Hedef web adresinin HTTP başlıklarını (headers) çeker ve analiz eder."
        self.Author = "MahmutP"
        self.Category = "auxiliary/analyze"
        
        # --- Seçenekler (Options) ---
        self.Options = {
            "URL": Option(
                name="URL",
                value="http://httpbin.org/get",
                required=True,
                description="Hedef URL adresi (örn: http://example.com)",
                regex_check=True,
                regex=r"^https?://.+" # Basit URL regex
            ),
            "TIMEOUT": Option(
                name="TIMEOUT",
                value=10,
                required=False,
                description="İstek zaman aşımı süresi (saniye)"
            )
        }
        
        super().__init__()

    def run(self, options):
        """
        HTTP Header Analyzer ana fonksiyonu.
        """
        target_url = options.get("URL")
        timeout = int(options.get("TIMEOUT"))

        print(f"[bold blue][*][/bold blue] Hedef: {target_url} analiz ediliyor...")
        
        try:
            # İsteği gönder (HEAD isteği genellikle sadece başlıkları almak için yeterlidir ve daha hızlıdır)
            # Ancak bazı sunucular HEAD'i engelleyebilir veya farklı yanıt verebilir.
            # Garanti olsun diye GET atıp stream=True diyebiliriz ama requests.head() standard.
            response = requests.head(target_url, timeout=timeout, allow_redirects=True)
            
            # Eğer status code 405 (Method Not Allowed) ise GET deneyelim
            if response.status_code == 405:
                print(f"[yellow][!][/yellow] HEAD isteği reddedildi (405). GET deneniyor...")
                response = requests.get(target_url, timeout=timeout, stream=True)
                response.close() # İçeriği indirmeden kapat

            print(f"[bold green][+][/bold green] Yanıt alındı! Durum Kodu: [bold cyan]{response.status_code}[/bold cyan]")

            # Başlıkları tablo olarak gösterelim
            table = Table(title=f"HTTP Headers ({target_url})", show_header=True, header_style="bold magenta")
            table.add_column("Başlık (Key)", style="cyan", no_wrap=True)
            table.add_column("Değer (Value)", style="white")

            important_headers = ["server", "x-powered-by", "strict-transport-security", "x-frame-options", "x-xss-protection", "set-cookie"]
            
            for key, value in response.headers.items():
                # Önemli güvenlik başlıklarını vurgulayalım veya işaretleyelim (isteğe bağlı)
                table.add_row(key, value)
            
            print(table)
            
            # Basit Analiz Raporu
            print("\n[bold white on blue] HIZLI ANALİZ [/bold white on blue]")
            missing_security_headers = []
            
            # Güvenlik başlık kontrolü
            security_headers_check = {
                "Strict-Transport-Security": "HSTS (HTTPS Zorlama) eksik.",
                "X-Frame-Options": "Clickjacking koruması (X-Frame-Options) eksik.",
                "X-Content-Type-Options": "MIME-sniffing koruması eksik.",
                "Content-Security-Policy": "XSS koruması (CSP) eksik."
            }
            
            for header, msg in security_headers_check.items():
                found = False
                for k in response.headers.keys():
                    if k.lower() == header.lower():
                        found = True
                        break
                if not found:
                    print(f"[yellow]⚠ {msg}[/yellow]")
            
            if "server" in response.headers:
                print(f"[green]✓ Sunucu Bilgisi:[/green] {response.headers['server']}")
            
            if "x-powered-by" in response.headers:
                print(f"[red]! Teknoloji Bilgisi İfşası (X-Powered-By):[/red] {response.headers['x-powered-by']}")

            return True

        except requests.exceptions.RequestException as e:
            print(f"[bold red][!][/bold red] Bağlantı hatası: {e}")
            logging.error(f"HTTP Header Analyzer hatasi: {e}")
            return False
        except Exception as e:
            print(f"[bold red][!][/bold red] Beklenmedik hata: {e}")
            logging.error(f"HTTP Header Analyzer genel hata: {e}")
            return False
