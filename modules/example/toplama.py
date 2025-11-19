from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print 
class toplama(BaseModule):
    """Toplama işlemi yapmaya yarıyan fonksiyon.

    Args:
        BaseModule (_type_): Ana modül sınıfı.
    """
    Name =  "toplama"
    Description = "Toplama işlemi yapan örnek bir modül."
    Author= "Mahmut P."
    Category = "example"
    def __init__(self):
        """init fonksiyon.
        """
        super().__init__()
        self.Options = {
            "first_number": Option("first_number", None, True, "Toplanacak birinci sayı."),
            "second_number": Option("second_number", None, True, "Toplanacak ikinci sayı.")
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)

    def run(self, options: Dict[str, Any]):
        """Modül çalıştırılınca çalışacak fonksiyon.

        Args:
            options (Dict[str, Any]): option'ların listesi.
        """
        print(f"Modül: '{self.Name}'")
        print(f"Toplanacak birinci sayı: {options.get("first_number")}")
        print(f"Toplanacak ikinci sayı: {options.get("second_number")}")
        print(f"{options.get("first_number")} + {options.get("second_number")} = {int(options.get("first_number"))+int(options.get("second_number"))}")