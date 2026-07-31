# Quick Start / Hızlı Başlangıç

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

Get Mah Framework running and complete a first useful workflow in a few minutes.

### Requirements

* Python **3.8+** (3.10+ recommended)
* `pip` and a virtual environment
* macOS, Linux, or Windows (WSL recommended on Windows)

### Install

```bash
git clone https://github.com/MahmutP/mah-framework.git
cd mah-framework
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### First Launch

```bash
python3 main.py
```

Startup flags:

| Flag | Meaning |
| ---- | ------- |
| `-q` | Quiet mode (skip banner) |
| `-r file.rc` | Run a resource file after start |
| `-x "cmd1; cmd2"` | Run commands then continue / exit flow |

Examples:

```bash
python3 main.py -q
python3 main.py -x "show modules; help"
python3 main.py -q -r my_macro.rc
```

### Console Basics

| Key / Command | Action |
| ------------- | ------ |
| `Tab` | Auto-complete |
| `Ctrl+R` | Reverse history search |
| `Up` / `Down` | Previous commands |
| `help` / `?` | List commands |
| `help <cmd>` | Details for one command |
| `exit` / `quit` | Leave the framework |

Command history is stored in `.mah_history` in the project root.

### Essential Workflow

Typical Metasploit-like loop:

```text
search <keyword>
use <module/path>
show options
set <OPTION> <value>
run
back
```

Example — port scan:

```bash
search port
use auxiliary/scanner/port_scanner
set RHOST 192.168.1.1
set RPORTS 20-80,443,8080
run
```

Example — hash helper:

```bash
use example/hash_generator
set TEXT hello
run
```

### Useful Discovery Commands

```bash
show modules              # Full module list
search scanner            # Filter by keyword
info                      # Details of selected module
show options              # Options of selected module
```

### Sessions (After a Payload Connects)

```bash
sessions -l               # List
sessions -i 1             # Interact
sessions -k 1             # Kill
sessions -g               # Group by host
```

For Chimera agents, see [CHIMERA_USER_GUIDE.md](CHIMERA_USER_GUIDE.md).

### Automate With Macros

```bash
record start
# ... run commands ...
record stop my_macro
resource my_macro.rc
```

Details: [usage_guide_macro.md](usage_guide_macro.md).

### Aliases

```bash
alias add s search
alias list
alias remove s
```

Aliases persist in `config/aliases.json`.

### Plugins Snapshot

```bash
plugins list
plugins enable "Audit Logger"
plugins info "Audit Logger"
```

Details: [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md).

### Update & Maintenance

```bash
checkupdate                 # Check for updates
checkupdate --apply         # Apply update
./pycache_sil.sh -y         # Clean __pycache__ and old logs
```

### Next Steps

* [COMMANDS.md](COMMANDS.md) — full command reference
* [MODULES.md](MODULES.md) — module catalog
* [PAYLOADS.md](PAYLOADS.md) — payload generation
* [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — write your own modules

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Mah Framework'ü kurup birkaç dakikada ilk iş akışını tamamlayın.

### Gereksinimler

* Python **3.8+** (önerilen: 3.10+)
* `pip` ve sanal ortam
* macOS, Linux veya Windows (Windows'ta WSL önerilir)

### Kurulum

```bash
git clone https://github.com/MahmutP/mah-framework.git
cd mah-framework
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### İlk Çalıştırma

```bash
python3 main.py
```

Başlangıç bayrakları:

| Bayrak | Anlamı |
| ------ | ------ |
| `-q` | Sessiz mod (banner yok) |
| `-r dosya.rc` | Açılışta resource dosyası çalıştır |
| `-x "cmd1; cmd2"` | Komutları doğrudan çalıştır |

Örnekler:

```bash
python3 main.py -q
python3 main.py -x "show modules; help"
python3 main.py -q -r makrom.rc
```

### Konsol Temelleri

| Tuş / Komut | İşlev |
| ----------- | ----- |
| `Tab` | Otomatik tamamlama |
| `Ctrl+R` | Geçmişte ters arama |
| `Yukarı` / `Aşağı` | Önceki komutlar |
| `help` / `?` | Komut listesi |
| `help <komut>` | Tek komut detayı |
| `exit` / `quit` | Çıkış |

Komut geçmişi proje kökündeki `.mah_history` dosyasında saklanır.

### Temel İş Akışı

Metasploit benzeri döngü:

```text
search <anahtar>
use <modül/yolu>
show options
set <SEÇENEK> <değer>
run
back
```

Örnek — port tarama:

```bash
search port
use auxiliary/scanner/port_scanner
set RHOST 192.168.1.1
set RPORTS 20-80,443,8080
run
```

Örnek — hash yardımcısı:

```bash
use example/hash_generator
set TEXT merhaba
run
```

### Keşif Komutları

```bash
show modules              # Tüm modüller
search scanner            # Anahtar kelime ile ara
info                      # Seçili modül detayı
show options              # Seçili modül seçenekleri
```

### Oturumlar (Payload Bağlandığında)

```bash
sessions -l               # Listele
sessions -i 1             # Etkileşim
sessions -k 1             # Sonlandır
sessions -g               # Hedefe göre grupla
```

Chimera ajanları için: [CHIMERA_USER_GUIDE.md](CHIMERA_USER_GUIDE.md).

### Makro ile Otomasyon

```bash
record start
# ... komutları çalıştır ...
record stop makrom
resource makrom.rc
```

Detay: [usage_guide_macro.md](usage_guide_macro.md).

### Alias'lar

```bash
alias add s search
alias list
alias remove s
```

Alias'lar `config/aliases.json` içinde kalıcıdır.

### Plugin Özeti

```bash
plugins list
plugins enable "Audit Logger"
plugins info "Audit Logger"
```

Detay: [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md).

### Güncelleme ve Bakım

```bash
checkupdate                 # Güncelleme kontrolü
checkupdate --apply         # Güncellemeyi uygula
./pycache_sil.sh -y         # __pycache__ ve eski logları temizle
```

### Sonraki Adımlar

* [COMMANDS.md](COMMANDS.md) — tam komut referansı
* [MODULES.md](MODULES.md) — modül kataloğu
* [PAYLOADS.md](PAYLOADS.md) — payload üretimi
* [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — kendi modülünüzü yazın
