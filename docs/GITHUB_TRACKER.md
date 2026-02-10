# 🕵️ GitHub Tracker Module / GitHub Takip Modülü

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

**GitHub Tracker** is a powerful reconnaissance module designed to gather comprehensive intelligence on GitHub users. It goes beyond simple profile scraping to provide deep insights into repositories, relationships, and activity patterns.

### 🚀 Key Features

*   **📊 Comprehensive Profile Analysis:** Retrieves bio, location, company, social links, and key statistics (stars, forks, gists).
*   **📁 Repository Insights:** Lists public repositories with detailed stats (language, stars, forks, last update). Supports sorting and filtering.
*   **🔗 Relationship Mapping:**
    *   Identifies users who don't follow back.
    *   Finds mutual followers.
    *   Analyzes follower/following networks.
*   **📈 Activity Tracking:**
    *   Fetches recent public events (pushes, stars, issues).
    *   Visualizes contribution graphs (streaks, daily commits).
    *   Analyzes active hours and days.
*   **🏢 Organization Recon:** Lists public organization memberships and teams.
*   **💾 Multi-Format Reports:** Exports data to **HTML**, **JSON**, **CSV**, and **Markdown**.

### 💻 Usage

```bash
use auxiliary/recon/github_tracker
set TARGET <username>
run
```

#### Advanced Options

| Option         | Description                                        | Default         |
| :------------- | :------------------------------------------------- | :-------------- |
| `TARGET`       | Target GitHub username or URL.                     | (Required)      |
| `OUTPUT`       | Output file path (without extension).              | `github_report` |
| `FORMAT`       | Report format: `txt`, `json`, `csv`, `html`, `md`. | `txt`           |
| `LIMIT`        | Limit for lists (repos, followers).                | `50`            |
| `PROFILE_INFO` | Fetch profile details.                             | `True`          |
| `REPOS`        | Fetch repository list.                             | `True`          |
| `ACTIVITY`     | Fetch activity feed and stats.                     | `True`          |
| `ORGS`         | Fetch organization info.                           | `True`          |
| `COMPARE`      | Another username to compare with (for mutuals).    | `None`          |

### 📄 Example

```bash
mah > use auxiliary/recon/github_tracker
mah (github_tracker) > set TARGET torvalds
mah (github_tracker) > set FORMAT html
mah (github_tracker) > set ACTIVITY true
mah (github_tracker) > run
[*] Fetching data for torvalds...
[+] Report saved to github_report.html
```

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

**GitHub Tracker**, GitHub kullanıcıları hakkında kapsamlı istihbarat toplamak için tasarlanmış güçlü bir keşif modülüdür. Basit profil bilgilerinin ötesine geçerek depo analizleri, takipçi ilişkileri ve aktivite desenleri hakkında derinlemesine bilgi sağlar.

### 🚀 Temel Özellikler

*   **📊 Kapsamlı Profil Analizi:** Biyografi, konum, şirket, sosyal medya linkleri ve temel istatistikleri (yıldızlar, forklar, gistler) çeker.
*   **📁 Depo (Repository) Analizi:** Public repoları detaylı istatistiklerle (dil, yıldız, güncellenme tarihi) listeler. Sıralama ve filtrelemeyi destekler.
*   **🔗 İlişki Haritalama:**
    *   Sizi geri takip etmeyenleri bulur.
    *   Karşılıklı takipleşilen kişileri (mutuals) listeler.
    *   Takipçi/Takip edilen ağını analiz eder.
*   **📈 Aktivite Takibi:**
    *   Son public olayları (push, star, issue vb.) getirir.
    *   Katkı grafiklerini (contribution graph) ve serileri (streaks) görselleştirir.
    *   En aktif olunan saatleri ve günleri analiz eder.
*   **🏢 Organizasyon Keşfi:** Üye olunan public organizasyonları ve takımları listeler.
*   **💾 Çoklu Format Raporlama:** Verileri **HTML**, **JSON**, **CSV** ve **Markdown** formatlarında dışa aktarır.

### 💻 Kullanım

```bash
use auxiliary/recon/github_tracker
set TARGET <kullanici_adi>
run
```

#### Gelişmiş Seçenekler

| Seçenek        | Açıklama                                           | Varsayılan      |
| :------------- | :------------------------------------------------- | :-------------- |
| `TARGET`       | Hedef GitHub kullanıcı adı veya linki.             | (Zorunlu)       |
| `OUTPUT`       | Çıktı dosya yolu (uzantısız).                      | `github_report` |
| `FORMAT`       | Rapor formatı: `txt`, `json`, `csv`, `html`, `md`. | `txt`           |
| `LIMIT`        | Liste limiti (repo, takipçi vb. için).             | `50`            |
| `PROFILE_INFO` | Profil detaylarını çek.                            | `True`          |
| `REPOS`        | Repository listesini çek.                          | `True`          |
| `ACTIVITY`     | Aktivite ve katkı bilgilerini çek.                 | `True`          |
| `ORGS`         | Organizasyon bilgilerini çek.                      | `True`          |
| `COMPARE`      | Karşılaştırma yapılacak ikinci kullanıcı.          | `None`          |

### 📄 Örnek Senaryo

```bash
mah > use auxiliary/recon/github_tracker
mah (github_tracker) > set TARGET torvalds
mah (github_tracker) > set FORMAT html
mah (github_tracker) > set ACTIVITY true
mah (github_tracker) > run
[*] torvalds için veriler çekiliyor...
[+] Rapor github_report.html olarak kaydedildi.
```
