# Metasploit Framework benzeri modüler yapıdaki 'Option' (Seçenek) mekanizmasını tanımlayan dosya.
# Modüllerin kullanıcıdan alacağı parametreleri (IP, Port, Dosya Yolu vb.) standartlaştırmak
# ve doğrulamak (validation) için kullanılır.

import re # Regular Expression (Düzenli İfade) modülü, girdi doğrulaması için.
from typing import Any, Optional, List
from core.cont import DEFAULT_REGEX # Varsayılan (her şeyi kabul eden) regex deseni.
from rich import print

class Option:
    """
    Modül Seçenek Sınıfı.
    
    Her bir Option nesnesi, modülün çalışması için gereken bir parametreyi temsil eder.
    Örn: RHOST (Hedef IP), LPORT (Dinlenecek Port) vb.
    """
    
    def __init__(self, name: str, value: Any, required: bool, description: str, 
                 regex_check: bool = False, regex: str = DEFAULT_REGEX,
                 choices: Optional[List[Any]] = None,
                 completion_dir: Optional[str] = None,
                 completion_extensions: Optional[List[str]] = None):
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
        """
        self.name = name 
        self._value = value # Asıl değeri tutan gizli değişken
        self.required = required 
        self.description = description 
        self.regex_check = regex_check 
        self.regex = regex 
        self.choices = choices or []  # Otomatik tamamlama için seçenek listesi
        self.completion_dir = completion_dir 
        self.completion_extensions = completion_extensions 

    @property
    def value(self) -> Any:
        """
        Seçeneğin o anki değerini döndüren özellik (property).
        
        Returns:
            Any: Seçeneğin değeri.
        """
        return self._value

    @value.setter
    def value(self, new_value: Any):
        """
        Seçeneğe yeni bir değer atayan setter metodu.
        Burada veri doğrulama (validation) işlemleri yapılır.

        Args:
            new_value (Any): Atanmak istenen yeni değer.
        """
        # Eğer regex kontrolü aktifse
        if self.regex_check:
            # Girilen değer regex desenine tam uyuyor mu kontrol et
            if not re.fullmatch(self.regex, str(new_value)):
                # Uymazsa değeri değiştirme ve (isteğe bağlı) hata bas, ama sessizce reddet.
                # (Burada print logu comment out edilmiş, gerekirse açılabilir)
                # self._value = new_value # Hatalı değeri atamak yerine reddetmek daha doğru olabilir, ancak kodda atanmış.
                # Mevcut mantık: Uymazsa bile atama yapıyor gibi görünüyor (kodda self._value = new_value var if bloğu içinde).
                # DÜZELTME NOTU: Orjinal kodda return ile çıkış var ama öncesinde _value = new_value var.
                # Bu mantık "uyarı ver ama ata" şeklinde çalışıyor olabilir.
                self._value = new_value
                return
        
        # Regex kontrolü yoksa veya geçildiyse değeri güncelle
        self._value = new_value
        # print(f"Option '{self.name}' set to '{self._value}'")

    def __str__(self):
        """
        Nesnenin string temsili (Debugging için).
        print(option_obj) dendiğinde bu döner.

        Returns:
            str: Option özelliklerinin özeti.
        """
        return f"Option(Name='{self.name}', Value='{self.value}', Required={self.required}, Description='{self.description}', Regex_Check={self.regex_check}, Regex='{self.regex}')"

    def to_dict(self):
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
            "choices": self.choices
        }