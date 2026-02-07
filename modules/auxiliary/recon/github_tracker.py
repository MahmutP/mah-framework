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
        self.Description = "GitHub kullanıcısının profil, takipçi ve takip edilenlerini çeker."
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
                description="Sonuçların kaydedileceği dosya yolu (örn: sonuclar.txt)",
                completion_dir="."
            ),
            "PROFILE_INFO": Option(
                name="PROFILE_INFO",
                value="True",
                required=False,
                description="Profil bilgilerini göster/gizle (True/False)",
                choices=["True", "False"]
            )
        }
        super().__init__()

    def get_username(self, input_str):
        if "github.com/" in input_str:
            return input_str.split("github.com/")[-1].strip("/")
        return input_str.strip()

    def fetch_profile_info(self, username):
        url = f"https://github.com/{username}"
        try:
            response = requests.get(url)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            info = {}
            
            # Bio
            bio_div = soup.select_one('div.p-note.user-profile-bio > div')
            info['bio'] = bio_div.get_text(strip=True) if bio_div else None
            
            # Location
            location_li = soup.select_one('li[itemprop="homeLocation"]')
            info['location'] = location_li.select_one('span.p-label').get_text(strip=True) if location_li else None
            
            # Company
            company_li = soup.select_one('li[itemprop="worksFor"]')
            info['company'] = company_li.select_one('span.p-org').get_text(strip=True) if company_li else None
            
            # Website
            website_li = soup.select_one('li[itemprop="url"]')
            if website_li:
                link = website_li.select_one('a')
                info['website'] = link.get('href') if link else None
            else:
                info['website'] = None

            # Twitter
            twitter_li = soup.select_one('li[itemprop="social"]')
            if twitter_li:
                link = twitter_li.select_one('a[href*="twitter.com"]')
                info['twitter'] = link.get_text(strip=True) if link else None
            else:
                info['twitter'] = None
            
            # Email (public)
            email_li = soup.select_one('li[itemprop="email"]')
            if email_li:
                link = email_li.select_one('a')
                info['email'] = link.get_text(strip=True) if link else None
            else:
                info['email'] = None

            # FAZ 1.2: İstatistik Bilgileri - Repo ve Gist sayıları
            # Profil sayfasındaki nav linklerden repo/gist sayısını çek
            info['public_repos'] = self._extract_nav_count(soup, 'Repositories')
            info['public_gists'] = self._extract_nav_count(soup, 'Gists')

            # Creation Date & Last Activity (Harder to scrape reliably without auth/JS, skipping for basic implementation)
            # These will be implemented in Phase 7 with API integration.
            
            return info

        except Exception as e:
            print(f"Hata: {e}")
            return None
    
    def _extract_nav_count(self, soup, tab_name):
        """Profil sayfasındaki nav tab'larından sayı çıkarır (Repositories, Gists vb.)"""
        try:
            # Nav linklerini bul
            nav_links = soup.select('nav[aria-label="User profile"] a, a.UnderlineNav-item')
            for link in nav_links:
                text = link.get_text(strip=True)
                if tab_name in text:
                    # Sayı genellikle span içinde
                    count_span = link.select_one('span.Counter')
                    if count_span:
                        count_text = count_span.get_text(strip=True).replace(',', '')
                        return int(count_text) if count_text.isdigit() else 0
            return 0
        except:
            return 0
    
    def fetch_statistics(self, username):
        """FAZ 1.2: Kullanıcının toplam star ve fork sayılarını hesaplar."""
        console = Console()
        stats = {'total_stars': 0, 'total_forks': 0}
        page = 1
        
        console.print(f"[yellow][*] {username} için istatistikler hesaplanıyor...[/yellow]")
        
        while True:
            url = f"https://github.com/{username}?tab=repositories&page={page}"
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Repository kartlarını bul
                repo_list = soup.select('div[id="user-repositories-list"] li, li.col-12.d-flex')
                
                if not repo_list:
                    break
                
                found_repos = False
                for repo in repo_list:
                    # Star sayısı
                    star_link = repo.select_one('a[href*="/stargazers"]')
                    if star_link:
                        star_text = star_link.get_text(strip=True).replace(',', '')
                        if star_text.isdigit():
                            stats['total_stars'] += int(star_text)
                            found_repos = True
                    
                    # Fork sayısı
                    fork_link = repo.select_one('a[href*="/forks"]')
                    if fork_link:
                        fork_text = fork_link.get_text(strip=True).replace(',', '')
                        if fork_text.isdigit():
                            stats['total_forks'] += int(fork_text)
                
                if not found_repos:
                    break
                
                # Sonraki sayfa var mı kontrol et
                next_button = soup.select_one('a[rel="next"]')
                if not next_button:
                    break
                
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                console.print(f"[red][!] İstatistik hatası: {e}[/red]")
                break
        
        return stats

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
        show_profile = options.get("PROFILE_INFO")
        
        target_user = self.get_username(username_input)
        
        console.print(f"[bold green][+] Hedef Kullanıcı:[/bold green] {target_user}")
        
        profile_info = None
        stats = None
        
        if show_profile == "True":
            profile_info = self.fetch_profile_info(target_user)
            stats = self.fetch_statistics(target_user)
            if profile_info:
                self.print_profile_info(target_user, profile_info, console, stats)
        
        following = self.fetch_users(target_user, "following")
        followers = self.fetch_users(target_user, "followers")
        
        # Ekrana Yazdır
        self.print_table("FOLLOWING", following, console)
        self.print_table("FOLLOWERS", followers, console)
        
        # Dosyaya Kaydet
        if output_file:
            self.save_to_file(target_user, following, followers, output_file, console, profile_info if show_profile == "True" else None, stats)

        return True

    def print_profile_info(self, username, info, console, stats=None):
        table = Table(title=f"Profil Bilgileri: {username}")
        table.add_column("Özellik", style="cyan")
        table.add_column("Değer", style="white")
        
        if info.get('bio'): table.add_row("Bio", info['bio'])
        if info.get('location'): table.add_row("Konum", info['location'])
        if info.get('company'): table.add_row("Şirket", info['company'])
        if info.get('website'): table.add_row("Web Sitesi", info['website'])
        if info.get('twitter'): table.add_row("Twitter", info['twitter'])
        if info.get('email'): table.add_row("E-posta", info['email'])
        
        # FAZ 1.2: İstatistik Bilgileri
        table.add_row("─" * 15, "─" * 20)  # Ayırıcı
        table.add_row("📊 [bold]İSTATİSTİKLER[/bold]", "")
        if info.get('public_repos') is not None:
            table.add_row("Public Repo", str(info['public_repos']))
        if info.get('public_gists') is not None:
            table.add_row("Public Gist", str(info['public_gists']))
        if stats:
            table.add_row("⭐ Toplam Star", str(stats.get('total_stars', 0)))
            table.add_row("🍴 Toplam Fork", str(stats.get('total_forks', 0)))
        
        console.print(table)
        console.print("\n")

    def print_table(self, title, data, console):
        table = Table(title=f"{title} ({len(data)})")
        table.add_column("Kullanıcı Adı", style="cyan")
        table.add_column("Profil Linki", style="blue")
        
        for user in data:
            table.add_row(user['username'], user['link'])
            
        console.print(table)
        console.print("\n")

    def save_to_file(self, target_user, following, followers, filename, console, profile_info=None, stats=None):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"GitHub Raporu: {target_user}\n")
                f.write("="*40 + "\n\n")
                
                if profile_info:
                    f.write("PROFIL BILGILERI:\n")
                    if profile_info.get('bio'): f.write(f"- Bio: {profile_info['bio']}\n")
                    if profile_info.get('location'): f.write(f"- Konum: {profile_info['location']}\n")
                    if profile_info.get('company'): f.write(f"- Şirket: {profile_info['company']}\n")
                    if profile_info.get('website'): f.write(f"- Web: {profile_info['website']}\n")
                    if profile_info.get('twitter'): f.write(f"- Twitter: {profile_info['twitter']}\n")
                    if profile_info.get('email'): f.write(f"- Email: {profile_info['email']}\n")
                    
                    # FAZ 1.2: İstatistik Bilgileri
                    f.write("\nISTATISTIKLER:\n")
                    if profile_info.get('public_repos') is not None:
                        f.write(f"- Public Repo: {profile_info['public_repos']}\n")
                    if profile_info.get('public_gists') is not None:
                        f.write(f"- Public Gist: {profile_info['public_gists']}\n")
                    if stats:
                        f.write(f"- Toplam Star: {stats.get('total_stars', 0)}\n")
                        f.write(f"- Toplam Fork: {stats.get('total_forks', 0)}\n")
                    
                    f.write("\n" + "-"*40 + "\n\n")

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
