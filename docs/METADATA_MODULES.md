# 🔍 Metadata Modülleri / Metadata Modules

[English](#-english) | [Türkçe](#-türkçe)

---

## 🇬🇧 English

### Overview

Mah Framework includes two forensics modules for handling image metadata:

| Module                 | Path                                     | Description                                 |
| ---------------------- | ---------------------------------------- | ------------------------------------------- |
| **Metadata Extractor** | `auxiliary/forensics/metadata_extractor` | Extracts EXIF and metadata from image files |
| **Metadata Cleaner**   | `auxiliary/forensics/metadata_cleaner`   | Strips all metadata from image files        |

### Supported Formats
JPEG, PNG, TIFF, BMP, GIF, WebP

### Dependencies
- `pillow` — Image processing (already included)
- `piexif` — Detailed EXIF tag manipulation

### Metadata Extractor

Extracts EXIF data from image files and displays a detailed report including camera info, GPS coordinates, date/time, resolution, and more.

**Usage:**
```bash
use auxiliary/forensics/metadata_extractor
set FILE /path/to/photo.jpg
set VERBOSE true          # Optional: show all raw EXIF tags
run
```

**Options:**

| Option    | Required | Default | Description            |
| --------- | -------- | ------- | ---------------------- |
| `FILE`    | ✅        | —       | Target image file path |
| `VERBOSE` | ❌        | `false` | Show all raw EXIF tags |

**Features:**
- Camera make/model detection
- Date/time extraction
- GPS coordinate extraction with Google Maps link
- ISO, aperture, shutter speed
- Lens model, software info
- Thumbnail detection (via piexif)
- Rich table output

### Metadata Cleaner

Removes all EXIF and metadata from image files. Useful for privacy/OPSEC purposes.

**Usage:**
```bash
use auxiliary/forensics/metadata_cleaner
set FILE /path/to/photo.jpg
set BACKUP true            # Create backup before cleaning
run
```

**Options:**

| Option   | Required | Default | Description                                |
| -------- | -------- | ------- | ------------------------------------------ |
| `FILE`   | ✅        | —       | Target image file path                     |
| `OUTPUT` | ❌        | —       | Output path (overwrites original if empty) |
| `BACKUP` | ❌        | `true`  | Create backup of original file             |

**Features:**
- Complete metadata stripping
- Before/after comparison report
- File size savings report
- Automatic backup creation
- Separate output file support

---

## 🇹🇷 Türkçe

### Genel Bakış

Mah Framework, görsel dosya metadata işlemleri için iki forensics modülü içerir:

| Modül                  | Yol                                      | Açıklama                                    |
| ---------------------- | ---------------------------------------- | ------------------------------------------- |
| **Metadata Extractor** | `auxiliary/forensics/metadata_extractor` | Görsel dosyalardan EXIF ve metadata çeker   |
| **Metadata Cleaner**   | `auxiliary/forensics/metadata_cleaner`   | Görsel dosyalardan tüm metadata'yı temizler |

### Desteklenen Formatlar
JPEG, PNG, TIFF, BMP, GIF, WebP

### Bağımlılıklar
- `pillow` — Görüntü işleme (zaten dahil)
- `piexif` — Detaylı EXIF tag manipülasyonu

### Metadata Extractor (Metadata Çekici)

Görsel dosyalardan EXIF verilerini çeker ve kamera bilgisi, GPS koordinatları, tarih/saat, çözünürlük gibi detaylı bir rapor sunar.

**Kullanım:**
```bash
use auxiliary/forensics/metadata_extractor
set FILE /yol/fotograf.jpg
set VERBOSE true          # Opsiyonel: tüm raw EXIF tag'lerini göster
run
```

**Seçenekler:**

| Seçenek   | Zorunlu | Varsayılan | Açıklama                       |
| --------- | ------- | ---------- | ------------------------------ |
| `FILE`    | ✅       | —          | Hedef görsel dosya yolu        |
| `VERBOSE` | ❌       | `false`    | Tüm ham EXIF tag'lerini göster |

**Özellikler:**
- Kamera marka/model tespit
- Tarih/saat bilgisi çıkarma
- GPS koordinat çıkarma + Google Maps linki
- ISO, diyafram, enstantane hızı
- Lens modeli, yazılım bilgisi
- Thumbnail tespiti (piexif ile)
- Rich tablo çıktısı

### Metadata Cleaner (Metadata Temizleyici)

Görsel dosyalardan tüm EXIF ve metadata bilgilerini temizler. Gizlilik/OPSEC amaçlı kullanılır.

**Kullanım:**
```bash
use auxiliary/forensics/metadata_cleaner
set FILE /yol/fotograf.jpg
set BACKUP true            # Temizlemeden önce yedek al
run
```

**Seçenekler:**

| Seçenek  | Zorunlu | Varsayılan | Açıklama                                    |
| -------- | ------- | ---------- | ------------------------------------------- |
| `FILE`   | ✅       | —          | Hedef görsel dosya yolu                     |
| `OUTPUT` | ❌       | —          | Çıktı yolu (boşsa orijinalin üzerine yazar) |
| `BACKUP` | ❌       | `true`     | Orijinal dosyanın yedeğini al               |

**Özellikler:**
- Tüm metadata'yı temizleme
- Öncesi/sonrası karşılaştırma raporu
- Dosya boyutu kazanımı raporu
- Otomatik yedek oluşturma
- Ayrı çıktı dosyası desteği
