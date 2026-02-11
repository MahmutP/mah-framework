# 🛠️ Mah Framework Developer Guide / Geliştirici Rehberi

[English](#-english-developer-guide) | [Türkçe](#-türkçe-geliştirici-rehberi)

---

## 🇺🇸 English Developer Guide

This guide is designed for developers who want to create new modules and plugins for **Mah Framework**.

### 📌 Table of Contents

1. [Module Structure](#module-structure)
2. [Step-by-Step Module Creation](#step-by-step-module-creation)
3. [BaseModule API Reference](#basemodule-api-reference)
4. [Option Class Usage](#option-class-usage)
5. [Plugin Development](#plugin-development)

---

### 🏗️ Module Structure

Mah Framework modules are `.py` files located under the `modules/` directory (or its subdirectories). Every module must inherit from the `core.module.BaseModule` class.

#### Example File Path
`modules/exploit/my_new_exploit.py`

---

### 🚀 Step-by-Step Module Creation

#### 1. Create a File
Create a file named `modules/test/hello_world.py`.

#### 2. Import Required Classes
```python
from core.module import BaseModule
from core.option import Option
from rich import print
```

#### 3. Define Your Class
```python
class HelloWorld(BaseModule):
    def __init__(self):
        # 1. Module Metadata
        self.Name = "Hello World Test Module" # Human-readable name
        self.Description = "Developer guide example module"
        self.Author = "Your Name"
        self.Category = "test"
        
        # 2. Define Options
        self.Options = {
            "TARGET": Option(
                name="TARGET",
                value="127.0.0.1",
                required=True,
                description="Target IP address",
                regex_check=True, # Simple regex check
                regex=r"^\d{1,3}(\.\d{1,3}){3}$" # IP format
            ),
            "MESSAGE": Option(
                name="MESSAGE",
                value="Hello World!",
                required=False,
                description="Message to display",
                choices=["Hello", "Hi", "Greetings"] # Optional: Suggestions for tab completion
            )
        }
        
        # BaseModule init call (Important!)
        super().__init__()

    def run(self, options):
        # 3. Business Logic
        target = options.get("TARGET")
        message = options.get("MESSAGE")
        
        print(f"[bold green][+] Target:[/bold green] {target}")
        print(f"[bold blue][*] Message:[/bold blue] {message}")
        
        # Return True or a string/list log message
        return True
```

---

### 📚 BaseModule API Reference

#### Properties
*   **Name** (`str`): Human-readable name of the module (e.g., `VSFTPD 2.3.4 Backdoor`). The system automatically handles the path.
*   **Description** (`str`): Description shown in the `info` command.
*   **Author** (`str`): Name of the author.
*   **Category** (`str`): Module category (`exploit`, `scanner`, `forensics`, etc.).
*   **Options** (`Dict[str, Option]`): Parameters accepted by the module.

#### Methods
*   **run(self, options: Dict[str, Any])**: Main function called when the module is executed (`run` command).
    *   *Args:* `options`: Dictionary containing values set by the user using `set`.
    *   *Returns:* `Union[str, List[str]]` or `True/False`.
*   **check_required_options(self) -> bool**: Checks if required parameters are filled. Called automatically.

---

### 🎛️ Option Class Usage

The `core.option.Option` class is used to receive input from the user.

#### Parameters
*   **name** (`str`): Parameter name (Uppercase recommended, e.g., `RHOST`).
*   **value** (`Any`): Default value.
*   **required** (`bool`): If `True`, the module will not run without a value.
*   **description** (`str`): Description shown in `show options`.
*   **regex_check** (`bool`): Enable regex validation?
*   **regex** (`str`): Validation pattern.
*   **choices** (`List[Any]`): Optional list of values for auto-completion suggestions.

---

### 🧩 Plugin Development

Plugins extend the framework with persistent functionality that reacts to events, unlike modules which perform a single task.

#### What is a Plugin?

*   **Difference from Modules**: Modules are "tools" (like a hammer), Plugins are "extensions" (like a surveillance camera).
*   **Hook/Event System**: Plugins register "hooks" (listeners). When an event occurs (e.g., startup, command execution), the framework notifies all registered plugins.

#### Creating a New Plugin

1.  **Copy Template**: Copy `templates/plugin_template.py` to `plugins/my_plugin.py`.
2.  **Define Class**: Inherit from `BasePlugin` and set properties (Name, Version, Enabled).
3.  **Implement Hooks**: Return dictionary map in `get_hooks()` and write your handler methods.
4.  **Save**: Save effectively in `plugins/` directory.

#### Available Hooks

| Hook Name          | Triggered When...                 | Scenario Example                             |
| :----------------- | :-------------------------------- | :------------------------------------------- |
| `ON_STARTUP`       | Framework starts                  | Database connection, Welcome message         |
| `ON_SHUTDOWN`      | Framework exits                   | Cleanup, Save state, Bye message             |
| `PRE_COMMAND`      | Before executing a command        | Command filtering, Auditing, Modification    |
| `POST_COMMAND`     | After executing a command         | Logging result, Notification                 |
| `PRE_MODULE_RUN`   | Before running a module           | Permission check, Resource allocation        |
| `POST_MODULE_RUN`  | After running a module            | Report generation, Success notification      |
| `ON_MODULE_SELECT` | When a module is selected (`use`) | specific setup for a module type             |
| `ON_OPTION_SET`    | When an option is changed (`set`) | Validation, Auto-configure dependent options |

#### Example Plugin (Simple Logger)

```python
from core.plugin import BasePlugin
from core.hooks import HookType
from datetime import datetime

class SimpleLogger(BasePlugin):
    Name = "Simple Logger"
    Description = "Logs module execution times"
    Version = "1.0"
    
    def get_hooks(self):
        return {
            # Listen for module run completion
            HookType.POST_MODULE_RUN: self.on_module_finish
        }
    
    def on_module_finish(self, module_path, success, **kwargs):
        status = "SUCCESS" if success else "FAILED"
        print(f"[{datetime.now()}] Module {module_path} finished with status: {status}")
```

<br><br>

---
---

## 🇹🇷 Türkçe Geliştirici Rehberi

Bu rehber, **Mah Framework** için yeni modüller ve pluginler geliştirmek isteyenler için hazırlanmıştır.

### 📌 İçindekiler

1. [Modül Yapısı](#modül-yapısı)
2. [Adım Adım Modül Oluşturma](#adım-adım-modül-oluşturma)
3. [BaseModule API Referansı](#basemodule-api-referansı)
4. [Option Sınıfı ve Kullanımı](#option-sınıfı-ve-kullanımı)
5. [Plugin Geliştirme](#plugin-geliştirme)

---

### 🏗️ Modül Yapısı

Mah Framework modülleri, `modules/` dizini (veya alt dizinleri) altında bulunan `.py` dosyalarıdır. Her modül, `core.module.BaseModule` sınıfından miras almalıdır.

#### Örnek Dosya Yolu
`modules/exploit/my_new_exploit.py`

---

### 🚀 Adım Adım Modül Oluşturma

#### 1. Dosya Oluşturun
`modules/test/hello_world.py` adında bir dosya oluşturun.

#### 2. Gerekli Importları Yapın
```python
from core.module import BaseModule
from core.option import Option
from rich import print
```

#### 3. Sınıfınızı Tanımlayın
```python
class HelloWorld(BaseModule):
    def __init__(self):
        # 1. Modül Meta Verileri
        self.Name = "Hello World Test Modülü" # Okunabilir modül adı
        self.Description = "Geliştirici rehberi örnek modülü"
        self.Author = "Sizin Adınız"
        self.Category = "test"
        
        # 2. Seçenekleri (Options) Tanımlayın
        self.Options = {
            "TARGET": Option(
                name="TARGET",
                value="127.0.0.1",
                required=True,
                description="Hedef IP adresi",
                regex_check=True, # Basit regex kontrolü
                regex=r"^\d{1,3}(\.\d{1,3}){3}$" # IP formatı
            ),
            "MESSAGE": Option(
                name="MESSAGE",
                value="Merhaba Dünya!",
                required=False,
                description="Ekrana yazılacak mesaj",
                choices=["Merhaba", "Selam", "Naber"] # Opsiyonel: Tamamlama önerileri
            )
        }
        
        # BaseModule init çağrısı (önemli!)
        super().__init__()

    def run(self, options):
        # 3. İş Mantığı
        target = options.get("TARGET")
        message = options.get("MESSAGE")
        
        print(f"[bold green][+] Hedef:[/bold green] {target}")
        print(f"[bold blue][*] Mesaj:[/bold blue] {message}")
        
        # True veya işlem sonucu log mesajı döndürün
        return True
```

---

### 📚 BaseModule API Referansı

#### Özellikler (Properties)
*   **Name** (`str`): Modülün okunabilir adı (örn: `VSFTPD 2.3.4 Backdoor`). Dosya yolu sistem tarafından otomatik yönetilir.
*   **Description** (`str`): `info` komutunda görünen açıklama.
*   **Author** (`str`): Yazar adı.
*   **Category** (`str`): Modül kategorisi (`exploit`, `scanner`, `forensics`, vb.).
*   **Options** (`Dict[str, Option]`): Modülün kabul ettiği parametreler.

#### Metotlar (Methods)
*   **run(self, options: Dict[str, Any])**: Modül çalıştırıldığında (`run` komutu) çağrılan ana fonksiyon.
    *   *Argümanlar:* `options`: Kullanıcının `set` komutuyla belirlediği değerleri içeren sözlük.
    *   *Dönüş:* `Union[str, List[str]]` veya `True/False`.
*   **check_required_options(self) -> bool**: Zorunlu parametrelerin doluluğunu kontrol eder. Otomatik çağrılır.

---

### 🎛️ Option Sınıfı ve Kullanımı
Kullanıcıdan veri almak için `core.option.Option` sınıfı kullanılır.

#### Parametreler
*   **name** (`str`): Parametre adı (Büyük harf önerilir, örn: `RHOST`).
*   **value** (`Any`): Varsayılan değer.
*   **required** (`bool`): `True` ise kullanıcı değer girmeden modül çalışmaz.
*   **description** (`str`): `show options` çıktısında görünen açıklama.
*   **regex_check** (`bool`): Regex doğrulaması yapılsın mı?
*   **regex** (`str`): Doğrulama paterni.
*   **choices** (`List[Any]`): Otomatik tamamlama önerileri için opsiyonel liste.

---

### 🧩 Plugin Geliştirme

Pluginler, olay tabanlı çalışarak framework'ün yeteneklerini genişletir. Modüllerden farklı olarak süreklidir ve belirli bir göreve değil, genel sisteme odaklanır.

#### 1. Plugin Nedir?

*   **Modül vs Plugin Farkı**: Modüller bir kez çalıştırılıp biten "araçlardır" (tarama, saldırı vb.). Pluginler ise arka planda çalışan ve sistemi dinleyen "uzantılardır" (loglama, bildirim vb.).
*   **Hook/Event Sistemi**: Pluginler "kanca" (hook) yöntemiyle sisteme tutunur. Belirli bir olay gerçekleştiğinde (örn: komut girildiğinde), framework bu olayı dinleyen tüm pluginlere haber verir.

#### 2. Yeni Plugin Oluşturma

1.  **Şablonu Kopyalayın**: `templates/plugin_template.py` dosyasını `plugins/` klasörüne (örn: `plugins/takip_eklentisi.py`) kopyalayın.
2.  **Sınıfı Düzenleyin**: Sınıf adını değiştirin ve özelliklerini (Name, Description vb.) doldurun.
3.  **Handler Yazın**: Dinlemek istediğiniz olaylar için metodlar (handler) yazın.
4.  **Kaydedin**: Dosyayı kaydedip framework'ü yeniden başlatın.

#### 3. Kullanılabilir Hook'lar

| Hook Türü          | Tetiklenme Zamanı             | Örnek Senaryo                                 |
| :----------------- | :---------------------------- | :-------------------------------------------- |
| `ON_STARTUP`       | Framework açıldığında         | Veritabanı bağlantısı kurma, Karşılama mesajı |
| `ON_SHUTDOWN`      | Framework kapanırken          | Geçici dosyaları temizleme, Oturumu kaydetme  |
| `PRE_COMMAND`      | Komut çalışmadan hemen önce   | Komut filtreleme, Yasaklı komut kontrolü      |
| `POST_COMMAND`     | Komut çalıştıktan hemen sonra | Komut sonucunu loglama, Bildirim gönderme     |
| `PRE_MODULE_RUN`   | Modül çalışmadan hemen önce   | Yetki kontrolü, Hedef doğrulama               |
| `POST_MODULE_RUN`  | Modül çalıştıktan sonra       | Rapor oluşturma, Sonucu veritabanına yazma    |
| `ON_MODULE_SELECT` | Modül seçildiğinde (`use`)    | Modüle özel ayarları yükleme                  |
| `ON_OPTION_SET`    | Seçenek değiştiğinde (`set`)  | Girilen değerin gelişmiş doğrulaması          |

#### 4. Örnek Plugin (Basit Loglayıcı)

Aşağıda, her modül çalıştırıldığında bunu ekrana yazan basit bir plugin örneği verilmiştir.

```python
from core.plugin import BasePlugin
from core.hooks import HookType
from datetime import datetime

class BasitLoglayici(BasePlugin):
    Name = "Basit Loglayıcı"
    Description = "Modül çalışma zamanlarını ekrana basar"
    Version = "1.0"
    Enabled = True  # Varsayılan olarak aktif
    
    def get_hooks(self):
        # Hangi olayları dinleyeceğimizi belirtiyoruz
        return {
            HookType.POST_MODULE_RUN: self.modul_tamamlandi
        }
    
    def modul_tamamlandi(self, module_path, success, **kwargs):
        # Bu metod, modül çalışması bitince otomatik çağrılır
        durum = "BAŞARILI" if success else "BAŞARISIZ"
        zamani = datetime.now().strftime("%H:%M:%S")
        print(f"[{zamani}] Modül {module_path} durumu: {durum}")
```
