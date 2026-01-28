# 🛠️ Mah Framework Developer Guide

Bu rehber, **Mah Framework** için yeni modüller geliştirmek isteyenler için hazırlanmıştır.

## 📌 İçindekiler
1. [Modül Yapısı](#modül-yapısı)
2. [Adım Adım Modül Oluşturma](#adım-adım-modül-oluşturma)
3. [BaseModule API Referansı](#basemodule-api-referansı)
4. [Option Sınıfı ve Kullanımı](#option-sınıfı-ve-kullanımı)

---

## 🏗️ Modül Yapısı

Mah Framework modülleri, `modules/` dizini (veya alt dizinleri) altında bulunan `.py` dosyalarıdır. Her modül, `core.module.BaseModule` sınıfından miras almalıdır.

### Örnek Dosya Yolu
`modules/exploit/my_new_exploit.py`

---

## 🚀 Adım Adım Modül Oluşturma

### 1. Dosya Oluşturun
`modules/test/hello_world.py` adında bir dosya oluşturun.

### 2. Gerekli Importları Yapın
```python
from core.module import BaseModule
from core.option import Option
from rich import print
```

### 3. Sınıfınızı Tanımlayın
```python
class HelloWorld(BaseModule):
    def __init__(self):
        # 1. Modül Meta Verileri
        self.Name = "test/hello_world"
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
                description="Ekrana yazılacak mesaj"
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
        
        return True
```

---

## 📚 BaseModule API Referansı

### Özellikler (Properties)
*   **Name** (`str`): Modülün benzersiz adı (örn: `exploit/linux/ftp/vsftpd_234`).
*   **Description** (`str`): `info` komutunda görünen açıklama.
*   **Author** (`str`): Yazar adı.
*   **Category** (`str`): Modül kategorisi (`exploit`, `scanner`, vb.).
*   **Options** (`Dict[str, Option]`): Modülün kabul ettiği parametreler.

### Metotlar
*   **run(self, options: Dict[str, Any])**: Modül çalıştırıldığında (`run` komutu) çağrılan ana fonksiyon.
    *   *Args:* `options`: Kullanıcının `set` komutuyla belirlediği değerleri içeren sözlük.
*   **check_required_options(self) -> bool**: Zorunlu parametrelerin doluluğunu kontrol eder. Otomatik çağrılır.

---

## 🎛️ Option Sınıfı ve Kullanımı

Kullanıcıdan veri almak için `core.option.Option` sınıfı kullanılır.

### Parametreler
*   **name** (`str`): Parametre adı (Büyük harf önerilir, örn: `RHOST`).
*   **value** (`Any`): Varsayılan değer.
*   **required** (`bool`): `True` ise kullanıcı değer girmeden modül çalışmaz.
*   **description** (`str`): `show options` çıktısında görünen açıklama.
*   **regex_check** (`bool`): Regex doğrulaması yapılsın mı?
*   **regex** (`str`): Doğrulama paterni.

---

## 💡 İpuçları
*   `self.Options` içinde tanımladığınız her anahtar (örn: `TARGET`), `run` metodunda `options.get("TARGET")` ile alınabilir.
*   Çıktı vermek için `rich` kütüphanesinin `print` fonksiyonunu kullanın (renkli çıktılar için).
*   Karmaşık işlemler için `templates/module_template.py` şablonunu kullanabilirsiniz.
