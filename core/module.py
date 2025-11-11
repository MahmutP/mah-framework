# temel modül sınıfı, modül kodlanırken import edilip kullanılacak
from typing import Dict, Any, Union, List
from core.option import Option # yerleşik opsiyon eklenmesi için
class BaseModule:
    Name: str = "Default Module Name" # modül adı, search ve show için
    Description: str = "description for module" # modül açıklaması, search ve show için
    Author: str = "Unknown" # kodlayanın adı
    Category: str = "uncategorized" # katagorisi tanımlanmazsa, katagorisizdir.
    Options: Dict[str, Option] = {} # core/option.py
    def __init__(self):
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)
    def run(self, options: Dict[str, Any]) -> Union[str, List[str]]: # modül çalıştırılması için çağrılacak fonksiyon.
        return f"[{self.Name}] Modül çalışması tamamlandı (varsayılan)."
    def get_options(self) -> Dict[str, Option]: # options çağırmak için
        return self.Options
    def get_option_value(self, option_name: str) -> Any: # opsiyon değişkenini içeride çağırmak için
        option = self.Options.get(option_name)
        if option:
            return option.value
        return None
    def set_option_value(self, option_name: str, value: Any) -> bool: # moülün option'unu değiştirmek için
        option = self.Options.get(option_name)
        if option:
            option.value = value
            setattr(self, option_name, value)
            print(f"[{self.Name}] Option '{option_name}' set to '{value}'.")
            return True
        print(f"[{self.Name}] Option '{option_name}' bulunamadı.")
        return False
    def check_required_options(self) -> bool: # show komutunda zorunluluğunu belirlemek için
        missing_options = []
        for opt_name, opt_obj in self.Options.items():
            if opt_obj.required and (opt_obj.value is None or str(opt_obj.value).strip() == ""):
                missing_options.append(opt_name)
        if missing_options:
            return False
        return True
