# Framework içindeki tüm modüllerin (exploit, scanner, auxiliary vb.) türetilmesi gereken temel sınıf.
# Bu dosya, bir modülün sahip olması gereken standart yapıyı, özellikleri ve metodları tanımlar.

from typing import Dict, Any, Union, List
from core.option import Option # Modül seçeneklerini (LHOST, RPORT vb.) tanımlamak için kullanılan sınıf.

class BaseModule:
    """
    Modüllerin Ana (Base) Sınıfı.
    
    Her yeni modül bu sınıftan miras almalı ve gerekli özellikleri (Name, Description vb.) doldurmalıdır.
    Ayrıca 'run' metodunu kendi iş mantığına göre eze (override) etmelidir.
    """
    
    # ==============================================================================
    # Modül Metadata (Kimlik) Bilgileri
    # ==============================================================================
    
    # Modülün adı. 'search' ve 'list' komutlarında görünür.
    Name: str = "Default Module Name" 
    
    # Modülün ne işe yaradığını anlatan kısa açıklama. 'info' komutunda görünür.
    Description: str = "description for module" 
    
    # Modülü geliştiren kişinin adı veya takma adı.
    Author: str = "Unknown" 
    
    # Modülün kategorisi (örn: exploit, scanner, auxiliary).
    # Eğer tanımlanmazsa 'uncategorized' olarak işaretlenir.
    Category: str = "uncategorized" 
    
    # Modülün dosya sistemindeki yolu (örn: auxiliary/recon/github_tracker).
    # Bu değer ModuleManager tarafından otomatik atanır, manuel doldurulmasına gerek yoktur.
    Path: str = "" 
    
    # Modülün çalışması için gereken seçenekler (ayarlar).
    # Sözlük formatındadır: {"SEÇENEK_ADI": Option(...)}
    Options: Dict[str, Option] = {} 

    def __init__(self):
        """
        Modül sınıfının başlatıcı metodu.
        Tanımlanan 'Options' sözlüğündeki varsayılan değerleri sınıf özelliklerine (attribute) dönüştürür.
        Örneğin Options={"RHOST": Option("127.0.0.1")} ise, self.RHOST = "127.0.0.1" olur.
        """
        for option_name, option_obj in self.Options.items():
            # Seçenek adını ve varsayılan değerini sınıf özelliği olarak ata.
            setattr(self, option_name, option_obj.value)

    def run(self, options: Dict[str, Any]) -> Union[str, List[str], bool, None]:
        """
        Modülün asıl işi yaptığı ana metod.
        Kullanıcı 'run' veya 'exploit' komutunu çalıştırdığında bu metod çağrılır.
        Her modül bu metodu kendi mantığına göre KESİNLİKLE ezmelidir (override).

        Args:
            options (Dict[str, Any]): Kullanıcı tarafından ayarlanan güncel seçenek değerleri.

        Returns:
            Modülün dönüş değeri (Rapor, başarı durumu vb. olabilir).
        """
        # Varsayılan davranış: Sadece bir mesaj döndür.
        return f"[{self.Name}] Modül çalışması tamamlandı (varsayılan)."

    def get_options(self) -> Dict[str, Option]:
        """
        Modülün sahip olduğu tüm seçenekleri (Options) ve bunların yapılandırmalarını döndürür.
        'show options' komutu tarafından kullanılır.

        Returns:
            Dict[str, Option]: Seçenek adı ve Option nesnesi eşleşmesi.
        """
        return self.Options

    def get_option_value(self, option_name: str) -> Any:
        """
        Belirli bir seçeneğin o anki değerini döndürür.

        Args:
            option_name (str): Değeri istenen seçeneğin adı (örn: 'RHOST').

        Returns:
            Any: Seçeneğin değeri veya bulunamazsa None.
        """
        option = self.Options.get(option_name)
        if option:
            return option.value
        return None

    def set_option_value(self, option_name: str, value: Any) -> bool:
        """
        Bir seçeneğin değerini günceller.
        'set OPTION VALUE' komutu kullanıldığında bu metod çalışır.

        Args:
            option_name (str): Değiştirilecek seçeneğin adı.
            value (Any): Yeni değer.

        Returns:
            bool: İşlem başarılıysa True, seçenek bulunamazsa False.
        """
        option = self.Options.get(option_name)
        if option:
            # Option nesnesinin değerini güncelle
            option.value = value
            # Sınıf attribute'unu da güncelle (self.RHOST gibi erişimler için)
            setattr(self, option_name, value)
            print(f"[{self.Name}] Option '{option_name}' set to '{value}'.")
            return True
        
        print(f"[{self.Name}] Option '{option_name}' bulunamadı.")
        return False

    def check_required_options(self) -> bool:
        """
        Modül çalıştırılmadan önce, tüm zorunlu (required) seçeneklerin
        dolu olup olmadığını kontrol eder.

        Returns:
            bool: Tüm zorunlu seçenekler doluysa True, eksik varsa False.
        """
        missing_options = []
        for opt_name, opt_obj in self.Options.items():
            # Eğer seçenek zorunluysa VE (değeri yoksa VEYA boş string ise)
            if opt_obj.required and (opt_obj.value is None or str(opt_obj.value).strip() == ""):
                missing_options.append(opt_name)
        
        # Eksik seçenek varsa False dön
        if missing_options:
            return False
            
        return True
