# 🚀 Mah Framework

**Mah Framework**, Python ile geliştirilmiş, modüler yapıya sahip, genişletilebilir bir Komut Satırı Arayüzü (CLI) çatısıdır.

Modern terminal araçları (`rich`, `prompt_toolkit`) kullanılarak tasarlanan bu framework, **mahpreter** projesinin altyapısını oluşturur ve kendi modüllerinizi/komutlarınızı kolayca ekleyebileceğiniz esnek bir yapı sunar.

## ✨ Özellikler

  * **Modüler Mimari:** `modules/` ve `commands/` klasörleri sayesinde yeni özellikleri tak-çıkar mantığıyla ekleyebilirsiniz.
  * **Modern Arayüz:** `rich` kütüphanesi ile renklendirilmiş, okunabilir ve şık terminal çıktıları.
  * **Gelişmiş Etkileşim:** `prompt_toolkit` desteği ile otomatik tamamlama ve geçmiş (history) özellikleri.
  * **Ağ ve Sistem Araçları:** `telnetlib3` ve `psutil` gibi yerleşik kütüphanelerle ağ/sistem yönetimi için hazır altyapı.

## 📂 Proje Yapısı

```
mah-framework/
├── core/             # Framework'ün çekirdek dosyaları (Motor)
├── commands/         # CLI üzerinden çalıştırılan komutlar
├── modules/          # Harici modüller ve eklentiler
├── config/           # Ayar dosyaları
├── main.py           # Uygulamanın giriş noktası (Başlatıcı)
├── pycache_sil.sh    # Gereksiz önbellek dosyalarını temizleme aracı
├── requirements.txt  # Gerekli Python kütüphaneleri
└── README.md         # Dokümantasyon
```

## 🛠️ Kurulum

Projeyi yerel makinenizde çalıştırmak için aşağıdaki adımları izleyin.

### Gereksinimler

  * Python 3.8 veya daha üzeri
  * Git

### 1\. Projeyi Klonlayın

Terminalinizi açın ve projeyi bilgisayarınıza indirin:

```bash
git clone https://github.com/MahmutP/mah-framework.git
cd mah-framework
```

### 2\. Sanal Ortam Oluşturun (Önerilen)

Bağımlılıkların sistem geneline yayılmaması için sanal ortam kullanmanız önerilir:

```bash
# Linux / MacOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3\. Kütüphaneleri Yükleyin

Gerekli paketleri `requirements.txt` dosyasından yükleyin:

```bash
pip install -r requirements.txt
```

*Alternatif olarak manuel yükleme:*

```bash
pip install rich prompt-toolkit asciistuff telnetlib3 psutil
```

## 💻 Kullanım

Kurulum tamamlandıktan sonra framework'ü başlatmak için `main.py` dosyasını çalıştırın:

```bash
python main.py
```

Uygulama başladığında sizi modern bir komut satırı karşılayacaktır. Burada tanımlı komutları kullanabilir veya `help` yazarak (eğer tanımlıysa) mevcut komutları listeleyebilirsiniz.

### Bakım

Geliştirme sırasında oluşan `__pycache__` dosyalarını temizlemek için hazır scripti kullanabilirsiniz:

```bash
chmod +x pycache_sil.sh  # İlk kullanımda çalıştırma izni verin
./pycache_sil.sh
```

## 🤝 Katkıda Bulunma

Bu proje açık kaynaklıdır ve katkılara açıktır.

1.  Projeyi Fork'layın.
2.  Yeni bir özellik dalı (branch) oluşturun (`git checkout -b ozellik/YeniOzellik`).
3.  Değişikliklerinizi kaydedin (`git commit -m 'Yeni özellik eklendi'`).
4.  Dalınızı Push edin (`git push origin ozellik/YeniOzellik`).
5.  Bir Pull Request (PR) oluşturun.

## 📜 Lisans

Bu proje **Apache License 2.0** ile lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakınız.

-----

*Geliştirici: [MahmutP](https://github.com/MahmutP)*