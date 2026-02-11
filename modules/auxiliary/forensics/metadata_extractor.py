# =============================================================================
# METADATA EXTRACTOR - Görsel Dosya Metadata Çekici
# =============================================================================
#
# Bu modül, görsel dosyalardan (JPEG, PNG, TIFF vb.) EXIF ve diğer
# metadata bilgilerini çeker ve detaylı bir rapor oluşturur.
#
# Kullanım:
#   1. use auxiliary/forensics/metadata_extractor
#   2. set FILE /path/to/image.jpg
#   3. run
#
# Desteklenen Formatlar:
#   JPEG, PNG, TIFF, BMP, GIF, WebP
#
# =============================================================================

from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from core import logger
from rich import print
from rich.table import Table
from rich.panel import Panel

import os

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False


class MetadataExtractor(BaseModule):
    """Metadata Extractor Modülü

    Görsel dosyalardan EXIF ve metadata bilgilerini çeker.
    Kamera bilgisi, GPS koordinatları, tarih/saat, çözünürlük
    gibi verileri analiz eder ve raporlar.

    Attributes:
        Name: Modülün görünen adı
        Description: Kısa açıklama
        Author: Geliştirici
        Category: Modül kategorisi
        Options: Kullanıcı tarafından ayarlanabilir seçenekler
    """

    Name = "Metadata Extractor"
    Description = "Görsel dosyalardan EXIF ve metadata bilgilerini çeker"
    Author = "Mahmut P."
    Category = "auxiliary/forensics"

    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp'}

    def __init__(self):
        """Modül başlatıcı."""
        super().__init__()

        self.Options = {
            "FILE": Option(
                name="FILE",
                value="",
                required=True,
                description="Hedef görsel dosya yolu",
                completion_dir=".",
                completion_extensions=['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp']
            ),
            "VERBOSE": Option(
                name="VERBOSE",
                value="false",
                required=False,
                description="Tüm raw EXIF tag'lerini göster (true/false)",
                choices=["true", "false"]
            ),
        }

        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    def _check_dependencies(self) -> bool:
        """Gerekli kütüphanelerin kurulu olup olmadığını kontrol eder."""
        if not PIL_AVAILABLE:
            print("[bold red]Hata:[/bold red] 'Pillow' kütüphanesi kurulu değil.")
            print("Kurulum: [cyan]pip install pillow[/cyan]")
            return False
        return True

    def _get_gps_coordinates(self, gps_info: dict) -> tuple:
        """GPS bilgisinden ondalık koordinatları hesaplar.

        Args:
            gps_info: EXIF GPS bilgi sözlüğü

        Returns:
            (latitude, longitude) tuple veya (None, None)
        """
        try:
            def _convert_to_degrees(value):
                """GPS koordinatını dereceye çevirir."""
                d = float(value[0])
                m = float(value[1])
                s = float(value[2])
                return d + (m / 60.0) + (s / 3600.0)

            lat = _convert_to_degrees(gps_info.get('GPSLatitude', [0, 0, 0]))
            lon = _convert_to_degrees(gps_info.get('GPSLongitude', [0, 0, 0]))

            lat_ref = gps_info.get('GPSLatitudeRef', 'N')
            lon_ref = gps_info.get('GPSLongitudeRef', 'E')

            if lat_ref == 'S':
                lat = -lat
            if lon_ref == 'W':
                lon = -lon

            return (lat, lon)
        except Exception:
            return (None, None)

    def _get_gps_from_piexif(self, exif_dict: dict) -> tuple:
        """piexif ile GPS bilgisinden ondalık koordinatları hesaplar.

        Args:
            exif_dict: piexif EXIF sözlüğü

        Returns:
            (latitude, longitude) tuple veya (None, None)
        """
        try:
            gps_data = exif_dict.get("GPS", {})
            if not gps_data:
                return (None, None)

            def _rational_to_float(rational):
                """piexif rational değerini float'a çevirir."""
                if isinstance(rational, tuple) and len(rational) == 2:
                    return rational[0] / rational[1] if rational[1] != 0 else 0.0
                return float(rational)

            def _convert_gps(coords):
                d = _rational_to_float(coords[0])
                m = _rational_to_float(coords[1])
                s = _rational_to_float(coords[2])
                return d + (m / 60.0) + (s / 3600.0)

            # piexif GPS tag IDs
            GPS_LAT = piexif.GPSIFD.GPSLatitude
            GPS_LAT_REF = piexif.GPSIFD.GPSLatitudeRef
            GPS_LON = piexif.GPSIFD.GPSLongitude
            GPS_LON_REF = piexif.GPSIFD.GPSLongitudeRef

            if GPS_LAT not in gps_data or GPS_LON not in gps_data:
                return (None, None)

            lat = _convert_gps(gps_data[GPS_LAT])
            lon = _convert_gps(gps_data[GPS_LON])

            lat_ref = gps_data.get(GPS_LAT_REF, b'N')
            lon_ref = gps_data.get(GPS_LON_REF, b'E')

            if isinstance(lat_ref, bytes):
                lat_ref = lat_ref.decode('ascii')
            if isinstance(lon_ref, bytes):
                lon_ref = lon_ref.decode('ascii')

            if lat_ref == 'S':
                lat = -lat
            if lon_ref == 'W':
                lon = -lon

            return (lat, lon)
        except Exception:
            return (None, None)

    def _extract_with_pillow(self, file_path: str, verbose: bool) -> dict:
        """Pillow ile metadata çeker.

        Args:
            file_path: Dosya yolu
            verbose: Detaylı çıktı

        Returns:
            Metadata sözlüğü
        """
        result = {
            "basic": {},
            "exif": {},
            "gps": None,
            "raw_tags": {}
        }

        img = Image.open(file_path)

        # Temel bilgiler
        result["basic"] = {
            "Format": img.format or "Bilinmiyor",
            "Boyut": f"{img.size[0]}x{img.size[1]} piksel",
            "Renk Modu": img.mode,
            "Dosya Boyutu": f"{os.path.getsize(file_path):,} byte"
        }

        # EXIF verisi
        exif_data = img._getexif() if hasattr(img, '_getexif') and img._getexif() else None

        if exif_data:
            gps_info = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)

                if tag_name == "GPSInfo":
                    for gps_tag_id, gps_value in value.items():
                        gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                        gps_info[gps_tag_name] = gps_value
                    continue

                # Önemli EXIF alanları
                important_tags = {
                    "Make": "Üretici",
                    "Model": "Kamera Modeli",
                    "DateTime": "Tarih/Saat",
                    "DateTimeOriginal": "Orijinal Tarih",
                    "DateTimeDigitized": "Dijitalleştirme Tarihi",
                    "Software": "Yazılım",
                    "ExifImageWidth": "Genişlik",
                    "ExifImageHeight": "Yükseklik",
                    "ISOSpeedRatings": "ISO",
                    "FNumber": "Diyafram (f/)",
                    "ExposureTime": "Enstantane",
                    "FocalLength": "Odak Uzaklığı",
                    "LensModel": "Lens Modeli",
                    "WhiteBalance": "Beyaz Dengesi",
                    "Flash": "Flaş",
                    "Orientation": "Yönelim",
                    "XResolution": "X Çözünürlük",
                    "YResolution": "Y Çözünürlük",
                    "Copyright": "Telif Hakkı",
                    "Artist": "Sanatçı/Fotoğrafçı",
                    "ImageDescription": "Açıklama",
                }

                if str(tag_name) in important_tags:
                    display_value = str(value)
                    if len(display_value) > 100:
                        display_value = display_value[:100] + "..."
                    result["exif"][important_tags[str(tag_name)]] = display_value

                if verbose:
                    raw_value = str(value)
                    if len(raw_value) > 150:
                        raw_value = raw_value[:150] + "..."
                    result["raw_tags"][str(tag_name)] = raw_value

            # GPS hesapla
            if gps_info:
                lat, lon = self._get_gps_coordinates(gps_info)
                if lat is not None and lon is not None:
                    result["gps"] = (lat, lon)

        img.close()
        return result

    def _extract_with_piexif(self, file_path: str, result: dict) -> dict:
        """piexif ile ek metadata çeker (GPS ve detaylı EXIF).

        Args:
            file_path: Dosya yolu
            result: Mevcut metadata sözlüğü

        Returns:
            Güncellenmiş metadata sözlüğü
        """
        try:
            exif_dict = piexif.load(file_path)

            # GPS verisi piexif ile daha güvenilir
            if result["gps"] is None:
                lat, lon = self._get_gps_from_piexif(exif_dict)
                if lat is not None and lon is not None:
                    result["gps"] = (lat, lon)

            # Thumbnail bilgisi
            if "thumbnail" in exif_dict and exif_dict["thumbnail"]:
                result["exif"]["Thumbnail"] = f"Mevcut ({len(exif_dict['thumbnail'])} byte)"

        except Exception as e:
            logger.warning(f"piexif ile ek veri çekilemedi: {e}")

        return result

    def run(self, options: Dict[str, Any]) -> bool:
        """Modülün ana çalıştırma metodu.

        Args:
            options: Kullanıcının ayarladığı seçenekler

        Returns:
            bool: Başarılı ise True
        """
        if not self._check_dependencies():
            return False

        file_path = options.get("FILE", "")
        verbose = str(options.get("VERBOSE", "false")).lower() == "true"

        # Dosya kontrolü
        if not file_path:
            print("[bold red]Hata:[/bold red] FILE parametresi boş olamaz!")
            return False

        if not os.path.isfile(file_path):
            print(f"[bold red]Hata:[/bold red] Dosya bulunamadı: {file_path}")
            return False

        # Format kontrolü
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.SUPPORTED_FORMATS:
            print(f"[bold red]Hata:[/bold red] Desteklenmeyen format: {ext}")
            print(f"Desteklenen formatlar: {', '.join(sorted(self.SUPPORTED_FORMATS))}")
            return False

        logger.info(f"Metadata çekiliyor: {file_path}")

        try:
            print(f"\n[bold cyan]🔍 Metadata Extractor[/bold cyan]\n")
            print(f"[dim]Dosya:[/dim] {file_path}\n")

            # Pillow ile metadata çek
            result = self._extract_with_pillow(file_path, verbose)

            # piexif ile ek veri çek
            if PIEXIF_AVAILABLE and ext.lower() in {'.jpg', '.jpeg', '.tiff', '.tif'}:
                result = self._extract_with_piexif(file_path, result)

            # --- Temel Bilgiler Tablosu ---
            basic_table = Table(title="📋 Dosya Bilgileri", border_style="blue")
            basic_table.add_column("Özellik", style="cyan", no_wrap=True)
            basic_table.add_column("Değer", style="white")

            for key, value in result["basic"].items():
                basic_table.add_row(key, str(value))

            print(basic_table)

            # --- EXIF Bilgileri Tablosu ---
            if result["exif"]:
                exif_table = Table(title="📷 EXIF Verileri", border_style="green")
                exif_table.add_column("Alan", style="cyan", no_wrap=True)
                exif_table.add_column("Değer", style="white")

                for key, value in result["exif"].items():
                    exif_table.add_row(key, str(value))

                print(exif_table)
            else:
                print("[yellow]⚠ EXIF verisi bulunamadı.[/yellow]")

            # --- GPS Bilgisi ---
            if result["gps"]:
                lat, lon = result["gps"]
                gps_table = Table(title="📍 GPS Konumu", border_style="red")
                gps_table.add_column("Bilgi", style="cyan", no_wrap=True)
                gps_table.add_column("Değer", style="white")

                gps_table.add_row("Enlem (Latitude)", f"{lat:.6f}")
                gps_table.add_row("Boylam (Longitude)", f"{lon:.6f}")
                gps_table.add_row("Google Maps", f"https://maps.google.com/?q={lat},{lon}")

                print(gps_table)
                print(f"\n[bold red]⚠ DİKKAT:[/bold red] Bu dosya GPS konum bilgisi içeriyor!")

            # --- Raw Tags (Verbose) ---
            if verbose and result["raw_tags"]:
                raw_table = Table(title="🏷️ Tüm EXIF Tag'leri (Raw)", border_style="dim")
                raw_table.add_column("Tag", style="dim cyan", no_wrap=True)
                raw_table.add_column("Değer", style="dim white")

                for key, value in sorted(result["raw_tags"].items()):
                    raw_table.add_row(str(key), str(value))

                print(raw_table)

            # --- Özet ---
            total_fields = len(result["exif"]) + len(result["basic"])
            has_gps = "✅ Evet" if result["gps"] else "❌ Hayır"
            print(f"\n[bold green]✓[/bold green] Toplam {total_fields} alan çıkarıldı. GPS: {has_gps}")

            logger.info(f"Metadata başarıyla çekildi: {file_path} ({total_fields} alan)")
            return True

        except Exception as e:
            print(f"[bold red]Hata:[/bold red] Metadata çekilirken sorun oluştu: {e}")
            logger.exception(f"Metadata çekme hatası: {file_path}")
            return False
