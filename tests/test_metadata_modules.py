import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock
from modules.auxiliary.forensics.metadata_extractor import MetadataExtractor
from modules.auxiliary.forensics.metadata_cleaner import MetadataCleaner
from core.option import Option


class TestMetadataExtractor:
    @pytest.fixture
    def extractor(self):
        return MetadataExtractor()

    def test_init(self, extractor):
        """Modül başlatma testi."""
        assert extractor.Name == "Metadata Extractor"
        assert extractor.Category == "auxiliary/forensics"
        assert extractor.Author == "Mahmut P."
        assert "FILE" in extractor.Options
        assert "VERBOSE" in extractor.Options

    def test_file_option_required(self, extractor):
        """FILE parametresinin zorunlu olduğunu doğrula."""
        assert extractor.Options["FILE"].required is True

    def test_verbose_option_default(self, extractor):
        """VERBOSE parametresinin varsayılan değerini doğrula."""
        assert extractor.Options["VERBOSE"].value == "false"
        assert extractor.Options["VERBOSE"].required is False

    def test_supported_formats(self, extractor):
        """Desteklenen format listesinin doğru olduğunu kontrol et."""
        assert '.jpg' in extractor.SUPPORTED_FORMATS
        assert '.jpeg' in extractor.SUPPORTED_FORMATS
        assert '.png' in extractor.SUPPORTED_FORMATS
        assert '.tiff' in extractor.SUPPORTED_FORMATS

    def test_run_empty_file(self, extractor):
        """Boş FILE parametresi ile çalıştırma testi."""
        result = extractor.run({"FILE": "", "VERBOSE": "false"})
        assert result is False

    def test_run_nonexistent_file(self, extractor):
        """Var olmayan dosya ile çalıştırma testi."""
        result = extractor.run({"FILE": "/tmp/nonexistent_image.jpg", "VERBOSE": "false"})
        assert result is False

    def test_run_unsupported_format(self, extractor):
        """Desteklenmeyen format testi."""
        # Geçici bir .txt dosyası oluştur
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            temp_path = f.name
        try:
            result = extractor.run({"FILE": temp_path, "VERBOSE": "false"})
            assert result is False
        finally:
            os.unlink(temp_path)

    @patch('modules.auxiliary.forensics.metadata_extractor.PIL_AVAILABLE', False)
    def test_run_no_pillow(self):
        """Pillow kurulu değilken çalıştırma testi."""
        extractor = MetadataExtractor()
        result = extractor.run({"FILE": "test.jpg", "VERBOSE": "false"})
        assert result is False

    def test_run_valid_image(self, extractor):
        """Geçerli bir görüntü dosyası ile çalıştırma testi."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow kurulu değil")

        # Basit bir test görseli oluştur
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name

        try:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(temp_path, format='PNG')
            img.close()

            result = extractor.run({"FILE": temp_path, "VERBOSE": "false"})
            assert result is True
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_gps_coordinate_conversion(self, extractor):
        """GPS koordinat dönüşüm testi."""
        gps_info = {
            'GPSLatitude': (41.0, 0.0, 50.4),
            'GPSLongitude': (28.0, 58.0, 59.64),
            'GPSLatitudeRef': 'N',
            'GPSLongitudeRef': 'E'
        }
        lat, lon = extractor._get_gps_coordinates(gps_info)
        assert lat is not None
        assert lon is not None
        assert lat > 0  # Kuzey yarımküre
        assert lon > 0  # Doğu yarımküre


class TestMetadataCleaner:
    @pytest.fixture
    def cleaner(self):
        return MetadataCleaner()

    def test_init(self, cleaner):
        """Modül başlatma testi."""
        assert cleaner.Name == "Metadata Cleaner"
        assert cleaner.Category == "auxiliary/forensics"
        assert cleaner.Author == "Mahmut P."
        assert "FILE" in cleaner.Options
        assert "OUTPUT" in cleaner.Options
        assert "BACKUP" in cleaner.Options

    def test_file_option_required(self, cleaner):
        """FILE parametresinin zorunlu olduğunu doğrula."""
        assert cleaner.Options["FILE"].required is True

    def test_output_option_not_required(self, cleaner):
        """OUTPUT parametresinin opsiyonel olduğunu doğrula."""
        assert cleaner.Options["OUTPUT"].required is False

    def test_backup_default(self, cleaner):
        """BACKUP parametresinin varsayılan olarak true olduğunu doğrula."""
        assert cleaner.Options["BACKUP"].value == "true"

    def test_run_empty_file(self, cleaner):
        """Boş FILE parametresi ile çalıştırma testi."""
        result = cleaner.run({"FILE": "", "OUTPUT": "", "BACKUP": "true"})
        assert result is False

    def test_run_nonexistent_file(self, cleaner):
        """Var olmayan dosya ile çalıştırma testi."""
        result = cleaner.run({"FILE": "/tmp/nonexistent_image.jpg", "OUTPUT": "", "BACKUP": "true"})
        assert result is False

    def test_run_unsupported_format(self, cleaner):
        """Desteklenmeyen format testi."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            temp_path = f.name
        try:
            result = cleaner.run({"FILE": temp_path, "OUTPUT": "", "BACKUP": "false"})
            assert result is False
        finally:
            os.unlink(temp_path)

    @patch('modules.auxiliary.forensics.metadata_cleaner.PIL_AVAILABLE', False)
    def test_run_no_pillow(self):
        """Pillow kurulu değilken çalıştırma testi."""
        cleaner = MetadataCleaner()
        result = cleaner.run({"FILE": "test.jpg", "OUTPUT": "", "BACKUP": "false"})
        assert result is False

    def test_run_clean_image(self, cleaner):
        """Geçerli bir görüntüden metadata temizleme testi."""
        try:
            from PIL import Image
            import piexif
        except ImportError:
            pytest.skip("Pillow veya piexif kurulu değil")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = f.name
        output_path = temp_path + "_clean.jpg"

        try:
            # EXIF verisi içeren bir JPEG oluştur
            img = Image.new('RGB', (100, 100), color='blue')
            exif_dict = {"0th": {piexif.ImageIFD.Make: b"TestCamera"}}
            exif_bytes = piexif.dump(exif_dict)
            img.save(temp_path, format='JPEG', exif=exif_bytes)
            img.close()

            result = cleaner.run({"FILE": temp_path, "OUTPUT": output_path, "BACKUP": "false"})
            assert result is True
            assert os.path.exists(output_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_backup_creation(self, cleaner):
        """Yedek dosya oluşturma testi."""
        try:
            from PIL import Image
            import piexif
        except ImportError:
            pytest.skip("Pillow veya piexif kurulu değil")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = f.name

        backup_path = temp_path + ".backup"

        try:
            # EXIF verisi içeren bir JPEG oluştur
            img = Image.new('RGB', (50, 50), color='green')
            exif_dict = {"0th": {piexif.ImageIFD.Make: b"TestCamera"}}
            exif_bytes = piexif.dump(exif_dict)
            img.save(temp_path, format='JPEG', exif=exif_bytes)
            img.close()

            # Üzerine yazma + backup
            result = cleaner.run({"FILE": temp_path, "OUTPUT": "", "BACKUP": "true"})
            assert result is True
            assert os.path.exists(backup_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists(backup_path):
                os.unlink(backup_path)
