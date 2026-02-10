from core.module import BaseModule
from core.option import Option
from rich import print
import socket
import concurrent.futures

class PortScanner(BaseModule):
    def __init__(self):
        self.Name = "Port Scanner"
        self.Description = "Belirtilen hedef IP üzerindeki açık TCP portlarını tarar."
        self.Author = "Mahmut P."
        self.Category = "auxiliary/scanner"
        
        self.Options = {
            "RHOST": Option(
                name="RHOST",
                value="127.0.0.1",
                required=True,
                description="Hedef IP adresi",
                regex_check=True,
                regex=r"^\d{1,3}(\.\d{1,3}){3}$"
            ),
            "RPORTS": Option(
                name="RPORTS",
                value="1-1000",
                required=True,
                description="Taranacak port aralığı (Örn: 1-1000 veya 80,443)"
            ),
            "THREADS": Option(
                name="THREADS",
                value=10,
                required=True,
                description="Eşzamanlı tarama yapacak thread sayısı"
            )
        }
        
        super().__init__()

    def scan_port(self, ip, port):
        """Tek bir portu tarar ve sonucu döner."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0) # 1 saniye zaman aşımı
                result = s.connect_ex((ip, int(port)))
                if result == 0:
                    return port
        except:
            pass
        return None

    def parse_ports(self, rports):
        """Port stringini listeye çevirir."""
        ports = set()
        parts = rports.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    for p in range(start, end + 1):
                        ports.add(p)
                except ValueError:
                    print(f"[yellow][!][/yellow] Geçersiz port aralığı formatı: {part}")
            else:
                try:
                    ports.add(int(part))
                except ValueError:
                    print(f"[yellow][!][/yellow] Geçersiz port formatı: {part}")
        
        # 0-65535 aralığına filtrele
        valid_ports = sorted([p for p in ports if 1 <= p <= 65535])
        return valid_ports

    def run(self, options):
        target_ip = options.get("RHOST")
        rports_str = str(options.get("RPORTS"))
        try:
            threads = int(options.get("THREADS"))
        except:
            threads = 10

        print(f"[bold blue][*][/bold blue] Hedef: {target_ip}")
        print(f"[bold blue][*][/bold blue] Portlar ayrıştırılıyor...")
        
        target_ports = self.parse_ports(rports_str)
        if not target_ports:
            print("[bold red][!] Taranacak geçerli port bulunamadı.[/bold red]")
            return False

        print(f"[bold blue][*][/bold blue] {len(target_ports)} port taranacak. (Thread: {threads})")
        
        open_ports = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_port = {executor.submit(self.scan_port, target_ip, port): port for port in target_ports}
            for future in concurrent.futures.as_completed(future_to_port):
                port = future_to_port[future]
                try:
                    result = future.result()
                    if result:
                        print(f"[bold green][+] Port {port} AÇIK (OPEN)[/bold green]")
                        open_ports.append(port)
                except Exception as exc:
                    pass

        if open_ports:
            print(f"\n[bold green]Tarama Tamamlandı![/bold green] Toplam {len(open_ports)} açık port bulundu.")
        else:
            print(f"\n[bold yellow]Tarama Tamamlandı![/bold yellow] Açık port bulunamadı.")
            
        return True
