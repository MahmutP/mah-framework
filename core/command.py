#command sınıfı, temel komut sınıfı kodlandı burada.
from typing import List, Dict, Any, Callable, Optional # çok işe yarıyor bu kütüphane.
from core.shared_state import shared_state # bu çok iyi oldu.
from core.cont import COMMAND_CATEGORIES
from rich import print
class Command:
    """Ana komut sınıfı.

    Returns:
        _type_: _description_
    """
    Name: str = "COMMAND" # komut adı
    Description: str = "Description for command" # komut açıklaması
    Category: str = "core" # komut açıklaması
    Aliases: List[str] = [] # aliases.json dan bağımsız olarakta alias atama imkanı verildi
    completer_function: Optional[Callable] = None  # prompt-toolkit üzerinden otomatik tamamlama için
    def __init__(self):
        self.shared_state = shared_state
    def execute(self, *args: str, **kwargs: Any) -> bool: # çalıştır.
        # komut çalıştırmak için, ara işlem tanımlamadı
        return True
    def get_category_display_name(self) -> str:# katagori verisi verecek.
        # eğer katagör,s, yoksa diğer komutlar katagorisinde tanımlanacak.
        return COMMAND_CATEGORIES.get(self.Category.lower(), "Diğer Komutlar")
    def get_completions(self, text: str, word_before_cursor: str) -> List[str]:
        # otomatik tamamlaa için
        if self.completer_function:
            try:
                return self.completer_function(text, word_before_cursor)
            except Exception as e:
                print(f"Komut '{self.Name}' tamamlama fonksiyonunda hata: {e}")
                return []
        return []
