# =============================================================================
# METADATA CLEANER - Görsel Dosya Metadata Temizleyici
# =============================================================================
#
# Bu modül, görsel dosyalardan tüm EXIF ve metadata bilgilerini
# temizler. Gizlilik ve OPSEC amaçlı kullanılır.
#
# Kullanım:
#   1. use auxiliary/forensics/metadata_cleaner
#   2. set FILE /path/to/image.jpg
#   3. run
#
# Desteklenen Formatlar:
#   JPEG, PNG, TIFF, BMP, GIF, WebP
#
# =============================================================================

import os
import shutil
from typing import Any

from rich import print
from rich.table import Table

from core import logger
from core.module import BaseModule
from core.option import Option

try:
    from PIL import Image
    from PIL.ExifTags import TAGS

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif

    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False


class MetadataCleaner(BaseModule):
    """Metadata Cleaner Modülü

    Görsel dosyalardan tüm EXIF ve metadata bilgilerini temizler.
    Temizleme öncesi/sonrası karşılaştırma raporu sunar.

    Attributes:
        Name: Modülün görünen adı
        Description: Kısa açıklama
        Author: Geliştirici
        Category: Modül kategorisi
        Options: Kullanıcı tarafından ayarlanabilir seçenekler
    """

    Name = "Metadata Cleaner"
    Description = "Görsel dosyalardan tüm metadata bilgilerini temizler"
    Author = "Mahmut P."
    Category = "auxiliary/forensics"

    SUPPORTED_FORMATS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".tif",
        ".bmp",
        ".gif",
        ".webp",
    }

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
                completion_extensions=[
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".tiff",
                    ".tif",
                    ".bmp",
                    ".gif",
                    ".webp",
                ],
            ),
            "OUTPUT": Option(
                name="OUTPUT",
                value="",
                required=False,
                description="Çıktı dosya yolu (boşsa üzerine yazar)",
                completion_dir=".",
            ),
            "BACKUP": Option(
                name="BACKUP",
                value="true",
                required=False,
                description="Orijinal dosyanın yedeğini al (true/false)",
                choices=["true", "false"],
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

    def _count_metadata_fields(self, file_path: str) -> int:
        """Dosyadaki metadata alan sayısını döndürür.

        Args:
            file_path: Dosya yolu

        Returns:
            Metadata alan sayısı
        """
        try:
            img = Image.open(file_path)
            exif_data = (
                img._getexif() if hasattr(img, "_getexif") and img._getexif() else None
            )
            count = 0
            if exif_data:
                count = len(exif_data)
            # PNG text chunks
            if hasattr(img, "info") and img.info:
                count += len(img.info)
            img.close()
            return count
        except Exception:
            return 0

    def _get_metadata_summary(self, file_path: str) -> dict:
        """Dosyadaki metadata özetini döndürür.

        Args:
            file_path: Dosya yolu

        Returns:
            Metadata özet sözlüğü
        """
        summary = {
            "field_count": 0,
            "has_gps": False,
            "has_camera": False,
            "has_datetime": False,
            "has_thumbnail": False,
            "file_size": os.path.getsize(file_path),
        }

        try:
            img = Image.open(file_path)
            exif_data = (
                img._getexif() if hasattr(img, "_getexif") and img._getexif() else None
            )

            if exif_data:
                summary["field_count"] = len(exif_data)
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, "")
                    if tag_name == "GPSInfo":
                        summary["has_gps"] = True
                    elif tag_name in ("Make", "Model"):
                        summary["has_camera"] = True
                    elif tag_name in ("DateTime", "DateTimeOriginal"):
                        summary["has_datetime"] = True

            # PNG info
            if hasattr(img, "info") and img.info:
                summary["field_count"] += len(img.info)

            # piexif ile thumbnail kontrolü
            if PIEXIF_AVAILABLE:
                try:
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in {".jpg", ".jpeg", ".tiff", ".tif"}:
                        exif_dict = piexif.load(file_path)
                        if exif_dict.get("thumbnail"):
                            summary["has_thumbnail"] = True
                except Exception:
                    pass

            img.close()
        except Exception:
            pass

        return summary

    def _clean_metadata(self, file_path: str, output_path: str) -> bool:
        """Dosyadan metadata'yı temizler.

        Args:
            file_path: Kaynak dosya yolu
            output_path: Çıktı dosya yolu

        Returns:
            bool: Başarılı ise True
        """
        img = Image.open(file_path)

        # Yeni bir görüntü oluştur (metadata olmadan)
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(list(img.getdata()))

        # Format belirleme
        ext = os.path.splitext(output_path)[1].lower()
        save_format = img.format or "JPEG"

        format_map = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".tiff": "TIFF",
            ".tif": "TIFF",
            ".bmp": "BMP",
            ".gif": "GIF",
            ".webp": "WEBP",
        }
        save_format = format_map.get(ext, save_format)

        # Kaydet (exif parametresi olmadan)
        save_kwargs = {}
        if save_format == "JPEG":
            save_kwargs["quality"] = 95
        elif save_format == "PNG":
            save_kwargs["optimize"] = True

        clean_img.save(output_path, format=save_format, **save_kwargs)

        img.close()
        clean_img.close()
        return True

    def run(self, options: dict[str, Any]) -> bool:
        """Modülün ana çalıştırma metodu.

        Args:
            options: Kullanıcının ayarladığı seçenekler

        Returns:
            bool: Başarılı ise True
        """
        if not self._check_dependencies():
            return False

        file_path = options.get("FILE", "")
        output_path = options.get("OUTPUT", "")
        backup = str(options.get("BACKUP", "true")).lower() == "true"

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

        # Çıktı yolunu belirle
        if not output_path:
            output_path = file_path  # Üzerine yaz

        logger.info(f"Metadata temizleniyor: {file_path}")

        try:
            print("\n[bold cyan]🧹 Metadata Cleaner[/bold cyan]\n")
            print(f"[dim]Kaynak:[/dim] {file_path}")
            if output_path != file_path:
                print(f"[dim]Çıktı:[/dim] {output_path}")
            print()

            # --- Temizleme Öncesi Analiz ---
            before = self._get_metadata_summary(file_path)

            # Ön rapor tablosu
            before_table = Table(title="📊 Temizleme Öncesi", border_style="yellow")
            before_table.add_column("Bilgi", style="cyan", no_wrap=True)
            before_table.add_column("Durum", style="white")

            before_table.add_row("Metadata Alan Sayısı", str(before["field_count"]))
            before_table.add_row(
                "GPS Verisi", "✅ Var" if before["has_gps"] else "❌ Yok"
            )
            before_table.add_row(
                "Kamera Bilgisi", "✅ Var" if before["has_camera"] else "❌ Yok"
            )
            before_table.add_row(
                "Tarih Bilgisi", "✅ Var" if before["has_datetime"] else "❌ Yok"
            )
            before_table.add_row(
                "Thumbnail", "✅ Var" if before["has_thumbnail"] else "❌ Yok"
            )
            before_table.add_row("Dosya Boyutu", f"{before['file_size']:,} byte")

            print(before_table)

            if before["field_count"] == 0:
                print(
                    "\n[yellow]⚠ Bu dosyada temizlenecek metadata bulunamadı.[/yellow]"
                )
                return True

            # --- Yedek Al ---
            if backup and output_path == file_path:
                backup_path = file_path + ".backup"
                shutil.copy2(file_path, backup_path)
                print(f"\n[bold green]✓[/bold green] Yedek oluşturuldu: {backup_path}")

            # --- Temizleme İşlemi ---
            self._clean_metadata(file_path, output_path)

            # --- Temizleme Sonrası Analiz ---
            after = self._get_metadata_summary(output_path)

            after_table = Table(title="📊 Temizleme Sonrası", border_style="green")
            after_table.add_column("Bilgi", style="cyan", no_wrap=True)
            after_table.add_column("Önceki", style="yellow")
            after_table.add_column("Sonraki", style="green")

            after_table.add_row(
                "Metadata Alan Sayısı",
                str(before["field_count"]),
                str(after["field_count"]),
            )
            after_table.add_row(
                "GPS Verisi",
                "✅ Var" if before["has_gps"] else "❌ Yok",
                "✅ Var" if after["has_gps"] else "❌ Yok",
            )
            after_table.add_row(
                "Kamera Bilgisi",
                "✅ Var" if before["has_camera"] else "❌ Yok",
                "✅ Var" if after["has_camera"] else "❌ Yok",
            )
            after_table.add_row(
                "Tarih Bilgisi",
                "✅ Var" if before["has_datetime"] else "❌ Yok",
                "✅ Var" if after["has_datetime"] else "❌ Yok",
            )
            after_table.add_row(
                "Dosya Boyutu",
                f"{before['file_size']:,} byte",
                f"{after['file_size']:,} byte",
            )

            size_diff = before["file_size"] - after["file_size"]
            if size_diff > 0:
                after_table.add_row(
                    "Kazanılan Alan",
                    "",
                    f"[bold green]{size_diff:,} byte ({size_diff / 1024:.1f} KB)[/bold green]",
                )

            print(after_table)

            # Sonuç
            cleaned_fields = before["field_count"] - after["field_count"]
            print(
                f"\n[bold green]✓[/bold green] {cleaned_fields} metadata alanı başarıyla temizlendi."
            )

            if before["has_gps"] and not after["has_gps"]:
                print("[bold green]✓[/bold green] GPS konum verisi kaldırıldı.")

            logger.info(
                f"Metadata temizlendi: {file_path} -> {output_path} ({cleaned_fields} alan)"
            )
            return True

        except Exception as e:
            print(
                f"[bold red]Hata:[/bold red] Metadata temizlenirken sorun oluştu: {e}"
            )
            logger.exception(f"Metadata temizleme hatası: {file_path}")
            return False
