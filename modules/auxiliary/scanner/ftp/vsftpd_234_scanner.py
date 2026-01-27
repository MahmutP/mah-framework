# =============================================================================
# vsftpd 2.3.4 Backdoor Vulnerability Scanner
# =============================================================================
# CVE-2011-2523 için zafiyet tarayıcı modülü
#
# AÇIKLAMA:
#   Bu modül, hedef sistemin vsftpd 2.3.4 sürümünü çalıştırıp çalıştırmadığını
#   ve arka kapı zafiyetine savunmasız olup olmadığını tespit eder.
#
# ÇALIŞMA MANTIĞI:
#   1. FTP portuna bağlan
#   2. Banner'ı oku ve sürümü kontrol et
#   3. Arka kapıyı tetiklemeyi dene (zararsız - sadece port kontrolü)
#   4. Port 6200'ün açılıp açılmadığını kontrol et
#   5. Sonucu raporla
#
# KULLANIM:
#   1. use auxiliary/scanner/ftp/vsftpd_234_scanner
#   2. set RHOSTS <hedef_ip veya ip_aralığı>
#   3. run
#
# NOT: Bu tarayıcı sadece tespit yapar, exploit çalıştırmaz.
# =============================================================================

import socket
import time
from typing import Dict, Any, List

from core.module import BaseModule
from core.option import Option
from core import logger
from rich import print


class vsftpd_234_scanner(BaseModule):
    """vsftpd 2.3.4 Backdoor Zafiyet Tarayıcı
    
    Bu modül, hedef sistemlerin vsftpd 2.3.4 arka kapı zafiyetine
    (CVE-2011-2523) savunmasız olup olmadığını tespit eder.
    
    Tarama Aşamaları:
        1. FTP banner kontrolü (sürüm tespiti)
        2. Arka kapı tetikleme denemesi
        3. Backdoor port (6200) erişilebilirlik kontrolü
    
    Sonuç Kodları:
        - VULNERABLE: Zafiyet tespit edildi, exploit çalıştırılabilir
        - NOT VULNERABLE: vsftpd 2.3.4 değil veya yamalı
        - UNKNOWN: Bağlantı kurulamadı veya belirsiz durum
    """
    
    # =========================================================================
    # MODÜL META BİLGİLERİ
    # =========================================================================
    Name = "vsftpd 2.3.4 Backdoor Scanner"
    Description = "CVE-2011-2523 - vsftpd 2.3.4 arka kapı zafiyetini tespit eder."
    Author = "Mahmut P."
    Category = "auxiliary/scanner"
    
    # =========================================================================
    # SABİTLER
    # =========================================================================
    BACKDOOR_PORT = 6200           # Arka kapının açıldığı port
    TRIGGER_USER = "mahmut:)"      # Arka kapıyı tetikleyen kullanıcı adı
    TRIGGER_PASS = "pass"          # Herhangi bir parola
    DEFAULT_TIMEOUT = 5            # Bağlantı zaman aşımı (saniye)
    
    def __init__(self):
        """Modül başlatıcı - Options tanımlaması
        
        Options:
            RHOSTS: Taranacak hedef IP adresi veya adresleri
            RPORT: FTP servisinin çalıştığı port
            TIMEOUT: Bağlantı zaman aşımı süresi
        """
        super().__init__()
        
        self.Options = {
            "RHOSTS": Option(
                name="RHOSTS",
                value=None,
                required=True,
                description="Hedef IP adresi (tekli veya virgülle ayrılmış liste)"
            ),
            "RPORT": Option(
                name="RPORT",
                value=21,
                required=True,
                description="FTP servisinin portu (varsayılan: 21)",
                regex_check=True,
                regex=r"^\d{1,5}$"
            ),
            "TIMEOUT": Option(
                name="TIMEOUT",
                value=5,
                required=False,
                description="Bağlantı zaman aşımı süresi (saniye)",
                regex_check=True,
                regex=r"^\d+$"
            ),
        }
        
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)
    
    # =========================================================================
    # YARDIMCI METODLAR
    # =========================================================================
    
    def _create_socket(self, timeout: int) -> socket.socket:
        """Yapılandırılmış bir TCP socket oluşturur."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        return sock
    
    def _check_ftp_banner(self, host: str, port: int, timeout: int) -> tuple:
        """FTP banner'ını kontrol eder ve vsftpd 2.3.4 olup olmadığını döner.
        
        Args:
            host: Hedef IP adresi
            port: FTP port numarası
            timeout: Zaman aşımı süresi
            
        Returns:
            (is_vsftpd_234, banner_string, error_message)
        """
        try:
            sock = self._create_socket(timeout)
            sock.connect((host, port))
            
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            sock.close()
            
            is_vulnerable = "vsFTPd 2.3.4" in banner or "vsftpd 2.3.4" in banner.lower()
            return (is_vulnerable, banner, None)
            
        except socket.timeout:
            return (False, None, "Bağlantı zaman aşımı")
        except ConnectionRefusedError:
            return (False, None, "Bağlantı reddedildi")
        except socket.error as e:
            return (False, None, str(e))
    
    def _trigger_and_check_backdoor(self, host: str, port: int, timeout: int) -> tuple:
        """Arka kapıyı tetiklemeye çalışır ve port 6200'ü kontrol eder.
        
        Args:
            host: Hedef IP adresi
            port: FTP port numarası
            timeout: Zaman aşımı süresi
            
        Returns:
            (backdoor_opened, error_message)
        """
        ftp_sock = None
        backdoor_sock = None
        
        try:
            # FTP'ye bağlan
            ftp_sock = self._create_socket(timeout)
            ftp_sock.connect((host, port))
            ftp_sock.recv(1024)  # Banner'ı oku
            
            # Arka kapıyı tetikle
            ftp_sock.send(f"USER {self.TRIGGER_USER}\r\n".encode())
            ftp_sock.recv(1024)
            ftp_sock.send(f"PASS {self.TRIGGER_PASS}\r\n".encode())
            
            # Kısa bekleme
            time.sleep(1)
            ftp_sock.close()
            ftp_sock = None
            
            # Arka kapı portunu kontrol et
            backdoor_sock = self._create_socket(timeout)
            backdoor_sock.connect((host, self.BACKDOOR_PORT))
            backdoor_sock.close()
            backdoor_sock = None
            
            return (True, None)
            
        except socket.timeout:
            return (False, "Backdoor portu yanıt vermedi")
        except ConnectionRefusedError:
            return (False, "Backdoor portu kapalı")
        except socket.error as e:
            return (False, str(e))
        finally:
            if ftp_sock:
                try:
                    ftp_sock.close()
                except:
                    pass
            if backdoor_sock:
                try:
                    backdoor_sock.close()
                except:
                    pass
    
    def _parse_hosts(self, rhosts: str) -> List[str]:
        """RHOSTS string'ini IP listesine çevirir.
        
        Desteklenen formatlar:
            - Tekli IP: "192.168.1.1"
            - Virgülle ayrılmış: "192.168.1.1, 192.168.1.2"
            - Boşlukla ayrılmış: "192.168.1.1 192.168.1.2"
        
        Args:
            rhosts: Ham RHOSTS string'i
            
        Returns:
            IP adresleri listesi
        """
        # Virgül veya boşlukla ayır
        hosts = rhosts.replace(',', ' ').split()
        # Boşlukları temizle
        return [h.strip() for h in hosts if h.strip()]
    
    def _scan_host(self, host: str, port: int, timeout: int) -> dict:
        """Tek bir host'u tarar ve sonuç döner.
        
        Args:
            host: Hedef IP
            port: FTP portu
            timeout: Zaman aşımı
            
        Returns:
            Tarama sonucu dict'i
        """
        result = {
            "host": host,
            "port": port,
            "status": "UNKNOWN",
            "banner": None,
            "details": None
        }
        
        # Aşama 1: Banner kontrolü
        is_vsftpd_234, banner, error = self._check_ftp_banner(host, port, timeout)
        result["banner"] = banner
        
        if error:
            result["status"] = "ERROR"
            result["details"] = error
            return result
        
        if not is_vsftpd_234:
            result["status"] = "NOT VULNERABLE"
            result["details"] = "vsftpd 2.3.4 değil"
            return result
        
        # Aşama 2: Arka kapı kontrolü
        backdoor_opened, error = self._trigger_and_check_backdoor(host, port, timeout)
        
        if backdoor_opened:
            result["status"] = "VULNERABLE"
            result["details"] = f"Backdoor portu ({self.BACKDOOR_PORT}) açıldı!"
        else:
            result["status"] = "PATCHED"
            result["details"] = f"vsftpd 2.3.4 ama yamalı olabilir ({error})"
        
        return result
    
    # =========================================================================
    # ANA ÇALIŞTIRMA METODU
    # =========================================================================
    
    def run(self, options: Dict[str, Any]) -> str:
        """Tarayıcıyı çalıştırır.
        
        Args:
            options: Kullanıcı tarafından ayarlanan seçenekler
        
        Returns:
            Tarama özet raporu
        """
        # Parametreleri al
        rhosts = options.get("RHOSTS")
        rport = int(options.get("RPORT", 21))
        timeout = int(options.get("TIMEOUT", self.DEFAULT_TIMEOUT))
        
        if not rhosts:
            print("[!] [bold red]RHOSTS parametresi zorunludur![/bold red]")
            return "Hata: RHOSTS belirtilmedi"
        
        # Host'ları parse et
        hosts = self._parse_hosts(rhosts)
        
        print("\n" + "=" * 70)
        print(f"[*] [bold cyan]vsftpd 2.3.4 Backdoor Scanner[/bold cyan]")
        print(f"[*] Hedefler: {len(hosts)} host")
        print(f"[*] Port: {rport}")
        print(f"[*] Timeout: {timeout}s")
        print("=" * 70 + "\n")
        
        logger.info(f"vsftpd taraması başlatıldı: {len(hosts)} host")
        
        # Sonuç istatistikleri
        stats = {"vulnerable": 0, "not_vulnerable": 0, "error": 0, "patched": 0}
        
        # Her host'u tara
        for host in hosts:
            print(f"[*] Taranıyor: {host}:{rport}...", end=" ")
            
            result = self._scan_host(host, rport, timeout)
            
            # Sonucu göster
            if result["status"] == "VULNERABLE":
                print(f"[bold green]✓ VULNERABLE[/bold green]")
                print(f"    └─ Banner: {result['banner']}")
                print(f"    └─ {result['details']}")
                stats["vulnerable"] += 1
                logger.info(f"VULNERABLE: {host}:{rport}")
                
            elif result["status"] == "PATCHED":
                print(f"[bold yellow]⚠ PATCHED[/bold yellow]")
                print(f"    └─ Banner: {result['banner']}")
                print(f"    └─ {result['details']}")
                stats["patched"] += 1
                logger.info(f"PATCHED: {host}:{rport}")
                
            elif result["status"] == "NOT VULNERABLE":
                print(f"[bold blue]✗ NOT VULNERABLE[/bold blue]")
                if result["banner"]:
                    print(f"    └─ Banner: {result['banner']}")
                stats["not_vulnerable"] += 1
                logger.debug(f"NOT VULNERABLE: {host}:{rport}")
                
            else:  # ERROR
                print(f"[bold red]✗ ERROR[/bold red]")
                print(f"    └─ {result['details']}")
                stats["error"] += 1
                logger.warning(f"ERROR: {host}:{rport} - {result['details']}")
        
        # Özet rapor
        print("\n" + "=" * 70)
        print("[*] Tarama Tamamlandı - Özet")
        print("=" * 70)
        print(f"    [bold green]Vulnerable:[/bold green]     {stats['vulnerable']}")
        print(f"    [bold yellow]Patched:[/bold yellow]        {stats['patched']}")
        print(f"    [bold blue]Not Vulnerable:[/bold blue] {stats['not_vulnerable']}")
        print(f"    [bold red]Error:[/bold red]          {stats['error']}")
        print("=" * 70 + "\n")
        
        logger.info(f"Tarama tamamlandı: {stats}")
        
        return f"Tarama tamamlandı. {stats['vulnerable']} vulnerable host bulundu."
