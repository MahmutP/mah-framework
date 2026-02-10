# temel modül sınıfı, modül kodlanırken import edilip kullanılacak
from typing import Dict, Any, Union, List
from core.option import Option # yerleşik opsiyon eklenmesi için
class BaseModule:
    """Modüllerin ana sınıfı.

    Returns:
        _type_: _description_
    """
    Name: str = "Default Module Name" # modül adı, search ve show için
    Description: str = "description for module" # modül açıklaması, search ve show için
    Author: str = "Unknown" # kodlayanın adı
    Category: str = "uncategorized" # katagorisi tanımlanmazsa, katagorisizdir.
    Path: str = "" # modülün dosya yolu (örn: auxiliary/recon/github_tracker)
    Options: Dict[str, Option] = {} # core/option.py
    def __init__(self):
        """init fonksiyon.
        """
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)
    def run(self, options: Dict[str, Any]) -> Union[str, List[str], bool, None]: # modül çalıştırılması için çağrılacak fonksiyon.
        """Modül çalıştırılınca çalışacak fonksiyon.

        Args:
            options (Dict[str, Any]): option'lar. değiştirilebilir değişkenler.

        Returns:
            Union[str, List[str]]: _description_
        """
        return f"[{self.Name}] Modül çalışması tamamlandı (varsayılan)."
    def get_options(self) -> Dict[str, Option]: # options çağırmak için
        """Option çağırmaya yarayan fonksiyon.

        Returns:
            Dict[str, Option]: Option'lar ve objeleri.
        """
        return self.Options
    def get_option_value(self, option_name: str) -> Any: # opsiyon değişkenini içeride çağırmak için
        """Option değişkenlerini almak için kullanılan fonksiyon.

        Args:
            option_name (str): Option ismi.

        Returns:
            Any: Option değerleri.
        """
        option = self.Options.get(option_name)
        if option:
            return option.value
        return None
    def set_option_value(self, option_name: str, value: Any) -> bool: # moülün option'unu değiştirmek için
        """Option değiştirmek için kullanılan fonksiyon.

        Args:
            option_name (str): option ismi.
            value (Any): option değeri.

        Returns:
            bool: başarılı olup olmadığının sonucu.
        """
        option = self.Options.get(option_name)
        if option:
            option.value = value
            setattr(self, option_name, value)
            print(f"[{self.Name}] Option '{option_name}' set to '{value}'.")
            return True
        print(f"[{self.Name}] Option '{option_name}' bulunamadı.")
        return False
    def check_required_options(self) -> bool: # show komutunda zorunluluğunu belirlemek için
        """Zorunlu option belirlemek için kullanılıyor.

        Returns:
            bool: Zorunlu olup olmadığının kontrolünün sonucu.
        """
        missing_options = []
        for opt_name, opt_obj in self.Options.items():
            if opt_obj.required and (opt_obj.value is None or str(opt_obj.value).strip() == ""):
                missing_options.append(opt_name)
        if missing_options:
            return False
        return True
