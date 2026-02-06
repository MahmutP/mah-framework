from core.module import BaseModule
from core.option import Option
from rich.console import Console
from rich.table import Table
import requests
from bs4 import BeautifulSoup
import time

class GitHubTracker(BaseModule):
    def __init__(self):
        self.Name = "auxiliary/recon/github_tracker"
        self.Description = "GitHub kullanıcısının takipçi ve takip edilenlerini çeker."
        self.Author = "Mahmut P."
        self.Category = "auxiliary/recon"
        
        self.Options = {
            "USERNAME": Option(
                name="USERNAME",
                value="",
                required=True,
                description="Hedef GitHub kullanıcı adı veya linki",
                choices=[]
            ),
            "OUTPUT": Option(
                name="OUTPUT",
                value="",
                required=False,
                description="Sonuçların kaydedileceği dosya yolu (örn: sonuclar.txt)"
            )
        }
        super().__init__()

    def get_username(self, input_str):
        if "github.com/" in input_str:
            return input_str.split("github.com/")[-1].strip("/")
        return input_str

    def fetch_users(self, username, relation_type):
        users = []
        page = 1
        base_url = f"https://github.com/{username}?tab={relation_type}"
        console = Console()
        
        console.print(f"[yellow][*] {username} için {relation_type} verileri çekiliyor...[/yellow]")
        
        while True:
            url = f"{base_url}&page={page}"
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    console.print(f"[red][!] Sayfa {page} alınamadı: {response.status_code}[/red]")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                user_links = soup.select('a[data-hovercard-type="user"]')
                
                page_users = []
                for link in user_links:
                    href = link.get('href')
                    if href:
                        u = href.strip("/")
                        if u != username and u not in [x['username'] for x in page_users]:
                            # Kullanıcı adını ve linkini sakla
                            page_users.append({
                                'username': u,
                                'link': f"https://github.com/{u}"
                            })
                
                if not page_users:
                    break
                    
                for u in page_users:
                    if u not in users:
                        users.append(u)
                
                next_button = soup.select_one('a[rel="next"]')
                if not next_button:
                    break
                
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                console.print(f"[red][!] Hata: {e}[/red]")
                break
                
        return users

    def run(self, options):
        console = Console()
        username_input = options.get("USERNAME")
        output_file = options.get("OUTPUT")
        
        target_user = self.get_username(username_input)
        
        console.print(f"[bold green][+] Hedef Kullanıcı:[/bold green] {target_user}")
        
        following = self.fetch_users(target_user, "following")
        followers = self.fetch_users(target_user, "followers")
        
        # Ekrana Yazdır
        self.print_table("FOLLOWING", following, console)
        self.print_table("FOLLOWERS", followers, console)
        
        # Dosyaya Kaydet
        if output_file:
            self.save_to_file(target_user, following, followers, output_file, console)

        return True

    def print_table(self, title, data, console):
        table = Table(title=f"{title} ({len(data)})")
        table.add_column("Kullanıcı Adı", style="cyan")
        table.add_column("Profil Linki", style="blue")
        
        for user in data:
            table.add_row(user['username'], user['link'])
            
        console.print(table)
        console.print("\n")

    def save_to_file(self, target_user, following, followers, filename, console):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"GitHub Raporu: {target_user}\n")
                f.write("="*40 + "\n\n")
                
                f.write(f"FOLLOWING ({len(following)}):\n")
                for u in following:
                    f.write(f"- {u['username']} ({u['link']})\n")
                
                f.write("\n" + "="*40 + "\n\n")
                
                f.write(f"FOLLOWERS ({len(followers)}):\n")
                for u in followers:
                    f.write(f"- {u['username']} ({u['link']})\n")
                    
            console.print(f"[bold green][+] Sonuçlar dosyaya kaydedildi:[/bold green] {filename}")
        except Exception as e:
            console.print(f"[bold red][!] Dosya kaydetme hatası:[/bold red] {e}")
