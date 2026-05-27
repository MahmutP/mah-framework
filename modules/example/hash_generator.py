# =============================================================================
# ÖRNEK MODÜL - Modül Geliştirme Rehberi
# =============================================================================
#
# Bu dosya, Mah Framework için modül geliştirmek isteyen yazılımcılara
# rehberlik etmek amacıyla hazırlanmış kapsamlı bir örnek modüldür.
#
# 📚 MODÜL GELİŞTİRME ADIMLARI:
#
#   1. Bu dosyayı kopyalayın: modules/<kategori>/<modül_adı>.py
#   2. Sınıf adını değiştirin (dosya adıyla aynı olmasına gerek yok)
#   3. Meta bilgileri güncelleyin (Name, Description, Author, Category)
#   4. İhtiyacınız olan Options'ları tanımlayın
#   5. run() metodunu yazın
#   6. Test edin: use <kategori>/<modül_adı>
#
# 📁 MODÜL KATEGORİLERİ:
#   - exploit     : Zafiyet sömürme modülleri
#   - auxiliary   : Yardımcı modüller (scanner, dos, fuzzer vb.)
#   - post        : Exploitation sonrası modüller
#   - payloads    : Payload modülleri
#   - example     : Örnek ve eğitim modülleri
#   - (özel)      : Kendi kategorinizi oluşturabilirsiniz
#
# ⚠️ ÖNEMLİ NOTLAR:
#   - Modül dosyası modules/ klasörü altında olmalı
#   - Sınıf BaseModule'den miras almalı
#   - run() metodu zorunludur
#   - Options dict'i __init__ içinde tanımlanmalı
#
# =============================================================================

# -----------------------------------------------------------------------------
# 1. GEREKLİ IMPORTLAR
# -----------------------------------------------------------------------------
# Her modülde bu import'lar standart olarak bulunmalıdır.

# Modülünüze özel import'lar:
import hashlib
from typing import Any  # Type hints için

from rich import print  # Renkli çıktı için (ÖNERİLEN)
from rich.table import Table  # Tablo çıktısı için (OPSİYONEL)

from core import logger  # Loglama için (ÖNERİLEN)
from core.module import BaseModule  # Ana modül sınıfı (ZORUNLU)
from core.option import Option  # Seçenek tanımlamak için (ZORUNLU)

# -----------------------------------------------------------------------------
# 2. MODÜL SINIFI TANIMI
# -----------------------------------------------------------------------------
# Sınıf adı önemli değil, ama dosya adıyla tutarlı olması önerilir.
# BaseModule'den miras almak ZORUNLUDUR.


class hash_generator(BaseModule):
    """Hash Oluşturucu Modülü - Örnek Modül

    Bu modül, verilen bir metni çeşitli hash algoritmalarıyla şifreler.
    Modül geliştirme sürecini öğrenmek için ideal bir örnektir.

    Kullanım:
        1. use example/hash_generator
        2. set TEXT "şifrelenecek metin"
        3. set ALGORITHM sha256
        4. run

    Desteklenen Algoritmalar:
        md5, sha1, sha256, sha384, sha512

    Attributes:
        Name: Modülün görünen adı
        Description: Kısa açıklama
        Author: Geliştirici
        Category: Modül kategorisi
        Options: Kullanıcı tarafından ayarlanabilir seçenekler
    """

    # -------------------------------------------------------------------------
    # 3. META BİLGİLER (Sınıf Değişkenleri)
    # -------------------------------------------------------------------------
    # Bu bilgiler 'info' ve 'show modules' komutlarında görünür.

    Name = "Hash Generator"  # Modül adı
    Description = "Metin için hash değeri oluşturur"  # Kısa açıklama
    Author = "Mahmut P."  # Yazar
    Category = "example"  # Kategori

    # -------------------------------------------------------------------------
    # 4. CONSTRUCTOR (__init__)
    # -------------------------------------------------------------------------

    def __init__(self):
        """Modül başlatıcı - Options tanımlaması yapılır.

        super().__init__() çağrısı ZORUNLUDUR!

        Options dict'i burada tanımlanır. Her option için:
            - name: Option adı (büyük harf önerilir)
            - value: Varsayılan değer
            - required: Zorunlu mu? (True/False)
            - description: Kullanıcı için açıklama
            - regex_check: Değer doğrulaması (opsiyonel)
            - regex: Doğrulama regex'i (opsiyonel)
        """
        super().__init__()  # ZORUNLU: Parent sınıfın __init__'i

        # Desteklenen algoritmalar (internal kullanım için)
        self.algorithms = ["md5", "sha1", "sha256", "sha384", "sha512"]

        # Options tanımlaması
        self.Options = {
            # ZORUNLU BİR OPTION ÖRNEĞİ
            "TEXT": Option(
                name="TEXT",
                value="",  # Varsayılan boş
                required=True,  # ZORUNLU
                description="Hash'lenecek metin",
            ),
            # CHOICES (OTOMATİK TAMAMLAMA) İLE OPTION ÖRNEĞİ
            "ALGORITHM": Option(
                name="ALGORITHM",
                value="sha256",  # Varsayılan değer
                required=False,  # Zorunlu değil
                description="Hash algoritması",
                choices=[
                    "md5",
                    "sha1",
                    "sha256",
                    "sha384",
                    "sha512",
                ],  # TAB ile önerilir
            ),
            # BOOLEAN OPTION ÖRNEĞİ
            "UPPERCASE": Option(
                name="UPPERCASE",
                value="false",
                required=False,
                description="Hash çıktısını büyük harfle göster (true/false)",
            ),
            # REGEX DOĞRULAMALI OPTION ÖRNEĞİ (sayısal değer)
            "ITERATIONS": Option(
                name="ITERATIONS",
                value=1,
                required=False,
                description="Hash kaç kez tekrarlansın",
                regex_check=True,  # Doğrulama aktif
                regex=r"^\d+$",  # Sadece rakam
            ),
        }

        # Options'ları instance attribute olarak ayarla (opsiyonel ama kullanışlı)
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    # -------------------------------------------------------------------------
    # 5. YARDIMCI METODLAR (Private Methods)
    # -------------------------------------------------------------------------
    # İsimlendirme: _metod_adi (alt çizgi ile başlar)

    def _calculate_hash(self, text: str, algorithm: str) -> str:
        """Verilen metni belirtilen algoritma ile hash'ler.

        Args:
            text: Hash'lenecek metin
            algorithm: Kullanılacak algoritma

        Returns:
            Hash değeri (hexadecimal string)

        Raises:
            ValueError: Geçersiz algoritma
        """
        algorithm = algorithm.lower()

        if algorithm not in self.algorithms:
            raise ValueError(f"Geçersiz algoritma: {algorithm}")

        # Hash hesaplama
        hash_func = getattr(hashlib, algorithm)
        return hash_func(text.encode("utf-8")).hexdigest()

    def _validate_algorithm(self, algorithm: str) -> bool:
        """Algoritmanın geçerli olup olmadığını kontrol eder.

        Args:
            algorithm: Kontrol edilecek algoritma adı

        Returns:
            Geçerli ise True, değilse False
        """
        return algorithm.lower() in self.algorithms

    # -------------------------------------------------------------------------
    # 6. ANA ÇALIŞTIRMA METODU (run)
    # -------------------------------------------------------------------------
    # Bu metod ZORUNLUDUR! Modül çalıştırıldığında bu metod çağrılır.

    def run(self, options: dict[str, Any]) -> bool:
        """Modülün ana çalıştırma metodu.

        Bu metod 'run' komutu ile çağrılır. Tüm modül mantığı burada
        veya bu metodun çağırdığı yardımcı metodlarda olmalıdır.

        Args:
            options: Kullanıcının ayarladığı seçenekler dict'i
                     Örnek: {"TEXT": "hello", "ALGORITHM": "md5", ...}

        Returns:
            bool: Başarılı ise True, hata oluşursa False

        Not:
            - options.get("KEY") ile değerlere erişin
            - Varsayılan değer için: options.get("KEY", default_value)
            - Hataları try/except ile yakalayın
            - logger.info/warning/error ile log tutun
        """

        # Options'lardan değerleri al
        text = options.get("TEXT", "")
        algorithm = options.get("ALGORITHM", "sha256")
        uppercase = str(options.get("UPPERCASE", "false")).lower() == "true"
        iterations = int(options.get("ITERATIONS", 1))

        # ------------------------------------------------------------------
        # ZORUNLU ALAN KONTROLÜ
        # ------------------------------------------------------------------
        if not text:
            print("[bold red]Hata:[/bold red] TEXT parametresi boş olamaz!")
            print('Kullanım: set TEXT "hash\'lenecek metin"')
            return False

        # ------------------------------------------------------------------
        # GİRDİ DOĞRULAMA
        # ------------------------------------------------------------------
        if not self._validate_algorithm(algorithm):
            print(f"[bold red]Hata:[/bold red] Geçersiz algoritma: {algorithm}")
            print(f"Desteklenen algoritmalar: {', '.join(self.algorithms)}")
            return False

        if iterations < 1:
            print("[bold red]Hata:[/bold red] ITERATIONS en az 1 olmalıdır.")
            return False

        # ------------------------------------------------------------------
        # LOGLAMA
        # ------------------------------------------------------------------
        logger.info(f"Hash hesaplanıyor: algoritma={algorithm}, iterasyon={iterations}")

        # ------------------------------------------------------------------
        # ANA İŞLEM
        # ------------------------------------------------------------------
        try:
            print("\n[bold cyan]🔐 Hash Generator[/bold cyan]\n")
            print(f"[dim]Metin:[/dim] {text[:50]}{'...' if len(text) > 50 else ''}")
            print(f"[dim]Algoritma:[/dim] {algorithm.upper()}")
            print(f"[dim]İterasyon:[/dim] {iterations}")
            print()

            # Hash hesapla
            current_hash = text
            for i in range(iterations):
                current_hash = self._calculate_hash(current_hash, algorithm)

            # Büyük harf dönüşümü
            if uppercase:
                current_hash = current_hash.upper()

            # ------------------------------------------------------------------
            # SONUÇ ÇIKTISI
            # ------------------------------------------------------------------
            # Rich Table kullanarak güzel bir çıktı
            table = Table(title="Hash Sonucu", border_style="green")
            table.add_column("Özellik", style="cyan")
            table.add_column("Değer", style="white")

            table.add_row("Algoritma", algorithm.upper())
            table.add_row("Hash Uzunluğu", f"{len(current_hash)} karakter")
            table.add_row("Hash Değeri", current_hash)

            print(table)

            # Başarılı log
            logger.info(f"Hash başarıyla hesaplandı: {algorithm}")

            return True  # Başarılı

        except Exception as e:
            # ------------------------------------------------------------------
            # HATA YÖNETİMİ
            # ------------------------------------------------------------------
            print(
                f"[bold red]Hata:[/bold red] Hash hesaplanırken bir sorun oluştu: {e}"
            )
            logger.exception("Hash hesaplama hatası")
            return False  # Başarısız


# =============================================================================
# MODÜL GELİŞTİRME KONTROL LİSTESİ
# =============================================================================
#
# ☐ BaseModule'den miras alındı mı?
# ☐ Name, Description, Author, Category tanımlandı mı?
# ☐ __init__ içinde super().__init__() çağrıldı mı?
# ☐ Options dict'i tanımlandı mı?
# ☐ run() metodu var mı ve bool dönüyor mu?
# ☐ Girdi doğrulaması yapıldı mı?
# ☐ Hata yönetimi (try/except) eklendi mi?
# ☐ Loglama eklendi mi?
# ☐ Docstring'ler yazıldı mı?
# ☐ Test edildi mi?
#
# =============================================================================
