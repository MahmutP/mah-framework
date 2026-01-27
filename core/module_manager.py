# modül kontrolü, işlemesi ve framework içi kullanılması ve 3. taraf modül desteği ile kullanımı içinimport os
import importlib.util # modülleri işlemek için
from typing import Dict, Optional, Tuple
from core.module import BaseModule # temel modül sınıfı
from core.module import BaseModule # temel modül sınıfı
from rich import print
from core import logger
import os
class ModuleManager:
    def __init__(self, modules_dir="modules"):
        """init fonksiyon.

        Args:
            modules_dir (str, optional): Modüllerin bulunduğu klasör. Defaults to "modules".
        """
        self.modules_dir = modules_dir # modüllerin bulunduğu dizin
        self.modules: Dict[str, BaseModule] = {} # framework içi global modül dcit'i 
    def load_modules(self):# modülleri import edecek ana fonksiyon
        """Modül yükleyici ana fonksiyon.
        """
        self.modules.clear() 
        #("Modüller yükleniyor...")
        for root, _, files in os.walk(self.modules_dir): # "modül_katagorisi/falan.py"-"modül_katagorisi/falan/filan.py" şeklinde işlenmesi için
            for file in files:
                if file.endswith(".py") and file != "__init__.py": # şimdilik sadece python destekliyor, ileride C/C++ desteği gelebilir.
                    module_path = os.path.join(root, file)
                    relative_path = os.path.relpath(module_path, self.modules_dir)
                    module_name_for_dict = relative_path.replace(os.sep, '/')[:-3] 
                    try:
                        spec = importlib.util.spec_from_file_location(module_name_for_dict, module_path)
                        if spec is None:
                            print(f"Modül spesifikasyonu alınamadı: {module_path}")
                            continue
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        for name, obj in module.__dict__.items():
                            if isinstance(obj, type) and issubclass(obj, BaseModule) and obj is not BaseModule:
                                module_instance = obj()
                                if not module_instance.Category:
                                    module_instance.Category = "uncategorized"
                                self.modules[module_name_for_dict] = module_instance 
                                #(f"Modül yüklendi: {module_name_for_dict} (Kategori: {module_instance.Category})")
                                break 
                    except Exception as e:
                        print(f"Modül yüklenirken hata oluştu '{module_path}': {e}")
                        logger.error(f"Modül yüklenirken hata oluştu '{module_path}': {e}")
        logger.info(f"{len(self.modules)} modül yüklendi")
    def get_module(self, module_path: str) -> Optional[BaseModule]: # modül/modül yolu çağırılması için
        """Modül çekici fonksiyon.

        Args:
            module_path (str): Modül yolu.

        Returns:
            Optional[BaseModule]: Modül objesi.
        """
        return self.modules.get(module_path)
    def get_all_modules(self) -> Dict[str, BaseModule]: # bütün modülleri çekmek için
        """Bütün modülleri çekmeye yarıyan fonksiyon.

        Returns:
            Dict[str, BaseModule]: bütün modüllerin liste ve obje yapısı.
        """
        return self.modules
    def get_modules_by_category(self) -> Dict[str, Dict[str, BaseModule]]: # listeleme ve kullanmak için katagorize ederek listeleyecek fonksiyon
        """Kategorize ederek modül çeken fonksiyon

        Returns:
            Dict[str, Dict[str, BaseModule]]: kategorize edilmiş şekilde çekilmiş modüllerin listesi ve objeleri.
        """
        categorized_modules = {}
        for module_path, module_obj in self.modules.items():
            category = module_obj.Category.capitalize() 
            if category not in categorized_modules:
                categorized_modules[category] = {}
            categorized_modules[category][module_path] = module_obj
        return categorized_modules
    def run_module(self, module_path: str) -> bool: # seçilen modülü çekip çalıştıracak fonksiyon
        """Modül çalıştırmaya yarıyan fonksiyon.

        Args:
            module_path (str): modül yolu.

        Returns:
            bool: Modül başarılı olup olmadığının kontrolü.
        """
        module = self.get_module(module_path)
        if not module:
            print(f"Modül bulunamadı: {module_path}")
            logger.warning(f"Modül bulunamadı: {module_path}")
            return False
        if not module.check_required_options():
            logger.warning(f"Modül çalıştırılamadı (eksik seçenekler): {module_path}")
            return False
        try:
            current_options = {name: opt.value for name, opt in module.get_options().items()}
            logger.info(f"Modül çalıştırılıyor: {module_path}")
            module.run(current_options)
            return True
        except Exception as e:
            print(f"Modül çalıştırılırken kritik hata oluştu '{module_path}': {e}")
            logger.error(f"Modül çalıştırılırken hata '{module_path}': {e}")
            return False
    def get_module_info(self, module_path: str) -> Optional[Tuple[str, str, str, str]]: # modül bilgisi çağırmak için, birincil kullanımı search ve show komutu ile kullanılması
        """modül bilgisi çekmeye yarıyan fonksiyon.

        Args:
            module_path (str): modül yolu.

        Returns:
            Optional[Tuple[str, str, str, str]]: Modül bilgisini bulunduğu liste.
        """
        module = self.get_module(module_path)
        if module:
            return (module.Name, module.Description, module.Author, module.Category)
        return None
