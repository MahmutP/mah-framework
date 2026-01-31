<div align="center">

# 🚀 Mah Framework

**A Powerful, Modular, and Extensible CLI Framework for Python.**
**Python ile Geliştirilmiş, Modüler ve Genişletilebilir CLI Çatısı**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green?style=for-the-badge)](LICENSE)
[![Maintenance](https://img.shields.io/badge/maintained-yes-brightgreen?style=for-the-badge)](https://github.com/MahmutP/mah-framework/graphs/commit-activity)

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

</div>

---

<a name="-english"></a>
## 🇬🇧 English

**Mah Framework** is a robust Command Line Interface (CLI) framework developed in Python. Designed with modern terminal tools like `rich` and `prompt_toolkit`, it powers the **mahpreter** project and offers a flexible infrastructure for easily adding your own modules and commands.

### ✨ Key Features

*   **🧩 Modular Architecture**: Easily extend functionality with a plug-and-play approach using `modules/` and `commands/` directories.
*   **🎨 Modern UI**: Beautiful, readable, and colorful terminal outputs powered by the `rich` library.
*   **🌈 Dynamic Banner**: Randomly generated, colorful ASCII banners using `pyfiglet` and `rich`, featuring a curated list of readable fonts.
*   **🧠 Intelligent Interaction**: Auto-completion, history navigation, and advanced input handling via `prompt_toolkit`.
*   **📝 Comprehensive Logging**: Powered by `loguru`, this system tracks application events, errors, and command executions in `config/logs/` with automatic rotation and retention.
*   **🛠️ System Utilities**: Includes tools for cache cleaning and log management (`pycache_sil.sh`).
*   **🌐 Network Ready**: Built-in support for libraries like `telnetlib3` and `psutil` for network and system management tasks.
*   **🛡️ Type Safe & Tested**: 100% type-annotated codebase with comprehensive unit tests (`pytest` & `mypy`), ensuring high reliability.

### 📊 Project Statistics
*   **16** Commands
*   **11+** Modules
*   **100%** Test Coverage (`20/20 passed`)
*   **Plugins System**, **Advanced Logging** & **Resource Script Support**

### � Development Note
The initial version of this project was developed entirely without AI assistance. The current version has been evolved using the **Antigravity IDE**, where AI enhanced the project based on the original codebase I wrote.

### �📦 Available Modules
Mah Framework comes with built-in modules across various categories:
*   **Exploit**: `vsftpd_234_backdoor` ...
*   **Auxiliary**: `scanner/port_scanner`, `scanner/http_dir_buster`, `scanner/vsftpd_234_scanner` ...
*   **Payloads**: `python/shell_reverse_tcp`, `python/mahpreter/reverse_tcp`, `linux/bash_reverse_tcp`, `mahpreter/reverse_dns`, `php/reverse_tcp` ...
*   **Handler**: `exploit/multi/handler` (Unified Listener)
*   **Example**: `hash_generator`, `toplama` ...
*   **Plugins**: `Audit Logger` (System Activity Monitoring) ...

### 📂 Project Structure

```text
mah-framework/
├── core/             # Core framework engine (managers, console, logger)
├── commands/         # Standard CLI commands (e.g., help, exit)
├── modules/          # External modules
├── plugins/          # 🔌 System plugins (NEW)
├── config/           # Configuration files and logs
│   └── logs/         # Application log files
├── main.py           # Application entry point
├── pycache_sil.sh    # Maintenance script (cache & log cleaner)
├── requirements.txt  # Python dependencies
└── README.md         # Documentation
```

### 🛠️ Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/MahmutP/mah-framework.git
    cd mah-framework
    ```

2.  **Create a Virtual Environment (Recommended)**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

### 💻 Usage

Start the framework by running the main script:

```bash
python main.py
```

**Startup Options:**
```bash
python main.py -q              # Quiet mode (no banner)
python main.py -r script.rc    # Run resource file at startup
python main.py -x "cmd1; cmd2"  # Execute commands directly
python main.py -q -r script.rc # Combine options
```

**Direct Command Execution (-x):**
Run commands without creating a file, separate multiple commands with semicolons:
```bash
python main.py -x "use example/hash_generator; set TEXT hello; run"
python main.py -q -x "banner; help"
```

**Port Scanner Usage:**
```bash
use auxiliary/scanner/port_scanner
set RHOST 192.168.1.1
set RPORTS 20-80,443,8080
run
```

**Directory Buster Usage (DirBuster):**
```bash
use auxiliary/scanner/http_dir_buster
set RHOST http://example.com
set WORDLIST config/wordlists/dirs/common.txt
run
```

Once inside the interactive shell, you can use built-in commands. Type `help` to see available commands or use `Tab` for auto-completion.

**Resource Files (.rc):**
Automate tasks using resource files, similar to Metasploit:
```bash
# From command line:
python main.py -r attack.rc

# Inside console:
mahmut > resource attack.rc
```

**Macro Recording:**
Record your commands to create a resource file automatically:
```bash
mahmut > record start           # Start recording
mahmut > show options           # Run commands...
mahmut > record stop my_macro   # Stop and save to my_macro.rc
```

**Maintenance:**
Use the included script to clean up `__pycache__` directories and old log files:
```bash
chmod +x pycache_sil.sh
./pycache_sil.sh      # Interactive mode (prompts for confirmation)
./pycache_sil.sh -y   # Auto-confirm all prompts (no interaction)
```

**Update Check:**
Regularly check for updates to get the latest features and security fixes:
```bash
mahmut > checkupdate
```
> ⚠️ **Important:** Run `checkupdate` periodically to ensure you're using the latest version.

### 🔌 Plugin System
Mah Framework supports plugins to extend functionality.
```bash
mahmut > plugins list
mahmut > plugins enable audit_logger
```

### 🤝 Contributing
Contributions are welcome! Please fork the repository, create a feature branch, and submit a Pull Request.

**Developers**: Check out the **[Developer Guide](docs/DEVELOPER_GUIDE.md)** to learn how to create your own modules!
**Users**: Read the **[Payloads Guide](docs/PAYLOADS.md)** to learn how to generate and use payloads.

### 🧪 Running Tests
Ensure high code quality by running the test suite:
```bash
pip install -r requirements.txt  # Install pytest and other deps
pytest                           # Run all tests
```

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

**Mah Framework**, Python ile geliştirilmiş, modüler yapıya sahip ve kolayca genişletilebilir bir Komut Satırı Arayüzü (CLI) çatısıdır. `rich` ve `prompt_toolkit` gibi modern araçlarla güçlendirilmiş bu yapı, **mahpreter** projesinin temelini oluşturur.

### ✨ Özellikler

*   **🧩 Modüler Mimari**: `modules/` ve `commands/` klasörleri sayesinde yeni özellikleri tak-çıkar mantığıyla kolayca ekleyin.
*   **🎨 Modern Arayüz**: `rich` kütüphanesi ile renklendirilmiş, okunaklı ve şık terminal çıktıları.
*   **🌈 Dinamik Banner**: `pyfiglet` ve `rich` kullanılarak oluşturulan, okunabilir fontlardan seçilen rastgele ve renkli ASCII bannerlar.
*   **🧠 Akıllı Etkileşim**: `prompt_toolkit` desteği ile otomatik tamamlama ve komut geçmişi özellikleri.
*   **📝 Kapsamlı Loglama**: `loguru` ile güçlendirilmiş bu sistem, uygulama olaylarını, hataları ve komutları `config/logs/` altında kayıt altına alır; otomatik rotasyon ve saklama özelliklerine sahiptir.
*   **🛠️ Sistem Araçları**: Gereksiz önbellek ve eski log dosyalarını temizlemek için hazır bakım aracı (`pycache_sil.sh`).
*   **🌐 Ağ Hazırlığı**: Ağ ve sistem yönetimi için `telnetlib3` ve `psutil` gibi kütüphane destekleri.
*   **🛡️ Tip Güvenli ve Test Edilmiş**: %100 tip güvenliği (Type Safety) ve kapsayıcı birim testleri (`pytest` & `mypy`) ile yüksek kararlılık sağlar.

### 📊 Proje İstatistikleri
*   **16** Komut
*   **11+** Modül
*   **%100** Test Kapsamı (`20/20 passed`)
*   **Plugin Sistemi**, **Gelişmiş Loglama** & **Resource Dosya Desteği**

### 💡 Geliştirme Notu
Bu projenin ilk hali tamamen yapay zeka desteği olmaksızın geliştirilmiştir. Şimdiki hali ise **Antigravity IDE** kullanılarak, benim yazdığım orijinal kodlar temel alınarak yapay zeka desteği ile geliştirilmiştir.

### 📦 Mevcut Modüller
Mah Framework, çeşitli kategorilerde yerleşik modüllerle gelir:
*   **Exploit**: `vsftpd_234_backdoor` ...
*   **Auxiliary**: `scanner/port_scanner`, `scanner/http_dir_buster`, `scanner/vsftpd_234_scanner` ...
*   **Payloads**: `python/shell_reverse_tcp`, `python/mahpreter/reverse_tcp`, `linux/bash_reverse_tcp`, `mahpreter/reverse_dns`, `php/reverse_tcp` ...
*   **Handler**: `exploit/multi/handler` (Unified Listener)
*   **Example**: `hash_generator`, `toplama` ...
*   **Plugins**: `Audit Logger` (Sistem Aktivite İzleme) ...

### 📂 Proje Yapısı

```text
mah-framework/
├── core/             # Framework çekirdek dosyaları (yöneticiler, konsol, logger)
├── commands/         # Standart CLI komutları (örn: help, exit)
├── modules/          # Harici modüller
├── plugins/          # 🔌 Sistem pluginleri (YENİ)
├── config/           # Ayar dosyaları ve loglar
│   └── logs/         # Uygulama logları
├── main.py           # Uygulamanın giriş noktası
├── pycache_sil.sh    # Bakım betiği (önbellek ve log temizleyici)
├── requirements.txt  # Gerekli Python kütüphaneleri
└── README.md         # Dokümantasyon
```

### 🛠️ Kurulum

1.  **Projeyi Klonlayın**
    ```bash
    git clone https://github.com/MahmutP/mah-framework.git
    cd mah-framework
    ```

2.  **Sanal Ortam Oluşturun (Önerilen)**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3.  **Kütüphaneleri Yükleyin**
    ```bash
    pip install -r requirements.txt
    ```

### 💻 Kullanım

Framework'ü başlatmak için `main.py` dosyasını çalıştırın:

```bash
python main.py
```

**Başlangıç Seçenekleri:**
```bash
python main.py -q              # Sessiz mod (banner gösterilmez)
python main.py -r script.rc    # Başlangıçta resource dosyası çalıştır
python main.py -x "cmd1; cmd2" # Komutları doğrudan çalıştır
python main.py -q -r script.rc # Seçenekleri birleştir
```

**Doğrudan Komut Çalıştırma (-x):**
Dosya oluşturmadan komutları çalıştırın, birden fazla komut için noktalı virgül kullanın:
```bash
python main.py -x "use example/hash_generator; set TEXT merhaba; run"
python main.py -q -x "banner; help"
```

**Port Tarayıcı Kullanımı:**
```bash
use auxiliary/scanner/port_scanner
set RHOST 192.168.1.1
set RPORTS 20-80,443,8080
run
```

**Dizin Tarayıcı Kullanımı (DirBuster):**
```bash
use auxiliary/scanner/http_dir_buster
set RHOST http://ornek-site.com
set WORDLIST config/wordlists/dirs/common.txt
run
```

Uygulama başladığında modern bir komut satırı sizi karşılayacaktır. `help` yazarak mevcut komutları listeleyebilir veya `Tab` tuşu ile otomatik tamamlamayı kullanabilirsiniz.

**Resource Dosyaları (.rc):**
Metasploit benzeri resource dosyaları ile görevleri otomatikleştirin:
```bash
# Komut satırından:
python main.py -r saldiri.rc

# Konsol içinden:
mahmut > resource saldiri.rc
```

**Makro Kayıt (Macro Recording):**
Yaptığınız işlemleri kaydedip otomatik olarak `.rc` dosyasına dönüştürün:
```bash
mahmut > record start           # Kaydı başlat
mahmut > show options           # Komutları çalıştır...
mahmut > record stop makrom     # Durdur ve makrom.rc olarak kaydet
```

**Bakım:**
Geliştirme artığı `__pycache__` klasörlerini ve eski log dosyalarını temizlemek için:
```bash
chmod +x pycache_sil.sh
./pycache_sil.sh      # Etkileşimli mod (onay sorar)
./pycache_sil.sh -y   # Tüm onayları otomatik kabul eder (etkileşimsiz)
```

**Güncelleme Kontrolü:**
En son özellikleri ve güvenlik yamalarını almak için düzenli olarak güncelleme kontrolü yapın:
```bash
mahmut > checkupdate
```
> ⚠️ **Önemli:** En son sürümü kullandığınızdan emin olmak için `checkupdate` komutunu düzenli olarak çalıştırın.

### 🔌 Plugin Sistemi
Mah Framework, işlevselliği artırmak için plugin desteği sunar.
```bash
mahmut > plugins list
mahmut > plugins enable audit_logger
```

### 🤝 Katkıda Bulunma
Bu proje açık kaynaklıdır ve katkılara açıktır. Lütfen projeyi fork'layın, yeni bir branch oluşturun ve Pull Request gönderin.

**Geliştiriciler**: Kendi modüllerinizi nasıl oluşturacağınızı öğrenmek için **[Geliştirici Rehberi](docs/DEVELOPER_GUIDE.md)** dosyasına göz atın!
**Kullanıcılar**: Payload oluşturma ve kullanma hakkında bilgi için **[Payloads Rehberi](docs/PAYLOADS.md)** dosyasına bakın.

### 🧪 Testleri Çalıştırma
Kod kalitesini korumak için testleri çalıştırın:
```bash
pip install -r requirements.txt  # pytest ve diğer bağımlılıkları yükle
pytest                           # Tüm testleri çalıştır
```

---

<div align="center">

*Geliştirici / Developer: [MahmutP](https://github.com/MahmutP)* 
*License: Apache 2.0*

</div>
