import ssl
import socket
from datetime import datetime
from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print

class ssl_checker(BaseModule):
    """
    Hedef sistemin SSL/TLS sertifikasını analiz eden modül.
    """
    Name = "SSL/TLS Cert Checker"
    Description = "Belirtilen hedefteki SSL/TLS sertifikasının süresini ve durumunu kontrol eder."
    Author = "Mahmut P."
    Category = "auxiliary/scanner"
    Version = "1.0"

    Requirements = {"python": []}

    def __init__(self):
        super().__init__()
        self.Options = {
            "RHOST": Option("RHOST", "127.0.0.1", True, "Hedef IP adresi veya Domain"),
            "RPORT": Option("RPORT", 443, True, "Hedef Port"),
            "TIMEOUT": Option("TIMEOUT", 5, False, "Bağlantı zaman aşımı (saniye)"),
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    def run(self, options: Dict[str, Any]):
        rhost = options.get("RHOST")
        rport = int(options.get("RPORT", 443))
        timeout = float(options.get("TIMEOUT", 5))

        print(f"[bold cyan][*] {rhost}:{rport} TLS/SSL sertifikası kontrol ediliyor...[/bold cyan]")

        context = ssl.create_default_context()
        # Doğrulama yapmadan salt bilgiyi almak istiyoruz (Bilinmeyen CA'lar için fallback)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        try:
            with socket.create_connection((rhost, rport), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=rhost) as ssock:
                    cert = ssock.getpeercert(binary_form=True)
                    # binary format olduğu için cryptography veya built-in ssl module fallback
                    # default format dict üzerinden veri okumak için tekrar wrap edelim
            
            # Doğru dict formatında almak için verify_mode değiştirmemiz gerekir, yoksa boş dönebilir.
            # Buna alternatif olarak yeniden bağlanıp dict formatında çekelim.
            context_dict = ssl.create_default_context()
            context_dict.check_hostname = False
            context_dict.verify_mode = ssl.CERT_NONE
            try:
                # SSL/TLS için dict parsing desteği genelde Python'un default'unda var
                cert_dict = ssl.get_server_certificate((rhost, rport))
                # x509 objesi parse etmek external modül gerekebilir. Kısayol için dict çekiyoruz
                with socket.create_connection((rhost, rport), timeout=timeout) as sock2:
                    with context_dict.wrap_socket(sock2, server_hostname=rhost) as ssock2:
                        cert_data = ssock2.getpeercert(binary_form=False)
            except Exception:
                cert_data = None
                
            if cert_data:
                print(f"[bold green][+] Sertifika Bilgileri ({rhost}):[/bold green]")
                if 'subject' in cert_data:
                    subject = dict(x[0] for x in cert_data['subject'])
                    print(f"  [green]Issued To:[/green] {subject.get('commonName', 'Unknown')}")
                if 'issuer' in cert_data:
                    issuer = dict(x[0] for x in cert_data['issuer'])
                    print(f"  [green]Issuer:[/green] {issuer.get('organizationName', 'Unknown')}")
                
                if 'notAfter' in cert_data:
                    expire_date = datetime.strptime(cert_data['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_left = (expire_date - datetime.utcnow()).days
                    color = "red" if days_left < 15 else "yellow" if days_left < 30 else "green"
                    print(f"  [green]Expires (UTC):[/green] {expire_date} ([{color}]{days_left} gün kaldı[/{color}])")

                print(f"  [green]TLS Version:[/green] {ssock.version()}")

                return True
            else:
                # Eger cert_data boş ise external modül kullanmadan (cryptography vs) getpeercert dict parse edememiştir.
                print(f"[yellow][!] Cihazda SSL/TLS etkin ancak dict formatında veri okunamadı.[/yellow]")
                return True

        except ssl.SSLError as e:
            print(f"[bold red][-] SSL/TLS Hatası: {e}[/bold red]")
            return False
        except socket.timeout:
            print(f"[bold red][-] {rhost}:{rport} - Bağlantı zaman aşımına uğradı.[/bold red]")
            return False
        except ConnectionRefusedError:
            print(f"[bold red][-] {rhost}:{rport} - Bağlantı reddedildi (Port kapalı olabilir).[/bold red]")
            return False
        except Exception as e:
            print(f"[bold red][-] Beklenmeyen Hata: {str(e)}[/bold red]")
            return False
