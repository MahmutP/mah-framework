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

### 📂 Project Structure

```text
mah-framework/
├── core/             # Core framework engine (managers, console, logger)
├── commands/         # Standard CLI commands (e.g., help, exit)
├── modules/          # External modules and plugins
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
python main.py -q -r script.rc # Both options combined
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

### 🤝 Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and submit a Pull Request.

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

### 📂 Proje Yapısı

```text
mah-framework/
├── core/             # Framework çekirdek dosyaları (yöneticiler, konsol, logger)
├── commands/         # Standart CLI komutları (örn: help, exit)
├── modules/          # Harici modüller ve eklentiler
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
python main.py -q -r script.rc # Her iki seçenek birlikte
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

### 🤝 Katkıda Bulunma

Bu proje açık kaynaklıdır ve katkılara açıktır. Lütfen projeyi fork'layın, yeni bir branch oluşturun ve Pull Request gönderin.

---

<div align="center">

*Geliştirici / Developer: [MahmutP](https://github.com/MahmutP)* 
*License: Apache 2.0*

</div>
