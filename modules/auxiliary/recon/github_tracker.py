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
            ),
            "COMPARE": Option(
                name="COMPARE",
                value="",
                required=False,
                description="Karşılaştırılacak ikinci kullanıcı (Ortak takipçi analizi için)",
                choices=[]
            ),
            "NETWORK_ANALYSIS": Option(
                name="NETWORK_ANALYSIS",
                value="False",
                required=False,
                description="Ağ Analizi Yap (Takipçilerin lokasyon/şirket analizi - YAVAŞ)",
                choices=["True", "False"]
            ),
            "ACTIVITY": Option(
                name="ACTIVITY",
                value="False",
                required=False,
                description="Son aktiviteleri çek (Push, Star, Fork, Issue, PR)",
                choices=["True", "False"]
            ),
            "DAYS": Option(
                name="DAYS",
                value="30",
                required=False,
                description="Son kaç günlük aktivite (varsayılan: 30)",
                regex_check=True,
                regex="^[0-9]+$"
            ),
            "CONTRIBUTIONS": Option(
                name="CONTRIBUTIONS",
                value="False",
                required=False,
                description="Contribution analizi çek (Yıllık katkı, aktif repolar, PR/Issue istatistikleri)",
                choices=["True", "False"]
            ),
            "ORGS": Option(
                name="ORGS",
                value="False",
                required=False,
                description="Organizasyon bilgilerini ve üyelerini çek",
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

    def compare_users(self, user1, user1_followers, user1_following, user2, console, output_file=None):
        """FAZ 3.1: İki kullanıcıyı karşılaştırır (Ortak takipçi/takip edilen)."""
        console.print(f"\n[bold blue]🔄 {user1} ve {user2} Karşılaştırılıyor...[/bold blue]")
        
        # User 2 verilerini çek
        u2_followers = self.fetch_users(user2, "followers")
        u2_following = self.fetch_users(user2, "following")
        
        # Analiz
        u1_followers_set = {u['username'] for u in user1_followers}
        u2_followers_set = {u['username'] for u in u2_followers}
        common_followers = u1_followers_set.intersection(u2_followers_set)
        
        u1_following_set = {u['username'] for u in user1_following}
        u2_following_set = {u['username'] for u in u2_following}
        common_following = u1_following_set.intersection(u2_following_set)
        
        # Ekrana bas
        table = Table(title=f"Ortak Analiz: {user1} & {user2}", style="bold green")
        table.add_column("Metrik", style="cyan")
        table.add_column("Sayı", style="yellow")
        table.add_column("Detay (İlk 5)", style="white")
        
        table.add_row("Ortak Takipçiler", str(len(common_followers)), ", ".join(list(common_followers)[:5]) + ("..." if len(common_followers)>5 else ""))
        table.add_row("Ortak Takip Edilenler", str(len(common_following)), ", ".join(list(common_following)[:5]) + ("..." if len(common_following)>5 else ""))
        
        console.print(table)
        console.print()
        
        # Dosyaya ekleme
        if output_file:
             try:
                 with open(output_file, 'a', encoding='utf-8') as f:
                     f.write(f"\nKARSILASTIRMA (COMPARE): {user1} vs {user2}\n")
                     f.write(f"- Ortak Takipciler ({len(common_followers)}): {', '.join(common_followers)}\n")
                     f.write(f"- Ortak Takip Edilenler ({len(common_following)}): {', '.join(common_following)}\n")
                     f.write("-" * 40 + "\n\n")
                 console.print(f"[bold green][+] Karşılaştırma sonuçları dosyaya eklendi.[/bold green]")
             except Exception as e:
                 console.print(f"[red][!] Dosya yazma hatası: {e}[/red]")

    def analyze_network(self, users, limit=20):
        """FAZ 3.2: Ağ Analizi (Lokasyon, Şirket, Aktiflik)."""
        from collections import Counter
        from rich.progress import track
        
        if not users: return None
        
        target_users = users[:limit]
        stats = {
            'locations': [], 
            'companies': [], 
            'active_count': 0, 
            'total_scanned': 0
        }
        
        # Progress bar ile göster
        for u in track(target_users, description="[green]Ağ analizi yapılıyor (Profil Taraması)...[/green]"):
            username = u['username']
            info = self.fetch_profile_info(username)
            if info:
                stats['total_scanned'] += 1
                
                # Lokasyon Analizi
                if info.get('location'):
                    stats['locations'].append(info['location'])
                    
                # Şirket Analizi
                if info.get('company'):
                    stats['companies'].append(info['company'])
                    
                # Aktiflik Analizi (Repo sayısı > 0 ise aktif kabul edelim)
                if info.get('public_repos', 0) > 0:
                    stats['active_count'] += 1
            
            time.sleep(0.5) # Rate limit koruması
            
        # Counter ile en sık geçenleri bul
        stats['top_locations'] = Counter(stats['locations']).most_common(5)
        stats['top_companies'] = Counter(stats['companies']).most_common(5)
        
        return stats

    def print_network_analysis(self, stats, console):
        if not stats or stats['total_scanned'] == 0: return
        
        table = Table(title=f"🕸️ Ağ Analizi (Taranan: {stats['total_scanned']})", style="bold magenta")
        table.add_column("Kategori", style="cyan")
        table.add_column("En Yaygın", style="yellow")
        table.add_column("Detay", style="white")
        
        # Lokasyon
        top_loc = ", ".join([f"{k} ({v})" for k,v in stats['top_locations']])
        table.add_row("📍 Lokasyonlar", top_loc if top_loc else "-", str(len(stats['locations'])) + " kişi belirtti")
        
        # Şirket
        top_comp = ", ".join([f"{k} ({v})" for k,v in stats['top_companies']])
        table.add_row("🏢 Şirketler", top_comp if top_comp else "-", str(len(stats['companies'])) + " kişi belirtti")
        
        # Aktiflik
        active_ratio = (stats['active_count'] / stats['total_scanned']) * 100
        table.add_row("⚡ Aktiflik (Repo > 0)", f"%{active_ratio:.1f}", f"{stats['active_count']}/{stats['total_scanned']}")
        
        console.print(table)
        console.print()

    def fetch_activity(self, username, days=30):
        """FAZ 4.1: Kullanıcının son aktivitelerini çeker (Atom feed kullanarak)."""
        import xml.etree.ElementTree as ET
        from datetime import datetime, timedelta
        
        url = f"https://github.com/{username}.atom"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
                
            # Parse XML
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            entries = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for entry in root.findall('atom:entry', ns):
                title_elem = entry.find('atom:title', ns)
                published_elem = entry.find('atom:published', ns)
                link_elem = entry.find('atom:link', ns)
                
                if title_elem is None or published_elem is None:
                    continue
                    
                title = title_elem.text
                published_str = published_elem.text
                link = link_elem.get('href') if link_elem is not None else ""
                
                # Parse date
                try:
                    # GitHub uses "YYYY-MM-DD HH:MM:SS UTC" format
                    from datetime import datetime
                    published = datetime.strptime(published_str, '%Y-%m-%d %H:%M:%S %Z')
                except:
                    try:
                        # Fallback to ISO format
                        published = datetime.fromisoformat(published_str.replace('Z', '+00:00'))  
                        published_local = published.replace(tzinfo=None)
                    except:
                        continue
                else:
                    published_local = published
                    
                if published_local < cutoff_date:
                    continue
                    
                # Classify event type (based on actual GitHub feed titles)
                event_type = "other"
                title_lower = title.lower()
                if "starred" in title_lower:
                    event_type = "star"
                elif "pushed" in title_lower:  # GitHub uses "pushed", not "pushed to"
                    event_type = "push"
                elif "forked" in title_lower:
                    event_type = "fork"
                elif "opened an issue" in title_lower or "issue" in title_lower:
                    event_type = "issue"
                elif "pull request" in title_lower or "merged" in title_lower or "pr" in title_lower:
                    event_type = "pull_request"
                elif "created" in title_lower:
                    event_type = "created_repo"
                    
                entries.append({
                    'type': event_type,
                    'title': title,
                    'date': published_local,
                    'link': link
                })
                
            return entries
            
        except Exception as e:
            return None

    def analyze_activity(self, events):
        """Aktivite verilerini analiz eder."""
        from collections import Counter
        
        if not events:
            return None
            
        analysis = {
            'total_events': len(events),
            'by_type': Counter([e['type'] for e in events]),
            'by_day': Counter([e['date'].strftime('%Y-%m-%d') for e in events]),
            'by_hour': Counter([e['date'].hour for e in events]),
            'first_event': min(events, key=lambda x: x['date'])['date'] if events else None,
            'last_event': max(events, key=lambda x: x['date'])['date'] if events else None,
        }
        
        # Most active day
        if analysis['by_day']:
            analysis['most_active_day'] = analysis['by_day'].most_common(1)[0]
        else:
            analysis['most_active_day'] = None
            
        # Most active hour
        if analysis['by_hour']:
            analysis['most_active_hour'] = analysis['by_hour'].most_common(1)[0]
        else:
            analysis['most_active_hour'] = None
            
        return analysis

    def print_activity(self, events, analysis, console):
        """Aktivite verilerini tablo ile gösterir."""
        if not events or not analysis:
            console.print("[yellow]⚠ Aktivite verisi bulunamadı veya son {days} günde aktivite yok.[/yellow]")
            return
            
        # Ana tablo - Aktivite türlerine göre
        activity_table = Table(title=f"📈 Son Aktiviteler (Toplam: {analysis['total_events']})", 
                              style="bold cyan", expand=True)
        activity_table.add_column("Aktivite Türü", style="cyan")
        activity_table.add_column("Adet", justify="right", style="yellow")
        
        event_emoji = {
            'star': '⭐',
            'push': '🚀',
            'fork': '🍴',
            'issue': '🐛',
            'pull_request': '🔀',
            'created_repo': '📦',
            'other': '📝'
        }
        
        for event_type, count in analysis['by_type'].most_common():
            emoji = event_emoji.get(event_type, '❓')
            activity_table.add_row(f"{emoji} {event_type.replace('_', ' ').title()}", str(count))
            
        console.print(activity_table)
        console.print()
        
        # İstatistikler tablosu
        stats_table = Table(title="📊 Aktivite İstatistikleri", style="bold magenta", 
                           show_header=False, expand=True)
        stats_table.add_column("Metrik", style="cyan")
        stats_table.add_column("Değer", style="white")
        
        if analysis['first_event']:
            stats_table.add_row("🕒 İlk Aktivite", analysis['first_event'].strftime('%Y-%m-%d %H:%M'))
        if analysis['last_event']:
            stats_table.add_row("🕐 Son Aktivite", analysis['last_event'].strftime('%Y-%m-%d %H:%M'))
        if analysis['most_active_day']:
            day, count = analysis['most_active_day']
            stats_table.add_row("📅 En Aktif Gün", f"{day} ({count} aktivite)")
        if analysis['most_active_hour']:
            hour, count = analysis['most_active_hour']
            stats_table.add_row("⏰ En Aktif Saat", f"{hour}:00 ({count} aktivite)")
            
        console.print(stats_table)
        console.print()

    # ==================== FAZ 4.2: CONTRIBUTION ANALİZİ ====================
    
    def fetch_contributions(self, username):
        """FAZ 4.2: Kullanıcının yıllık contribution sayısını ve contribution graph verilerini çeker."""
        import re
        
        # GitHub'ın contribution calendar sayfasını kullan
        url = f"https://github.com/users/{username}/contributions"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            contributions = {
                'yearly_total': 0,
                'current_streak': 0,
                'longest_streak': 0,
                'daily_contributions': []
            }
            
            # H2 elementinden yıllık toplam contribution sayısını bul
            # Format: "3,060 contributions in the last year"
            for h2 in soup.find_all('h2'):
                text = h2.get_text(strip=True)
                match = re.search(r'([\d,]+)\s*contributions?', text, re.IGNORECASE)
                if match:
                    contributions['yearly_total'] = int(match.group(1).replace(',', ''))
                    break
            
            # Tool-tip elementlerinden günlük contribution'ları topla (alternatif hesaplama)
            if contributions['yearly_total'] == 0:
                tooltips = soup.select('tool-tip')
                total_from_tips = 0
                for tt in tooltips:
                    text = tt.get_text(strip=True)
                    match = re.search(r'(\d+)\s+contribution', text)
                    if match:
                        total_from_tips += int(match.group(1))
                if total_from_tips > 0:
                    contributions['yearly_total'] = total_from_tips
            
            return contributions
            
        except Exception as e:
            return None
    
    def fetch_contribution_repos(self, username, events=None):
        """FAZ 4.2: En aktif olduğu repo'ları belirler (push eventlerinden)."""
        from collections import Counter
        
        if events is None:
            # Eğer events verilmediyse, fetch_activity ile çek (daha uzun bir periyod için)
            events = self.fetch_activity(username, days=365)
            
        if not events:
            return []
            
        # Push eventlerinden repo isimlerini çıkar
        repo_counts = Counter()
        
        for event in events:
            if event['type'] == 'push' and event.get('link'):
                # GitHub atom feed linki: https://github.com/user/repo/...
                link = event['link']
                parts = link.replace('https://github.com/', '').split('/')
                if len(parts) >= 2:
                    repo_name = f"{parts[0]}/{parts[1]}"
                    repo_counts[repo_name] += 1
        
        # En aktif repoları döndür
        return repo_counts.most_common(10)
    
    def fetch_pr_stats(self, username):
        """FAZ 4.2: Kullanıcının Pull Request istatistiklerini çeker."""
        import re
        
        stats = {
            'total_prs': 0,
            'open_prs': 0,
            'closed_prs': 0,
            'merged_prs': 0
        }
        
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        
        try:
            # Toplam PR sayısı
            total_url = f"https://github.com/search?q=author:{username}+is:pr&type=issues"
            response = requests.get(total_url, headers=headers, timeout=10)
            if response.status_code == 200:
                text = response.text
                # "XX results" formatını bul
                match = re.search(r'([\d,]+)\s+results?', text, re.IGNORECASE)
                if match:
                    stats['total_prs'] = int(match.group(1).replace(',', ''))
            
            time.sleep(0.3)
            
            # Open PR sayısı
            open_url = f"https://github.com/search?q=author:{username}+is:pr+is:open&type=issues"
            response = requests.get(open_url, headers=headers, timeout=10)
            if response.status_code == 200:
                match = re.search(r'([\d,]+)\s+results?', response.text, re.IGNORECASE)
                if match:
                    stats['open_prs'] = int(match.group(1).replace(',', ''))
            
            time.sleep(0.3)
            
            # Merged PR sayısı
            merged_url = f"https://github.com/search?q=author:{username}+is:pr+is:merged&type=issues"
            response = requests.get(merged_url, headers=headers, timeout=10)
            if response.status_code == 200:
                match = re.search(r'([\d,]+)\s+results?', response.text, re.IGNORECASE)
                if match:
                    stats['merged_prs'] = int(match.group(1).replace(',', ''))
            
            # Closed = Total - Open (veya merged + unmerged closed)
            stats['closed_prs'] = stats['total_prs'] - stats['open_prs']
                
            return stats
            
        except Exception as e:
            return stats
    
    def fetch_issue_stats(self, username):
        """FAZ 4.2: Kullanıcının Issue istatistiklerini çeker."""
        import re
        
        stats = {
            'total_issues': 0,
            'open_issues': 0,
            'closed_issues': 0
        }
        
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        
        try:
            # Toplam Issue sayısı (PR dahil değil, sadece issue)
            total_url = f"https://github.com/search?q=author:{username}+is:issue&type=issues"
            response = requests.get(total_url, headers=headers, timeout=10)
            if response.status_code == 200:
                match = re.search(r'([\d,]+)\s+results?', response.text, re.IGNORECASE)
                if match:
                    stats['total_issues'] = int(match.group(1).replace(',', ''))
            
            time.sleep(0.3)
            
            # Open Issue sayısı
            open_url = f"https://github.com/search?q=author:{username}+is:issue+is:open&type=issues"
            response = requests.get(open_url, headers=headers, timeout=10)
            if response.status_code == 200:
                match = re.search(r'([\d,]+)\s+results?', response.text, re.IGNORECASE)
                if match:
                    stats['open_issues'] = int(match.group(1).replace(',', ''))
            
            # Closed = Total - Open
            stats['closed_issues'] = stats['total_issues'] - stats['open_issues']
            
            return stats
            
        except Exception as e:
            return stats
    
    def analyze_contributions(self, username, activity_events=None):
        """FAZ 4.2: Tüm contribution analizini bir araya getirir."""
        console = Console()
        console.print(f"[yellow][*] {username} için contribution analizi yapılıyor...[/yellow]")
        
        analysis = {
            'contributions': None,
            'active_repos': [],
            'pr_stats': None,
            'issue_stats': None
        }
        
        # 1. Yıllık contribution sayısı
        analysis['contributions'] = self.fetch_contributions(username)
        time.sleep(0.5)
        
        # 2. En aktif olduğu repolar (Push eventlerinden)
        analysis['active_repos'] = self.fetch_contribution_repos(username, activity_events)
        time.sleep(0.5)
        
        # 3. PR istatistikleri
        analysis['pr_stats'] = self.fetch_pr_stats(username)
        time.sleep(0.5)
        
        # 4. Issue istatistikleri
        analysis['issue_stats'] = self.fetch_issue_stats(username)
        
        return analysis
    
    def print_contributions(self, analysis, console):
        """FAZ 4.2: Contribution analiz sonuçlarını tablo olarak gösterir."""
        if not analysis:
            console.print("[yellow]⚠ Contribution verisi alınamadı.[/yellow]")
            return
            
        # Ana tablo - Genel Contribution Özeti
        main_table = Table(title="📊 Contribution Analizi", style="bold green", expand=True)
        main_table.add_column("Kategori", style="cyan")
        main_table.add_column("Değer", style="yellow")
        main_table.add_column("Detay", style="white")
        
        # Yıllık contribution
        if analysis['contributions']:
            yearly = analysis['contributions'].get('yearly_total', 0)
            main_table.add_row(
                "📅 Yıllık Contributions", 
                str(yearly), 
                "Son 1 yıl"
            )
        
        # PR istatistikleri
        if analysis['pr_stats']:
            pr = analysis['pr_stats']
            main_table.add_row(
                "🔀 Pull Requests", 
                f"{pr['total_prs']}", 
                f"Açık: {pr['open_prs']} | Kapalı: {pr['closed_prs']} | Merged: {pr['merged_prs']}"
            )
        
        # Issue istatistikleri
        if analysis['issue_stats']:
            iss = analysis['issue_stats']
            main_table.add_row(
                "🐛 Issues", 
                f"{iss['total_issues']}", 
                f"Açık: {iss['open_issues']} | Kapalı: {iss['closed_issues']}"
            )
        
        console.print(main_table)
        console.print()
        
        # En aktif repolar tablosu
        if analysis['active_repos']:
            repo_table = Table(title="🔥 En Aktif Olduğu Repolar (Push Sayısına Göre)", style="bold magenta")
            repo_table.add_column("#", style="dim", width=3)
            repo_table.add_column("Repository", style="cyan")
            repo_table.add_column("Push Sayısı", style="yellow", justify="right")
            
            for idx, (repo, count) in enumerate(analysis['active_repos'][:10], 1):
                repo_table.add_row(str(idx), repo, str(count))
            
            console.print(repo_table)
            console.print()
            console.print(repo_table)
            console.print()

    # ==================== FAZ 5.1: ORGANIZASYON DESTEĞİ ====================

    def fetch_organizations(self, username):
        """FAZ 5.1: Kullanıcının üye olduğu organizasyonları çeker."""
        url = f"https://github.com/{username}"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            orgs = []
            
            # Organizasyonlar genellikle sol sidebar'da
            org_links = soup.select('a.avatar-group-item')
            if not org_links:
                org_links = soup.select('a[data-hovercard-type="organization"]')
            
            for link in org_links:
                org_name = link.get('aria-label')
                href = link.get('href')
                if not href: continue
                
                org_url = "https://github.com" + href
                
                # İsim boşsa href'ten çıkar
                if not org_name:
                    org_name = href.strip("/")
                
                orgs.append({
                    'name': org_name,
                    'url': org_url,
                    'username': org_name.replace(" ", "-").lower() # URL friendly name approx
                })
            return orgs
        except Exception as e:
            return []

    def fetch_org_details(self, org_name):
        """FAZ 5.1: Organizasyon detaylarını çeker."""
        url = f"https://github.com/{org_name}"
        info = {}
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # İsim (genellikle h1 içinde)
            name_tag = soup.select_one('h1')
            info['title'] = name_tag.get_text(strip=True) if name_tag else org_name
            
            # Açıklama
            desc_tag = soup.select_one('div.org-description')
            if not desc_tag:
                 # Bazen meta tag'de olabilir
                 desc_tag = soup.select_one('meta[name="description"]')
                 info['description'] = desc_tag.get('content') if desc_tag else "-"
            else:
                 info['description'] = desc_tag.get_text(strip=True)

            return info
        except:
            return None

    def fetch_org_members(self, org_name, limit=10):
        """FAZ 5.1: Organizasyonun public üyelerini çeker."""
        url = f"https://github.com/orgs/{org_name}/people"
        members = []
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            # Üye listesi
            # Eski selector: li.table-list-item.member-list-item
            # Yeni/Alternatif: div.d-table > div.d-table-row
            
            member_links = soup.select('li.table-list-item.member-list-item a.d-inline-block')
            if not member_links:
                 # Genel bir arama yap (Layout-main içinde)
                 main_layout = soup.select_one('div.Layout-main')
                 if main_layout:
                     member_links = main_layout.select('a[data-hovercard-type="user"]')
            
            for link in member_links:
                if len(members) >= limit: break
                
                href = link.get('href')
                if href:
                    m_name = href.strip("/")
                    if m_name not in members: # Tekrarı önle
                        members.append(m_name)
            
            return members
        except:
            return []

    def fetch_org_teams(self, org_name):
        """FAZ 5.2: Organizasyonun public takımlarını çeker."""
        url = f"https://github.com/orgs/{org_name}/teams"
        teams = []
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Takım linklerini bul
            team_links = soup.select('a[href*="/teams/"]')
            
            for link in team_links:
                name = link.get_text(strip=True)
                href = link.get('href')
                
                # Link kontrolü: /orgs/ORGNAME/teams/TEAMNAME formatında olmalı
                if href and f"/orgs/{org_name}/teams/" in href:
                     # Sadece ana takım linkini al (members, repositories vb. alt linkleri ele)
                     if not href.endswith("/members") and not href.endswith("/repositories"):
                         if name and name not in teams:
                             teams.append(name)
            return teams
        except:
            return []

    def print_organizations(self, orgs, console):
        """Organizasyonları listeler."""
        if not orgs:
            console.print("[yellow]⚠ Kullanıcının public organizasyonu bulunamadı.[/yellow]")
            return

        table = Table(title=f"🏢 Organizasyonlar ({len(orgs)})", style="bold cyan")
        table.add_column("Organizasyon", style="white")
        table.add_column("Detaylar", style="green")
        table.add_column("Takımlar", style="magenta")
        table.add_column("Üyeler (İlk 10)", style="yellow")
        
        for org in orgs:
            desc = org.get('details', {}).get('description', '-')
            if len(desc) > 50: desc = desc[:47] + "..."
            
            members = org.get('members', [])
            members_str = ", ".join(members) if members else "-"

            teams = org.get('teams', [])
            teams_str = ", ".join(teams) if teams else "0"
            if len(teams) > 5:
                teams_str = f"{len(teams)} Takım ({', '.join(teams[:3])}...)"
            elif len(teams) == 0:
                teams_str = "-"
            
            table.add_row(
                org['name'],
                desc,
                teams_str,
                members_str
            )
            
        console.print(table)
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
        compare_user = options.get("COMPARE")
        network_analysis_opt = options.get("NETWORK_ANALYSIS")
        activity_opt = options.get("ACTIVITY")
        activity_days = int(options.get("DAYS"))
        contributions_opt = options.get("CONTRIBUTIONS")
        orgs_opt = options.get("ORGS")  # FAZ 5.1
        
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
            
        # Ağ Analizi (FAZ 3.2) - Followers üzerinde
        network_stats = None
        if network_analysis_opt == "True":
            # Limit parametresini kullanalım ama çok yüksekse uyaralım veya max 50 ile sınırlayalım
            analysis_limit = limit if limit < 50 else 20 
            if limit > 50:
                 console.print(f"[yellow][!] Ağ analizi için limit otomatik olarak {analysis_limit} ile sınırlandırıldı (Hız limiti nedeniyle).[/yellow]")
            network_stats = self.analyze_network(followers, limit=analysis_limit)
            self.print_network_analysis(network_stats, console)

        # Aktivite Takibi (FAZ 4.1)
        activity_events = None
        activity_analysis = None
        if activity_opt == "True":
            activity_events = self.fetch_activity(target_user, days=activity_days)
            if activity_events:
                activity_analysis = self.analyze_activity(activity_events)
                self.print_activity(activity_events, activity_analysis, console)
            else:
                console.print(f"[yellow]⚠ Son {activity_days} günlük aktivite verisi alınamadı.[/yellow]")

        # Contribution Analizi (FAZ 4.2)
        contribution_analysis = None
        if contributions_opt == "True":
            contribution_analysis = self.analyze_contributions(target_user, activity_events)
            self.print_contributions(contribution_analysis, console)

        # Organizasyon Analizi (FAZ 5.1)
        orgs_data = []
        if orgs_opt == "True":
            orgs_data = self.fetch_organizations(target_user)
            if orgs_data:
                console.print(f"[yellow][*] {len(orgs_data)} organizasyon bulundu. Detaylar çekiliyor...[/yellow]")
                with console.status("[bold green]Organizasyon detayları taranıyor...") as status:
                    for org in orgs_data:
                        # İsimden username'i tahmin etmeye çalış (URL için)
                        # Genellikle url'in son kısmı
                        org_slug = org['url'].split('/')[-1]
                        
                        details = self.fetch_org_details(org_slug)
                        org['details'] = details
                        
                        members = self.fetch_org_members(org_slug)
                        org['members'] = members

                        teams = self.fetch_org_teams(org_slug)
                        org['teams'] = teams
                        
                        time.sleep(0.5) 
                
                self.print_organizations(orgs_data, console)

        # Dosyaya Kaydet
        if output_file:
            self.save_to_file(target_user, following, followers, output_file, console, profile_info if show_profile == "True" else None, stats, repos, repo_analysis, rel_analysis, network_stats, activity_analysis, contribution_analysis, orgs_data)

        # Karşılaştırma Analizi (Varsa) - Dosyaya append yaptığı için save_to_file'dan sonra çağrılmalı
        if compare_user:
            compare_user_target = self.get_username(compare_user)
            if compare_user_target.lower() != target_user.lower():
                self.compare_users(target_user, followers, following, compare_user_target, console, output_file)
            else:
                 console.print("[red][!] Karşılaştırılacak kullanıcı hedef kullanıcı ile aynı olamaz.[/red]")

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

    def save_to_file(self, target_user, following, followers, filename, console, profile_info=None, stats=None, repos=None, repo_analysis=None, rel_analysis=None, network_stats=None, activity_analysis=None, contribution_analysis=None, orgs_data=None):
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

                if network_stats:
                     f.write("AG ANALIZI (FAZ 3.2):\n")
                     f.write(f"- Taranan Kisi: {network_stats['total_scanned']}\n")
                     f.write(f"- Aktif Kullanici Orani: {network_stats['active_count']}/{network_stats['total_scanned']}\n")
                     f.write("En Yaygin Lokasyonlar:\n")
                     for k,v in network_stats['top_locations']:
                         f.write(f"  - {k}: {v}\n")
                     f.write("En Yaygin Sirketler:\n")
                     for k,v in network_stats['top_companies']:
                         f.write(f"  - {k}: {v}\n")
                     f.write("\n" + "-"*40 + "\n\n")

                if activity_analysis:
                     f.write("AKTIVITE TAKIBI (FAZ 4.1):\n")
                     f.write(f"- Toplam Aktivite: {activity_analysis['total_events']}\n")
                     f.write("\nAktivite Turleri:\n")
                     for event_type, count in activity_analysis['by_type'].most_common():
                         f.write(f"  - {event_type.replace('_', ' ').title()}: {count}\n")
                     if activity_analysis['most_active_day']:
                         day, count = activity_analysis['most_active_day']
                         f.write(f"\nEn Aktif Gun: {day} ({count} aktivite)\n")
                     if activity_analysis['most_active_hour']:
                         hour, count = activity_analysis['most_active_hour']
                         f.write(f"En Aktif Saat: {hour}:00 ({count} aktivite)\n")
                     f.write("\n" + "-"*40 + "\n\n")

                # FAZ 4.2: Contribution Analizi
                if contribution_analysis:
                     f.write("CONTRIBUTION ANALIZI (FAZ 4.2):\n")
                     
                     if contribution_analysis.get('contributions'):
                         yearly = contribution_analysis['contributions'].get('yearly_total', 0)
                         f.write(f"- Yillik Contribution: {yearly}\n")
                     
                     if contribution_analysis.get('pr_stats'):
                         pr = contribution_analysis['pr_stats']
                         f.write(f"\nPull Request Istatistikleri:\n")
                         f.write(f"  - Toplam PR: {pr['total_prs']}\n")
                         f.write(f"  - Acik PR: {pr['open_prs']}\n")
                         f.write(f"  - Kapali PR: {pr['closed_prs']}\n")
                         f.write(f"  - Merged PR: {pr['merged_prs']}\n")
                     
                     if contribution_analysis.get('issue_stats'):
                         iss = contribution_analysis['issue_stats']
                         f.write(f"\nIssue Istatistikleri:\n")
                         f.write(f"  - Toplam Issue: {iss['total_issues']}\n")
                         f.write(f"  - Acik Issue: {iss['open_issues']}\n")
                         f.write(f"  - Kapali Issue: {iss['closed_issues']}\n")
                     
                     if contribution_analysis.get('active_repos'):
                         f.write(f"\nEn Aktif Repolar (Push Sayisina Gore):\n")
                         for idx, (repo, count) in enumerate(contribution_analysis['active_repos'][:10], 1):
                             f.write(f"  {idx}. {repo}: {count} push\n")
                     
                     f.write("\n" + "-"*40 + "\n\n")

                     f.write("\n" + "-"*40 + "\n\n")

                if orgs_data:
                    f.write("ORGANIZASYONLAR (FAZ 5.1):\n")
                    for org in orgs_data:
                        f.write(f"- {org['name']} ({org['url']})\n")
                        desc = org.get('details', {}).get('description', '-')
                        f.write(f"  Aciklama: {desc}\n")
                        teams = org.get('teams', [])
                        f.write(f"  Takimlar ({len(teams)}): {', '.join(teams)}\n")
                        members = org.get('members', [])
                        f.write(f"  Uyeler ({len(members)}): {', '.join(members)}\n")
                        f.write("  ---\n")
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
