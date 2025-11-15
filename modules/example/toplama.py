from typing import Dict, Any
from core.module import BaseModule
from core.option import Option
from rich import print
class topla(BaseModule):
    Name =  "topla"
    Description = "Bu bir deneme modülü."
    Author= "Mahmut P."
    Category = "example"
    def __init__(self):
        super().__init__()
        self.Options = {
            "first_number": Option("first_number", None, True, "Toplanacak birinci sayı."),
            "second_number": Option("second_number", None, True, "Toplanacak ikinci sayı.")
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)
    def run(self, options: Dict[str, Any]):
        print(f"Modül: '{self.Name}'")
        print(f"Toplanacak birinci sayı: {options.get("first_number")}")
        print(f"Toplanacakl ikinci sayı: {options.get("second_number")}")
        print(f"{options.get("first_number")} + {options.get("second_number")} = {int(options.get("first_number"))+int(options.get("second_number"))}")