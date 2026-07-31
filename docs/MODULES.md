# Modules Catalog / Modül Kataloğu

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

Catalog of built-in modules under `modules/`. Paths are what you pass to `use`.

Discover at runtime:

```bash
show modules
search <keyword>
info
```

### Auxiliary — Analyze

| Path | Description |
| ---- | ----------- |
| `auxiliary/analyze/banner_grabber` | Grab service banners (version/software) |
| `auxiliary/analyze/http_headers` | Fetch and analyze HTTP response headers |

### Auxiliary — Forensics

| Path | Description | Docs |
| ---- | ----------- | ---- |
| `auxiliary/forensics/metadata_extractor` | Extract EXIF / image metadata | [METADATA_MODULES.md](METADATA_MODULES.md) |
| `auxiliary/forensics/metadata_cleaner` | Strip image metadata | [METADATA_MODULES.md](METADATA_MODULES.md) |

### Auxiliary — OS

| Path | Description |
| ---- | ----------- |
| `auxiliary/os/process_manager` | Local process listing / management helpers |
| `auxiliary/os/service_manager` | Local service management helpers |

### Auxiliary — Recon

| Path | Description | Docs |
| ---- | ----------- | ---- |
| `auxiliary/recon/dns_enum` | DNS enumeration |
| `auxiliary/recon/email_harvester` | Collect emails from public sources |
| `auxiliary/recon/github_tracker` | GitHub profile / follower recon | [GITHUB_TRACKER.md](GITHUB_TRACKER.md) |
| `auxiliary/recon/subdomain_finder` | Subdomain discovery (DNS bruteforce) |
| `auxiliary/recon/whois_lookup` | WHOIS lookup |

### Auxiliary — Scanner

| Path | Description |
| ---- | ----------- |
| `auxiliary/scanner/port_scanner` | TCP port scanner (`RHOST`, `RPORTS`) |
| `auxiliary/scanner/http_dir_buster` | Web directory / file bruteforce |
| `auxiliary/scanner/service_version_detector` | Probe service versions |
| `auxiliary/scanner/ssh_brute` | SSH credential bruteforce |
| `auxiliary/scanner/smb_enum` | SMB enumeration |
| `auxiliary/scanner/ssl_checker` | TLS/SSL certificate checks |
| `auxiliary/scanner/whatsmyip` | External IP discovery |
| `auxiliary/scanner/ftp/vsftpd_234_scanner` | Detect VSFTPD 2.3.4 backdoor |

Wordlists live under `config/wordlists/` (dirs, subdomains, passwords).

### Auxiliary — Utils

| Path | Description |
| ---- | ----------- |
| `auxiliary/utils/hash_cracker` | Offline hash cracking helper |
| `auxiliary/utils/web_crawler` | Simple web crawler |

### Exploit

| Path | Description |
| ---- | ----------- |
| `exploit/ftp/vsftpd_234_backdoor` | VSFTPD 2.3.4 backdoor exploit |
| `exploit/multi/handler` | Unified multi-payload listener |

Handler example:

```bash
use exploit/multi/handler
set PAYLOAD payloads/python/chimera/generate
set LHOST 192.168.1.10
set LPORT 4444
set BACKGROUND false
run
```

### Example

| Path | Description |
| ---- | ----------- |
| `example/hash_generator` | Demo hashing module |
| `example/toplama` | Demo addition module |
| `example/cikarma` | Demo subtraction module |

Useful as templates while reading [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

### Payloads

Generate modules typically end with `/generate`; matching listeners with `/handler` (or `/server` for HTTP).

| Family | Paths | Notes |
| ------ | ----- | ----- |
| Python reverse/bind | `payloads/python/shell_reverse_tcp`, `shell_bind_tcp` | One-liner style |
| Python mahpreter | `payloads/python/mahpreter/reverse_tcp` | Agent features + encode |
| **Chimera** | `payloads/python/chimera` | Encrypted agent — [CHIMERA_USER_GUIDE.md](CHIMERA_USER_GUIDE.md) |
| PHP / JSP / ASPX | `payloads/php/reverse_tcp`, `java/jsp_reverse_tcp`, `windows/aspx_reverse_tcp` | Web shells |
| Windows | `powershell_reverse_tcp`, `hta_reverse_tcp` | PS / HTA |
| Linux | `linux/bash_reverse_tcp` | `/dev/tcp` |
| Advanced C2-ish | `mahpreter/reverse_http`, `mahpreter/reverse_dns` | HTTP / DNS channels |

Full usage: [PAYLOADS.md](PAYLOADS.md).

### Post-Exploitation

| Path | Description |
| ---- | ----------- |
| `post/gather/system_info` | Collect system information |
| `post/gather/credentials` | Credential gathering helpers |
| `post/persist/cron_backdoor` | Cron-based persistence (Linux) |
| `post/pivot/socks_proxy` | SOCKS pivot helper |
| `post/chimera/example_post` | Example Chimera post module |

Chimera in-memory posts: [chimera_module_loading.md](chimera_module_loading.md).

### Common Option Conventions

| Option | Meaning |
| ------ | ------- |
| `RHOST` / `RHOSTS` | Remote target host(s) |
| `RPORT` / `RPORTS` | Remote port(s) / ranges |
| `LHOST` | Local / attacker listen host |
| `LPORT` | Local / attacker listen port |
| `THREADS` | Concurrency |
| `TIMEOUT` | Network timeout |
| `WORDLIST` / `FILE` | Input file path |

Always run `show options` after `use` — modules define their own set.

### Adding Modules

Place a new `.py` under the right category folder, inherit `BaseModule`, then `reload` or restart. See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md). Remote installs: [REPO_AND_DOWNLOAD.md](REPO_AND_DOWNLOAD.md).

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

`modules/` altındaki yerleşik modüllerin kataloğu. `use` komutuna verdiğiniz yol buradaki path'tir.

Çalışma anında keşif:

```bash
show modules
search <anahtar>
info
```

### Auxiliary — Analyze

| Yol | Açıklama |
| --- | -------- |
| `auxiliary/analyze/banner_grabber` | Servis banner (sürüm/yazılım) çekme |
| `auxiliary/analyze/http_headers` | HTTP başlıklarını çekme ve analiz |

### Auxiliary — Forensics

| Yol | Açıklama | Docs |
| --- | -------- | ---- |
| `auxiliary/forensics/metadata_extractor` | EXIF / görüntü meta verisi çıkarma | [METADATA_MODULES.md](METADATA_MODULES.md) |
| `auxiliary/forensics/metadata_cleaner` | Görüntü meta verisini temizleme | [METADATA_MODULES.md](METADATA_MODULES.md) |

### Auxiliary — OS

| Yol | Açıklama |
| --- | -------- |
| `auxiliary/os/process_manager` | Yerel süreç listeleme / yönetim |
| `auxiliary/os/service_manager` | Yerel servis yönetimi |

### Auxiliary — Recon

| Yol | Açıklama | Docs |
| --- | -------- | ---- |
| `auxiliary/recon/dns_enum` | DNS enumeration |
| `auxiliary/recon/email_harvester` | Genel kaynaklardan e-posta toplama |
| `auxiliary/recon/github_tracker` | GitHub profil / takipçi keşfi | [GITHUB_TRACKER.md](GITHUB_TRACKER.md) |
| `auxiliary/recon/subdomain_finder` | Subdomain keşfi (DNS bruteforce) |
| `auxiliary/recon/whois_lookup` | WHOIS sorgusu |

### Auxiliary — Scanner

| Yol | Açıklama |
| --- | -------- |
| `auxiliary/scanner/port_scanner` | TCP port tarayıcı (`RHOST`, `RPORTS`) |
| `auxiliary/scanner/http_dir_buster` | Web dizin / dosya bruteforce |
| `auxiliary/scanner/service_version_detector` | Servis sürüm tespiti |
| `auxiliary/scanner/ssh_brute` | SSH kimlik bilgisi bruteforce |
| `auxiliary/scanner/smb_enum` | SMB enumeration |
| `auxiliary/scanner/ssl_checker` | TLS/SSL sertifika kontrolü |
| `auxiliary/scanner/whatsmyip` | Dış IP öğrenme |
| `auxiliary/scanner/ftp/vsftpd_234_scanner` | VSFTPD 2.3.4 backdoor tespiti |

Wordlist'ler: `config/wordlists/`.

### Auxiliary — Utils

| Yol | Açıklama |
| --- | -------- |
| `auxiliary/utils/hash_cracker` | Offline hash kırma yardımcısı |
| `auxiliary/utils/web_crawler` | Basit web crawler |

### Exploit

| Yol | Açıklama |
| --- | -------- |
| `exploit/ftp/vsftpd_234_backdoor` | VSFTPD 2.3.4 backdoor exploit |
| `exploit/multi/handler` | Birleşik çoklu-payload dinleyici |

### Example

| Yol | Açıklama |
| --- | -------- |
| `example/hash_generator` | Demo hash modülü |
| `example/toplama` | Demo toplama |
| `example/cikarma` | Demo çıkarma |

Şablon için: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

### Payload'lar

Üretim modülleri genelde `/generate`, dinleyiciler `/handler` (HTTP için `/server`) ile biter. Aileler İngilizce tabloda; kullanım: [PAYLOADS.md](PAYLOADS.md). Chimera: [CHIMERA_USER_GUIDE.md](CHIMERA_USER_GUIDE.md).

### Post-Exploitation

| Yol | Açıklama |
| --- | -------- |
| `post/gather/system_info` | Sistem bilgisi toplama |
| `post/gather/credentials` | Kimlik bilgisi toplama |
| `post/persist/cron_backdoor` | Cron tabanlı kalıcılık (Linux) |
| `post/pivot/socks_proxy` | SOCKS pivot yardımcısı |
| `post/chimera/example_post` | Örnek Chimera post modülü |

Bellek içi Chimera post: [chimera_module_loading.md](chimera_module_loading.md).

### Yaygın Seçenek İsimleri

| Seçenek | Anlamı |
| ------- | ------ |
| `RHOST` / `RHOSTS` | Uzak hedef |
| `RPORT` / `RPORTS` | Uzak port / aralık |
| `LHOST` | Yerel dinleme adresi |
| `LPORT` | Yerel dinleme portu |
| `THREADS` | Paralellik |
| `TIMEOUT` | Ağ zaman aşımı |
| `WORDLIST` / `FILE` | Girdi dosyası |

`use` sonrası her zaman `show options` çalıştırın.

### Modül Ekleme

Doğru kategori altına `BaseModule` miras alan `.py` koyun; `reload` veya yeniden başlatın. Detay: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md). Uzaktan kurulum: [REPO_AND_DOWNLOAD.md](REPO_AND_DOWNLOAD.md).
