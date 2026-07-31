# Mah Framework Documentation / Dokümantasyon

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

Central index for Mah Framework guides. Start with [Quick Start](QUICKSTART.md) if you are new.

### Getting Started

| Guide | Description |
| ----- | ----------- |
| [Quick Start](QUICKSTART.md) | Install, first run, essential workflow |
| [Commands Reference](COMMANDS.md) | All built-in CLI commands |
| [Modules Catalog](MODULES.md) | Built-in modules by category |
| [Macro / Resource Files](usage_guide_macro.md) | Record and replay `.rc` scripts |

### Payloads & Agents

| Guide | Description |
| ----- | ----------- |
| [Payloads Guide](PAYLOADS.md) | Reverse/bind shells, encoders, sessions |
| [Chimera User Guide](CHIMERA_USER_GUIDE.md) | Chimera agent: generate, handler, session features |
| [Chimera Commands](CHIMERA_COMMANDS_USAGE.md) | Detailed Chimera session command reference |
| [Chimera Module Loading](chimera_module_loading.md) | In-memory `loadmodule` / `runmodule` |
| [Payload Testing Guide](PAYLOAD_TESTING_GUIDE.md) | How to test payloads safely |

### Chimera Testing & Hardening

| Guide | Description |
| ----- | ----------- |
| [Test Scenarios](CHIMERA_TEST_SCENARIOS.md) | End-to-end test scenarios |
| [Edge Cases](CHIMERA_EDGE_CASES.md) | Boundary and failure cases |
| [Performance Tests](CHIMERA_PERFORMANCE_TESTS.md) | Performance checklist |
| [AV Testing](CHIMERA_AV_TESTING.md) | Antivirus / EDR test notes |

### Extensions & Repos

| Guide | Description |
| ----- | ----------- |
| [Plugin Guide](PLUGIN_GUIDE.md) | Hooks, plugin lifecycle, built-in plugins |
| [Repo & Download](REPO_AND_DOWNLOAD.md) | Remote repositories and module install |
| [Developer Guide](DEVELOPER_GUIDE.md) | Create modules, plugins, and commands |

### Feature Modules

| Guide | Description |
| ----- | ----------- |
| [GitHub Tracker](GITHUB_TRACKER.md) | `auxiliary/recon/github_tracker` |
| [Metadata Modules](METADATA_MODULES.md) | EXIF extract / clean |

### Internals

| Guide | Description |
| ----- | ----------- |
| [Architecture](ARCHITECTURE.md) | Core components, data flow, directories |

### Suggested Reading Order

1. [Quick Start](QUICKSTART.md)
2. [Commands Reference](COMMANDS.md)
3. [Modules Catalog](MODULES.md) or [Payloads](PAYLOADS.md)
4. [Chimera User Guide](CHIMERA_USER_GUIDE.md) (if using Chimera)
5. [Developer Guide](DEVELOPER_GUIDE.md) (if extending the framework)

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Mah Framework rehberlerinin merkezi indeksi. Yeni başlıyorsanız [Hızlı Başlangıç](QUICKSTART.md) ile başlayın.

### Başlangıç

| Rehber | Açıklama |
| ------ | -------- |
| [Hızlı Başlangıç](QUICKSTART.md) | Kurulum, ilk çalıştırma, temel akış |
| [Komut Referansı](COMMANDS.md) | Tüm yerleşik CLI komutları |
| [Modül Kataloğu](MODULES.md) | Kategoriye göre yerleşik modüller |
| [Makro / Resource Dosyaları](usage_guide_macro.md) | `.rc` kaydetme ve oynatma |

### Payload ve Ajanlar

| Rehber | Açıklama |
| ------ | -------- |
| [Payloads Rehberi](PAYLOADS.md) | Reverse/bind shell, encoder, oturumlar |
| [Chimera Kullanım Rehberi](CHIMERA_USER_GUIDE.md) | Chimera ajan: üret, dinle, oturum özellikleri |
| [Chimera Komutları](CHIMERA_COMMANDS_USAGE.md) | Chimera oturum komutlarının detaylı referansı |
| [Chimera Modül Yükleme](chimera_module_loading.md) | Bellek içi `loadmodule` / `runmodule` |
| [Payload Test Rehberi](PAYLOAD_TESTING_GUIDE.md) | Payload'ları güvenli test etme |

### Chimera Test ve Sertleştirme

| Rehber | Açıklama |
| ------ | -------- |
| [Test Senaryoları](CHIMERA_TEST_SCENARIOS.md) | Uçtan uca test senaryoları |
| [Edge Case'ler](CHIMERA_EDGE_CASES.md) | Sınır ve hata durumları |
| [Performans Testleri](CHIMERA_PERFORMANCE_TESTS.md) | Performans kontrol listesi |
| [AV Testleri](CHIMERA_AV_TESTING.md) | Antivirüs / EDR test notları |

### Uzantılar ve Depolar

| Rehber | Açıklama |
| ------ | -------- |
| [Plugin Rehberi](PLUGIN_GUIDE.md) | Hook'lar, yaşam döngüsü, yerleşik pluginler |
| [Repo ve Download](REPO_AND_DOWNLOAD.md) | Uzak depolar ve modül kurulumu |
| [Geliştirici Rehberi](DEVELOPER_GUIDE.md) | Modül, plugin ve komut yazma |

### Özellik Modülleri

| Rehber | Açıklama |
| ------ | -------- |
| [GitHub Tracker](GITHUB_TRACKER.md) | `auxiliary/recon/github_tracker` |
| [Metadata Modülleri](METADATA_MODULES.md) | EXIF çıkarma / temizleme |

### İç Yapı

| Rehber | Açıklama |
| ------ | -------- |
| [Mimari](ARCHITECTURE.md) | Çekirdek bileşenler, veri akışı, dizinler |

### Önerilen Okuma Sırası

1. [Hızlı Başlangıç](QUICKSTART.md)
2. [Komut Referansı](COMMANDS.md)
3. [Modül Kataloğu](MODULES.md) veya [Payloads](PAYLOADS.md)
4. [Chimera Kullanım Rehberi](CHIMERA_USER_GUIDE.md) (Chimera kullanıyorsanız)
5. [Geliştirici Rehberi](DEVELOPER_GUIDE.md) (framework'ü genişletecekseniz)
