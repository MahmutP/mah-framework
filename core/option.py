# metasploit framework yapısındaki optons yapısına benzer amaçla oluşturuldu.
# framework içindeki yapılar için kullanacak bir kütüphane
# asıl hedefi modüllere(modules dizinindeki) değiştirilebilir option eklemek birincil hedefi
import re # doğrulama ve tanımlama için regex
from typing import Any, Optional, List
from core.cont import DEFAULT_REGEX # ön tanımlı regex
from rich import print
class Option:
    """değiştirilebilir opsiyonlar tanımlamak için kullanılan ana sınıf.
    """
    def __init__(self, name: str, value: Any, required: bool, description: str, 
                 regex_check: bool = False, regex: str = DEFAULT_REGEX,
                 choices: Optional[List[Any]] = None):
        """init fonksiyon.

        Args:
            name (str): option adı.
            value (Any): option değeri.
            required (bool): zorunlu olup olmadığının belirtilemesi.
            description (str): Açıklaması.
            regex_check (bool, optional): regex kontrolü yapılsın mı onun belirtilmesi. Defaults to False.
            regex (str, optional): regex. Defaults to DEFAULT_REGEX.
            choices (list, optional): Otomatik tamamlama için önceden tanımlı değerler. Defaults to None.
        """
        self.name = name # obje ismi
        self._value = value # option'un değeri, değiştirilecek olan
        self.required = required # zorunlu bir opsiyon mu? değil mi?
        self.description = description # o opsiyonun açıklaması
        self.regex_check = regex_check # regex kontrolü yapılacak mı?
        self.regex = regex 
        self.choices = choices or []  # Otomatik tamamlama seçenekleri 
    @property
    def value(self) -> Any: # değişken, her türlü type sahip değişken tanımlanabilir
        """Değişken. her türlü değişken tipini kabul ediyor.

        Returns:
            Any: değişken değeri.
        """
        return self._value
    @value.setter
    def value(self, new_value: Any): # value ana fonksiyonu
        """Değişken değişimi sağlayan ana fonksiyon.

        Args:
            new_value (Any): Yeni değer.
        """
        if self.regex_check:
            if not re.fullmatch(self.regex, str(new_value)):
                #print(f"'{self.name}' seçeneği için '{new_value}' değeri, '{self.regex}' regex'ine uymuyor.")
                self._value = new_value
                return
        self._value = new_value
        #print(f"Option '{self.name}' set to '{self._value}'")
    def __str__(self): # bunu "io" dan ilham alarak ekledim
        """Option direkt çağrıldığında verilecek string.

        Returns:
            _type_: verilen string.
        """
        return f"Option(Name='{self.name}', Value='{self.value}', Required={self.required}, Description='{self.description}', Regex_Check={self.regex_check}, Regex='{self.regex}')"

    def to_dict(self): # dict çıktısı, işlemede kolaylık sağlayacak
        """Liste olarak option verileri.

        Returns:
            _type_: Liste.
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