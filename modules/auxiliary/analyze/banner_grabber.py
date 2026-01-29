from core.module import BaseModule
from core.option import Option
from rich import print
import socket
import logging

class BannerGrabber(BaseModule):
    def __init__(self):
        # --- Modül Bilgileri ---
        self.Name = "Banner Grabber"
        self.Description = "Hedef servisin banner bilgisini (versiyon, yazılım adı vb.) çeker."
        self.Author = "MahmutP"
        self.Category = "auxiliary/analyze"
        
        # --- Seçenekler (Options) ---
        self.Options = {
            "RHOST": Option(
                name="RHOST",
                value="scanme.nmap.org",
                required=True,
                description="Hedef IP veya Hostname",
                regex_check=False # Domain name de girebilir
            ),
            "RPORT": Option(
                name="RPORT",
                value=22,
                required=True,
                description="Hedef port numarası"
            ),
            "TIMEOUT": Option(
                name="TIMEOUT",
                value=5,
                required=False,
                description="Bağlantı zaman aşımı süresi (saniye)"
            )
        }
        
        super().__init__()

    def run(self, options):
        """
        Banner grabber ana fonksiyonu.
        """
        target_host = options.get("RHOST")
        target_port = int(options.get("RPORT"))
        timeout = int(options.get("TIMEOUT"))

        print(f"[bold blue][*][/bold blue] Hedef: {target_host}:{target_port} üzerinde banner aranıyor...")
        
        try:
            # Socket oluştur
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            
            # Bağlan
            connect_result = s.connect_ex((target_host, target_port))
            
            if connect_result == 0:
                print(f"[bold green][+][/bold green] Port {target_port} açık. Veri bekleniyor...")
                
                # HTTP servisleri bazen istek bekler, ancak saf banner grabber önce okumayı dener.
                # Eğer okuma boş dönerse belki bir HTTP isteği atmayı deneyebiliriz ama
                # şimdilik temel TCP banner grabbing yapıyoruz (SSH, FTP, SMTP vb. için ideal).
                try:
                    banner = s.recv(1024)
                    if banner:
                        banner_str = banner.decode('utf-8', errors='ignore').strip()
                        print(f"[bold green][SUCCESS][/bold green] Banner Yakalandı!")
                        print(f"[bold white on blue] BANNER [/bold white on blue] {banner_str}")
                        return True
                    else:
                        print(f"[yellow][!][/yellow] Bağlantı sağlandı ancak sunucu herhangi bir veri göndermedi (Empty Response).")
                        return False
                except socket.timeout:
                    print(f"[yellow][!][/yellow] Bağlantı başarılı ama veri okuma zaman aşımına uğradı.")
                    return False
            else:
                print(f"[bold red][-][/bold red] Port {target_port} kapalı veya ulaşılamaz.")
                return False
                
            s.close()

        except Exception as e:
            print(f"[bold red][!][/bold red] Hata oluştu: {e}")
            logging.error(f"Banner grabber hatasi: {e}")
            return False
