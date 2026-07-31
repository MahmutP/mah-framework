# Plugin Guide / Plugin Rehberi

[English](#-english-plugin-guide) | [Türkçe](#-türkçe-plugin-rehberi)

---

## 🇺🇸 English Plugin Guide

### What is a Plugin?

Plugins extend Mah Framework through a **hook / event system**. Unlike modules (standalone tools you `use` and `run`), plugins stay loaded and react to framework events such as startup, command execution, or session open/close.

### Module vs Plugin

| Feature | Module | Plugin |
| ------- | ------ | ------ |
| Purpose | Standalone tool | Extends the framework |
| Activation | `use` + `run` | Auto-loaded at startup |
| Interaction | Direct execution | Event-driven (hooks) |
| Location | `modules/` | `plugins/` |
| Base class | `BaseModule` | `BasePlugin` |

### Available Hooks

| Hook | Trigger | Example use |
| ---- | ------- | ----------- |
| `ON_STARTUP` | Framework starts | Init resources, welcome |
| `ON_SHUTDOWN` | Framework closes | Cleanup, flush buffers |
| `PRE_COMMAND` | Before any command | Audit, filter, block |
| `POST_COMMAND` | After any command | Result logging |
| `PRE_MODULE_RUN` | Before `run` | Extra validation |
| `POST_MODULE_RUN` | After `run` | Report / notify |
| `ON_MODULE_SELECT` | Module selected (`use`) | Context setup |
| `ON_OPTION_SET` | Option changed (`set`) | Dependent options |
| `ON_SESSION_OPEN` | Agent connects | Notify, log IP |
| `ON_SESSION_CLOSE` | Agent disconnects | Status update |
| `PRE_MODULE_LOAD` | Before module file load | Blacklist / watch |
| `POST_MODULE_LOAD` | After module load | Metadata index |
| `PRE_PLUGIN_LOAD` | Before plugin load | Env prep |
| `POST_PLUGIN_LOAD` | After plugin load | Stats |
| `ON_ERROR` | Exception occurs | Error reporting |

Full enum: `core/hooks.py`. Architecture notes: [ARCHITECTURE.md](ARCHITECTURE.md).

### Plugin Commands

```bash
plugins list
plugins info "Name"
plugins enable "Name"
plugins disable "Name"
plugins search <term>
plugins install <source>
plugins update [name]
plugins remove "Name"
```

### Creating a Plugin

1. Copy the template:

```bash
cp templates/plugin_template.py plugins/my_plugin.py
```

2. Edit class metadata:

```python
class MyPlugin(BasePlugin):
    Name = "My Plugin"
    Description = "What it does"
    Author = "Your Name"
    Version = "1.0.0"
    Enabled = True
    Priority = 100  # lower = earlier
```

3. Map hooks in `get_hooks()` and implement handlers:

```python
from collections.abc import Callable
from typing import Any

from core.hooks import HookType
from core.plugin import BasePlugin

class SimpleLogger(BasePlugin):
    Name = "Simple Logger"
    Description = "Logs all commands"
    Version = "1.0.0"

    def get_hooks(self) -> dict[HookType, Callable[..., Any]]:
        return {HookType.POST_COMMAND: self.log_command}

    def log_command(self, command_line: str, **kwargs: Any) -> None:
        print(f"[LOG] Command executed: {command_line}")
```

4. Restart the framework (or ensure plugin manager reloads plugins). Use `plugins list` to confirm.

Optional lifecycle hooks on the class:

* `on_load()` — when the plugin is loaded
* `on_unload()` — when unloaded / framework shutdown

### Configuration Files

Plugins may ship with YAML/JSON config. If the plugin declares a config path/name, the framework loads it at startup so each plugin can keep independent settings.

### Built-in Plugins

#### Audit Logger

* Logs framework activity for auditing.
* Manage with: `plugins enable "Audit Logger"` / `plugins disable "Audit Logger"`.

#### Resource Monitor

Logs system resource usage (CPU, RAM, Disk, Network) in the background.

* **Default:** disabled
* **Log file:** `config/logs/resources.log`
* **Interval:** every 5 seconds
* **Enable:** `plugins enable resource_monitor` (or the display name shown in `plugins list`)
* Monitoring starts after enable when subsequent commands run; it stays in the background.

### Tips

* Keep handlers fast — they run on the hot path of every command/module event.
* Use `Priority` to order cooperating plugins.
* Prefer logging to files under `config/logs/` for noisy plugins.
* For module-like one-shot tools, write a **module** instead of a plugin.

---

## 🇹🇷 Türkçe Plugin Rehberi

### Plugin Nedir?

Pluginler, Mah Framework'ü **hook / olay sistemi** ile genişletir. Modüllerden farklı olarak (`use` + `run` ile çalışan araçlar), pluginler yüklü kalır ve başlangıç, komut çalıştırma veya oturum açılma/kapanma gibi olaylara tepki verir.

### Modül vs Plugin

| Özellik | Modül | Plugin |
| ------- | ----- | ------ |
| Amaç | Bağımsız araç | Framework'ü genişletir |
| Aktivasyon | `use` + `run` | Başlangıçta otomatik |
| Etkileşim | Doğrudan çalıştırma | Olay tabanlı (hook) |
| Konum | `modules/` | `plugins/` |
| Temel sınıf | `BaseModule` | `BasePlugin` |

### Kullanılabilir Hook'lar

| Hook | Tetiklenme | Örnek kullanım |
| ---- | ---------- | -------------- |
| `ON_STARTUP` | Framework başlar | Kaynak başlatma |
| `ON_SHUTDOWN` | Framework kapanır | Temizlik |
| `PRE_COMMAND` | Komuttan önce | Denetim, filtre |
| `POST_COMMAND` | Komuttan sonra | Sonuç loglama |
| `PRE_MODULE_RUN` | `run` öncesi | Ek doğrulama |
| `POST_MODULE_RUN` | `run` sonrası | Rapor / bildirim |
| `ON_MODULE_SELECT` | Modül seçimi (`use`) | Bağlam kurulumu |
| `ON_OPTION_SET` | Seçenek değişimi (`set`) | Bağımlı seçenekler |
| `ON_SESSION_OPEN` | Ajan bağlanır | Bildirim, IP log |
| `ON_SESSION_CLOSE` | Ajan kopar | Durum güncelleme |
| `PRE_MODULE_LOAD` | Modül dosyası yüklenmeden önce | Kara liste |
| `POST_MODULE_LOAD` | Modül yüklendikten sonra | Meta indeks |
| `PRE_PLUGIN_LOAD` | Plugin yüklenmeden önce | Ortam hazırlığı |
| `POST_PLUGIN_LOAD` | Plugin yüklendikten sonra | İstatistik |
| `ON_ERROR` | Hata oluşunca | Hata raporlama |

Tam enum: `core/hooks.py`. Mimari: [ARCHITECTURE.md](ARCHITECTURE.md).

### Plugin Komutları

```bash
plugins list
plugins info "İsim"
plugins enable "İsim"
plugins disable "İsim"
plugins search <terim>
plugins install <kaynak>
plugins update [isim]
plugins remove "İsim"
```

### Plugin Oluşturma

1. Şablonu kopyalayın:

```bash
cp templates/plugin_template.py plugins/benim_pluginim.py
```

2. Meta verileri düzenleyin:

```python
class BenimPluginim(BasePlugin):
    Name = "Benim Pluginim"
    Description = "Ne yaptığı"
    Author = "Adınız"
    Version = "1.0.0"
    Enabled = True
    Priority = 100  # düşük = daha önce
```

3. `get_hooks()` içinde hook eşlemesi yapın ve handler yazın:

```python
from collections.abc import Callable
from typing import Any

from core.hooks import HookType
from core.plugin import BasePlugin

class BasitLoglayici(BasePlugin):
    Name = "Basit Loglayıcı"
    Description = "Tüm komutları loglar"
    Version = "1.0.0"

    def get_hooks(self) -> dict[HookType, Callable[..., Any]]:
        return {HookType.POST_COMMAND: self.komut_logla}

    def komut_logla(self, command_line: str, **kwargs: Any) -> None:
        print(f"[LOG] Çalıştırılan komut: {command_line}")
```

4. Framework'ü yeniden başlatın. `plugins list` ile doğrulayın.

İsteğe bağlı yaşam döngüsü:

* `on_load()` — yüklenince
* `on_unload()` — kaldırılınca / kapanırken

### Yapılandırma Dosyaları

Pluginler kendi YAML/JSON ayar dosyalarını kullanabilir. Tanımlanan config açılışta yüklenir; her plugin bağımsız ayar tutabilir.

### Yerleşik Pluginler

#### Audit Logger

* Framework aktivitesini denetim için loglar.
* Yönetim: `plugins enable "Audit Logger"` / `plugins disable "Audit Logger"`.

#### Resource Monitor

Sistem kaynak kullanımını (CPU, RAM, Disk, Ağ) arka planda loglar.

* **Varsayılan:** kapalı
* **Log dosyası:** `config/logs/resources.log`
* **Aralık:** 5 saniye
* **Açma:** `plugins enable resource_monitor` (`plugins list`teki görünen ad)
* Etkinleştirmeden sonra komutlar çalıştıkça arka planda sürer.

### İpuçları

* Handler'ları hızlı tutun — her komut/modül olayının sıcak yolundadırlar.
* Birlikte çalışan pluginlerde sırayı `Priority` ile ayarlayın.
* Gürültülü pluginler için `config/logs/` altına yazın.
* Tek seferlik araçlar için **modül** yazın, plugin değil.
