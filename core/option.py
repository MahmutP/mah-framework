# Metasploit Framework benzeri modüler yapıdaki 'Option' (Seçenek) mekanizmasını tanımlayan dosya.
# Modüllerin kullanıcıdan alacağı parametreleri (IP, Port, Dosya Yolu vb.) standartlaştırmak
# ve doğrulamak (validation) için kullanılır.

import re  # Regular Expression (Düzenli İfade) modülü, girdi doğrulaması için.
from collections.abc import Callable
from typing import Any

from rich import print

from core.cont import DEFAULT_REGEX  # Varsayılan (her şeyi kabul eden) regex deseni.


def ensure_url_scheme(value: Any) -> Any:
    """Şemasız URL girdilerine ``http://`` ekleyen normalizer.

    Doğrulamadan *önce* çalışır; böylece ``kurs.example.com`` gibi bir giriş
    ``^https?://.+`` regex'ine takılmaz. Diğer şemalara (``ftp://`` vb.)
    dokunmaz — onların regex tarafından reddedilmesi gerekir.

    ``None`` (unset akışı) ve boş değerler olduğu gibi bırakılır.
    """
    if value is None:
        return value
    text = str(value).strip()
    if not text:
        return text
    if text.startswith("//"):  # protokol-relatif → http
        return "http:" + text
    if "://" not in text:
        return f"http://{text}"
    return text


class Option:
    """
    Modül Seçenek Sınıfı.

    Her bir Option nesnesi, modülün çalışması için gereken bir parametreyi temsil eder.
    Örn: RHOST (Hedef IP), LPORT (Dinlenecek Port) vb.
    """

    def __init__(
        self,
        name: str,
        value: Any,
        required: bool,
        description: str,
        regex_check: bool = False,
        regex: str = DEFAULT_REGEX,
        choices: list[Any] | None = None,
        completion_dir: str | None = None,
        completion_extensions: list[str] | None = None,
        normalizer: Callable[[Any], Any] | None = None,
    ):
        """
        Option nesnesini başlatır.

        Args:
            name (str): Seçeneğin adı (Genellikle büyük harf: RHOST, THREADS).
            value (Any): Varsayılan değer. None olabilir.
            required (bool): Bu seçeneğin doldurulması zorunlu mu? (True/False)
            description (str): Kullanıcıya gösterilecek açıklama metni.
            regex_check (bool, optional): Değer atanırken regex kontrolü yapılsın mı? Varsayılan: False.
            regex (str, optional): Regex kontrolü yapılacaksa kullanılacak desen.
            choices (list, optional): Kullanıcının seçebileceği ön tanımlı değerler listesi (Enum gibi).
            completion_dir (str, optional): Dosya yolu tamamlaması için varsayılan dizin.
            completion_extensions (list, optional): Dosya tamamlamada sadece bu uzantıları göster (örn: ['.txt']).
            normalizer (Callable, optional): Doğrulamadan önce değeri dönüştüren fonksiyon
                (örn: şemasız URL'lere 'http://' eklemek).
        """
        self.name = name
        self._value = value  # Asıl değeri tutan gizli değişken
        self.required = required
        self.description = description
        self.regex_check = regex_check
        self.regex = regex
        self.choices = choices or []  # Otomatik tamamlama için seçenek listesi
        self.completion_dir = completion_dir
        self.completion_extensions = completion_extensions
        self.normalizer = normalizer

    @property
    def value(self) -> Any:
        """
        Seçeneğin o anki değerini döndüren özellik (property).

        Returns:
            Any: Seçeneğin değeri.
        """
        return self._value

    def set_value(self, new_value: Any) -> bool:
        """Değeri (varsa normalizer ile dönüştürüp) doğrular ve uygular.

        Doğrulama başarısız olduğunda mevcut değer korunur ve ayrıntılı bir
        hata mesajı basılır. ``value`` setter'ı da bu metodu kullanır.

        Args:
            new_value (Any): Atanmak istenen yeni değer.

        Returns:
            bool: Değer uygulandıysa True, reddedildiyse False.
        """
        if self.normalizer is not None:
            new_value = self.normalizer(new_value)

        # None: 'unset' akışı — regex'e sokmadan kabul et. Zorunluluk kontrolü
        # çalışma zamanında check_required_options() tarafından yapılır.
        if (
            new_value is not None
            and self.regex_check
            and not re.fullmatch(self.regex, str(new_value))
        ):
            hint = ""
            if "https?" in self.regex:
                hint = " (http:// veya https:// ile başlamalı; örn: http://example.com)"
            print(
                f"[bold red]Hata:[/bold red] '{new_value}' değeri '{self.name}' "
                f"için geçersiz — beklenen format: {self.regex}{hint}. "
                f"Değişiklik uygulanmadı, mevcut değer korundu: '{self._value}'."
            )
            return False

        self._value = new_value
        return True

    @value.setter
    def value(self, new_value: Any) -> None:
        """Setter: doğrulamayı ``set_value`` üzerinden yapar (eski davranış korunur)."""
        self.set_value(new_value)

    def __str__(self) -> str:
        """
        Nesnenin string temsili (Debugging için).
        print(option_obj) dendiğinde bu döner.

        Returns:
            str: Option özelliklerinin özeti.
        """
        return f"Option(Name='{self.name}', Value='{self.value}', Required={self.required}, Description='{self.description}', Regex_Check={self.regex_check}, Regex='{self.regex}')"

    def to_dict(self) -> dict:
        """
        Option nesnesini Python sözlüğüne (dictionary) çevirir.
        API yanıtları veya JSON serileştirme (kaydetme) işlemleri için kullanışlıdır.

        Returns:
            dict: Option verilerini içeren sözlük.
        """
        return {
            "name": self.name,
            "value": self.value,
            "required": self.required,
            "description": self.description,
            "regex_check": self.regex_check,
            "regex": self.regex,
            "choices": self.choices,
        }
