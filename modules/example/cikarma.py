from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print

class cikarma(BaseModule):
    """Çıkarma işlemi yapmaya yarıyan örnek bir modül.

    Args:
        BaseModule (_type_): Ana komut sınıfı.
    """
    Name = "cikarma"
    Description = "Çıkarma işlemi yapmaya yarıyan örnek bir modül."
    Author = "Mahmut P."
    Category = "example"
    def __init__(self):
        """init fonksiyon.
        """
        super().__init__()
        self.Options = {
            "first_number": Option("first_number", None, True, "Çıkarılacak birinci sayı."),
            "second_number": Option("second_number", None, True, "Çıkarılacak ikinci sayı.")
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    def run(self, options: Dict[str, Any]):
        """Modül çalışınca çalışacak fonksiyon

        Args:
            options (Dict[str, Any]): işlenecek Option'lar
        """
        print(f"Modül: '{self.Name}'")
        print(f"Çıkarılacak birinci sayı: {options.get("first_number")}")
        print(f"Çıkarılacak ikinci sayı: {options.get("second_number")}")
        val1 = options.get("first_number")
        val2 = options.get("second_number")
        if val1 and val2:
             print(f"{val1} - {val2} = {int(val1)-int(val2)}")
        else:
             print("Lütfen tüm sayıları giriniz.")
