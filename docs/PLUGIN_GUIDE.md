# 🔌 Plugin Guide / Plugin Rehberi

[English](#-english-plugin-guide) | [Türkçe](#-türkçe-plugin-rehberi)

---

## 🇺🇸 English Plugin Guide

### What is a Plugin?

Plugins extend Mah Framework functionality through a **hook/event system**. Unlike modules (which are standalone tools), plugins react to framework events like command execution or startup.

### Module vs Plugin

| Feature     | Module           | Plugin                 |
| ----------- | ---------------- | ---------------------- |
| Purpose     | Standalone tool  | Extends framework      |
| Activation  | `use` command    | Auto-loaded at startup |
| Interaction | Direct execution | Event-driven (hooks)   |
| Location    | `modules/`       | `plugins/`             |

### Available Hooks

| Hook               | Trigger            | Example Use          |
| ------------------ | ------------------ | -------------------- |
| `ON_STARTUP`       | Framework starts   | Initialize resources |
| `ON_SHUTDOWN`      | Framework closes   | Cleanup operations   |
| `PRE_COMMAND`      | Before any command | Command logging      |
| `POST_COMMAND`     | After any command  | Command auditing     |
| `PRE_MODULE_RUN`   | Before module runs | Validation checks    |
| `POST_MODULE_RUN`  | After module runs  | Result logging       |
| `ON_MODULE_SELECT` | Module selected    | Context setup        |
| `ON_ERROR`         | Error occurs       | Error reporting      |

### Plugin Commands

```bash
plugins list              # List all plugins
plugins info "Name"       # Show plugin details
plugins enable "Name"     # Enable a plugin
plugins disable "Name"    # Disable a plugin
```

### Creating a Plugin

1. Copy the template:
   ```bash
   cp templates/plugin_template.py plugins/my_plugin.py
   ```

2. Edit the class properties:
   ```python
   class MyPlugin(BasePlugin):
       Name = "My Plugin"
       Description = "What it does"
       Author = "Your Name"
       Version = "1.0.0"
   ```

3. Define hooks in `get_hooks()`:
   ```python
   def get_hooks(self) -> Dict[HookType, Callable]:
       return {
           HookType.PRE_COMMAND: self.on_command,
       }
   ```

4. Implement handler methods and restart the framework.

---

## 🇹🇷 Türkçe Plugin Rehberi

### Plugin Nedir?

Pluginler, Mah Framework işlevselliğini **hook/event sistemi** üzerinden genişletir. Modüllerden farklı olarak (bağımsız araçlar), pluginler framework olaylarına tepki verir.

### Modül vs Plugin

| Özellik    | Modül               | Plugin                 |
| ---------- | ------------------- | ---------------------- |
| Amaç       | Bağımsız araç       | Framework'ü genişletir |
| Aktivasyon | `use` komutu        | Başlangıçta otomatik   |
| Etkileşim  | Doğrudan çalıştırma | Olay tabanlı (hook)    |
| Konum      | `modules/`          | `plugins/`             |

### Kullanılabilir Hook'lar

| Hook               | Tetiklenme              | Örnek Kullanım        |
| ------------------ | ----------------------- | --------------------- |
| `ON_STARTUP`       | Framework başlar        | Kaynak başlatma       |
| `ON_SHUTDOWN`      | Framework kapanır       | Temizlik işlemleri    |
| `PRE_COMMAND`      | Komuttan önce           | Komut loglama         |
| `POST_COMMAND`     | Komuttan sonra          | Komut denetimi        |
| `PRE_MODULE_RUN`   | Modül çalışmadan önce   | Doğrulama kontrolleri |
| `POST_MODULE_RUN`  | Modül çalıştıktan sonra | Sonuç loglama         |
| `ON_MODULE_SELECT` | Modül seçildiğinde      | Bağlam kurulumu       |
| `ON_ERROR`         | Hata oluştuğunda        | Hata raporlama        |

### Plugin Komutları

```bash
plugins list              # Tüm pluginleri listele
plugins info "İsim"       # Plugin detaylarını göster
plugins enable "İsim"     # Plugini etkinleştir
plugins disable "İsim"    # Plugini devre dışı bırak
```

### Plugin Oluşturma

1. Şablonu kopyalayın:
   ```bash
   cp templates/plugin_template.py plugins/benim_pluginim.py
   ```

2. Sınıf özelliklerini düzenleyin:
   ```python
   class BenimPluginim(BasePlugin):
       Name = "Benim Pluginim"
       Description = "Ne yaptığı"
       Author = "Adınız"
       Version = "1.0.0"
   ```

3. `get_hooks()` metodunda hook'ları tanımlayın:
   ```python
   def get_hooks(self) -> Dict[HookType, Callable]:
       return {
           HookType.PRE_COMMAND: self.on_command,
       }
   ```

4. Handler metodlarını yazın ve framework'ü yeniden başlatın.

---

```

### Resource Monitor Plugin

The **Resource Monitor** plugin logs system resource usage (CPU, RAM, Disk, Network) to a file in the background.

- **Status**: Disabled by default.
- **Log File**: `config/logs/resources.log`
- **Interval**: Every 5 seconds.
- **Commands**:
  - Enable: `plugins enable resource_monitor`
  - Disable: `plugins disable resource_monitor`

**Note**: The monitoring starts automatically when you run any command after enabling the plugin. It runs silently in the background.

---

### Example Plugin / Örnek Plugin

```python
from core.plugin import BasePlugin
from core.hooks import HookType

class SimpleLogger(BasePlugin):
    Name = "Simple Logger"
    Description = "Logs all commands"
    
    def get_hooks(self):
        return {HookType.POST_COMMAND: self.log_command}
    
    def log_command(self, command_line, **kwargs):
        print(f"[LOG] Command executed: {command_line}")
```
