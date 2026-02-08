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
            ),
            "REPOS": Option(
                name="REPOS",
                value="False",
                required=False,
                description="Repository bilgilerini çek (True/False)",
                choices=["True", "False"]
            ),
            "LIMIT": Option(
                name="LIMIT",
                value="50",
                required=False,
                description="Maksimum repo sayısı",
                regex_check=True,
                regex="^[0-9]+$"
            ),
            "SORT_BY": Option(
                name="SORT_BY",
                value="updated",
                required=False,
                description="Sıralama ölçütü (stars, updated, created, name)",
                choices=["stars", "updated", "created", "name"]
            ),
            "MUTUAL_ONLY": Option(
                name="MUTUAL_ONLY",
                value="False",
                required=False,
                description="Sadece karşılıklı takipleşenleri göster (True/False)",
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

    def fetch_repositories(self, username, limit=50, sort_by="updated"):
        """FAZ 2.1: Kullanıcının repository listesini ve detaylarını çeker."""
        console = Console()
        repos = []
        page = 1
        count = 0
        
        # Sort parametresi URL için mapping
        sort_map = {
            "stars": "stargazers",
            "updated": "updated",
            "created": "created",
            "name": "name"
        }
        sort_param = sort_map.get(sort_by, "updated")
        
        console.print(f"[yellow][*] {username} için repository listesi çekiliyor (Limit: {limit}, Sort: {sort_by})...[/yellow]")
        
        while count < limit:
            url = f"https://github.com/{username}?tab=repositories&page={page}&sort={sort_param}"
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                repo_list = soup.select('div[id="user-repositories-list"] li, li.col-12.d-flex')
                
                if not repo_list:
                    break
                
                for item in repo_list:
                    if count >= limit:
                        break
                        
                    repo_data = {}
                    
                    # İsim ve Link
                    name_tag = item.select_one('h3 a')
                    if name_tag:
                        repo_data['name'] = name_tag.get_text(strip=True)
                        repo_data['link'] = f"https://github.com{name_tag.get('href')}"
                    else:
                        continue
                        
                    # Açıklama
                    desc_tag = item.select_one('p[itemprop="description"]')
                    repo_data['description'] = desc_tag.get_text(strip=True) if desc_tag else "-"
                    
                    # Dil
                    lang_tag = item.select_one('span[itemprop="programmingLanguage"]')
                    repo_data['language'] = lang_tag.get_text(strip=True) if lang_tag else "-"
                    
                    # Star
                    star_link = item.select_one('a[href*="/stargazers"]')
                    repo_data['stars'] = star_link.get_text(strip=True).strip() if star_link else "0"
                    
                    # Fork
                    fork_link = item.select_one('a[href*="/forks"]')
                    repo_data['forks'] = fork_link.get_text(strip=True).strip() if fork_link else "0"
                    
                    # Son Güncelleme
                    time_tag = item.select_one('relative-time')
                    repo_data['updated'] = time_tag.get_text(strip=True) if time_tag else "-"
                    
                    repos.append(repo_data)
                    count += 1
                
                # Pagination kontrolü
                next_button = soup.select_one('a[rel="next"]')
                if not next_button:
                    break
                    
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                console.print(f"[red][!] Repo çekme hatası: {e}[/red]")
                break
                
        return repos

    def _parse_number(self, num_str):
        """1.2k gibi sayıları int'e çevirir."""
        if not num_str: return 0
        ns = num_str.lower().strip()
        if ns == "-" or not ns: return 0
        
        mult = 1
        if ns.endswith('k'):
            mult = 1000
            ns = ns[:-1]
        elif ns.endswith('m'):
            mult = 1000000
            ns = ns[:-1]
            
        try:
            return int(float(ns) * mult)
        except:
            return 0

    def analyze_repositories(self, repos):
        """FAZ 2.2: Repository listesini analiz eder."""
        from collections import Counter
        
        if not repos:
            return None
        
        analysis = {}
        
        # 1. En çok kullanılan diller
        languages = [r['language'] for r in repos if r['language'] and r['language'] != "-"]
        lang_counts = Counter(languages)
        analysis['top_languages'] = lang_counts.most_common(5)
        
        # 2. En popüler repo (Star sayısına göre)
        sorted_by_stars = sorted(repos, key=lambda x: self._parse_number(x['stars']), reverse=True)
        analysis['most_starred'] = sorted_by_stars[:3]
        
        # 3. En çok fork alan
        sorted_by_forks = sorted(repos, key=lambda x: self._parse_number(x['forks']), reverse=True)
        analysis['most_forked'] = sorted_by_forks[:3]
        
        return analysis

    def print_repo_analysis(self, analysis, console):
        if not analysis: return
        
        # Diller Tablosu
        table_lang = Table(title="🔥 En Çok Kullanılan Diller", style="magenta", show_header=True, header_style="bold magenta")
        table_lang.add_column("Dil", style="cyan")
        table_lang.add_column("Kullanım Sayısı", style="yellow")
        for lang, count in analysis['top_languages']:
            table_lang.add_row(lang, str(count))
        
        # En Popülerler
        table_pop = Table(title="🌟 En Popüler Repolar (Star)", style="yellow", show_header=True, header_style="bold yellow")
        table_pop.add_column("Repo", style="bold white")
        table_pop.add_column("Star", style="yellow")
        table_pop.add_column("Fork", style="white")
        table_pop.add_column("Dil", style="cyan")
        for r in analysis['most_starred']:
            table_pop.add_row(r['name'], str(r['stars']), str(r['forks']), r['language'])
            
        console.print(table_lang)
        console.print(table_pop)
        console.print("\n")

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

    def analyze_relationships(self, following, followers):
        """FAZ 3.1: Takipçi ilişkilerini analiz eder."""
        if not following or not followers:
            return None
            
        following_usernames = {u['username'] for u in following}
        follower_usernames = {u['username'] for u in followers}
        
        mutual = following_usernames.intersection(follower_usernames)
        not_following_back = following_usernames - follower_usernames # Sen ediyorsun, o etmiyor
        not_followed_back = follower_usernames - following_usernames # O ediyor, sen etmiyorsun
        
        return {
            'mutual': mutual,
            'not_following_back': not_following_back,
            'not_followed_back': not_followed_back
        }

    def print_relationship_analysis(self, analysis, console, mutual_only="False"):
        if not analysis: return
        
        table = Table(title="🔗 İlişki Analizi", style="bold blue")
        table.add_column("Durum", style="cyan")
        table.add_column("Kişi Sayısı", style="yellow")
        
        table.add_row("Karşılıklı Takip (Mutual)", str(len(analysis['mutual'])))
        if mutual_only != "True":
            table.add_row("Takip Edip Geri Dönmeyenler", str(len(analysis['not_following_back'])))
            table.add_row("Sizi Takip Edip Sizin Etmediğiniz", str(len(analysis['not_followed_back'])))
            
        console.print(table)
        console.print()
        
        if analysis['mutual']:
            console.print(f"[bold green]🤝 Karşılıklı Takipleşenler ({len(analysis['mutual'])}):[/bold green]")
            console.print(", ".join(list(analysis['mutual'])[:50]) + ("..." if len(analysis['mutual']) > 50 else ""))
            console.print()

        if mutual_only != "True":
            if analysis['not_following_back']:
                 console.print(f"[bold red]❌ Takip Edip Geri Dönmeyenler (İlk 20):[/bold red]")
                 console.print(", ".join(list(analysis['not_following_back'])[:20]) + "...")
                 console.print()

    def run(self, options):
        console = Console()
        username_input = options.get("USERNAME")
        output_file = options.get("OUTPUT")
        show_profile = options.get("PROFILE_INFO")
        show_repos = options.get("REPOS")
        limit = int(options.get("LIMIT"))
        sort_by = options.get("SORT_BY")
        mutual_only = options.get("MUTUAL_ONLY")
        
        target_user = self.get_username(username_input)
        
        console.print(f"[bold green][+] Hedef Kullanıcı:[/bold green] {target_user}")
        
        profile_info = None
        stats = None
        repos = []
        
        if show_profile == "True":
            profile_info = self.fetch_profile_info(target_user)
            stats = self.fetch_statistics(target_user)
            if profile_info:
                self.print_profile_info(target_user, profile_info, console, stats)
        
        repo_analysis = None
        if show_repos == "True":
            repos = self.fetch_repositories(target_user, limit, sort_by)
            repo_analysis = self.analyze_repositories(repos)
            self.print_repositories_table(repos, console)
            self.print_repo_analysis(repo_analysis, console)
        
        following = self.fetch_users(target_user, "following")
        followers = self.fetch_users(target_user, "followers")
        
        rel_analysis = self.analyze_relationships(following, followers)
        self.print_relationship_analysis(rel_analysis, console, mutual_only)
        
        # Ekrana Yazdır (Eğer Mutual Only ise sadece mutual basılabilir ama tablo zaten var)
        # Burada full listeleri basmak yerine analiz sonucunu basmak daha temiz.
        # Kullanıcı detay isterse zaten table basılıyor.
        
        # Sadece mutual_only=False ise listeleri bas
        if mutual_only != "True":
            self.print_table("FOLLOWING", following, console)
            self.print_table("FOLLOWERS", followers, console)
        
        # Dosyaya Kaydet
        if output_file:
            self.save_to_file(target_user, following, followers, output_file, console, profile_info if show_profile == "True" else None, stats, repos, repo_analysis, rel_analysis)

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

    def print_repositories_table(self, repos, console):
        if not repos:
            console.print("[yellow][!] Gösterilecek repository yok.[/yellow]")
            return

        table = Table(title=f"Repositories ({len(repos)})")
        table.add_column("İsim", style="bold green")
        table.add_column("Dil", style="cyan")
        table.add_column("⭐", style="yellow")
        table.add_column("🍴", style="white")
        table.add_column("Güncelleme", style="blue")
        # table.add_column("Açıklama", style="dim white") # Çok yer kapladığı için opsiyonel yapılabilir

        for repo in repos:
            table.add_row(
                repo['name'],
                repo['language'],
                repo['stars'],
                repo['forks'],
                repo['updated']
            )
        
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

    def save_to_file(self, target_user, following, followers, filename, console, profile_info=None, stats=None, repos=None, repo_analysis=None, rel_analysis=None):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"GitHub Raporu: {target_user}\n")
                f.write("="*40 + "\n\n")
                
                if rel_analysis:
                     f.write("ILISKI ANALIZI (FAZ 3.1):\n")
                     f.write(f"- Karsilikli Takip: {len(rel_analysis['mutual'])}\n")
                     f.write(f"- Takip Edip Donmeyenler: {len(rel_analysis['not_following_back'])}\n")
                     f.write(f"- Seni Takip Edip Etmediklerin: {len(rel_analysis['not_followed_back'])}\n")
                     
                     if rel_analysis['mutual']:
                         f.write("\nmutual_users:\n" + ", ".join(rel_analysis['mutual']) + "\n")
                     
                     f.write("\n" + "-"*40 + "\n\n")
                
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

                if repo_analysis:
                    f.write("REPO ANALIZI ve ISTATISTIKLERI (FAZ 2.2):\n")
                    f.write("En Cok Kullanilan Diller:\n")
                    for lang, count in repo_analysis['top_languages']:
                        f.write(f"- {lang}: {count}\n")
                    f.write("\nEn Populer Repolar:\n")
                    for r in repo_analysis['most_starred']:
                        f.write(f"- {r['name']} (Star: {r['stars']}, Fork: {r['forks']}, Dil: {r['language']})\n")
                    f.write("\n" + "-"*40 + "\n\n")

                if repos:
                    f.write(f"REPOSITORIES ({len(repos)}):\n")
                    for r in repos:
                        f.write(f"- [{r['name']}] ({r['link']})\n")
                        f.write(f"  Dil: {r['language']} | Star: {r['stars']} | Fork: {r['forks']}\n")
                        f.write(f"  Güncelleme: {r['updated']}\n")
                        f.write(f"  Açıklama: {r['description']}\n")
                        f.write("  ---\n")
                    f.write("\n" + "="*40 + "\n\n")

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
