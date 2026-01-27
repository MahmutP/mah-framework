# modül kontrolü, işlemesi ve framework içi kullanılması ve 3. taraf modül desteği ile kullanımı için
from pathlib import Path
import importlib.util # modülleri işlemek için
from typing import Dict, Optional, Tuple
from core.module import BaseModule # temel modül sınıfı
from rich import print
from core import logger

class ModuleManager:
    def __init__(self, modules_dir="modules"):
        """init fonksiyon.

        Args:
            modules_dir (str, optional): Modüllerin bulunduğu klasör. Defaults to "modules".
        """
        self.modules_dir = Path(modules_dir) # modüllerin bulunduğu dizin
        self.modules: Dict[str, BaseModule] = {} # framework içi global modül dict'i 

    def load_modules(self):# modülleri import edecek ana fonksiyon
        """Modül yükleyici ana fonksiyon.
        """
        self.modules.clear() 
        for file_path in self.modules_dir.rglob('*.py'):
            if file_path.name == '__init__.py':
                continue
            # Relative path using pathlib, with forward slashes for consistency
            relative_path = file_path.relative_to(self.modules_dir)
            module_name_for_dict = relative_path.with_suffix('').as_posix()
            try:
                spec = importlib.util.spec_from_file_location(module_name_for_dict, str(file_path))
                if spec is None:
                    print(f"Modül spesifikasyonu alınamadı: {file_path}")
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for name, obj in module.__dict__.items():
                    if isinstance(obj, type) and issubclass(obj, BaseModule) and obj is not BaseModule:
                        module_instance = obj()
                        if not module_instance.Category:
                            module_instance.Category = "uncategorized"
                        self.modules[module_name_for_dict] = module_instance 
                        break 
            except SyntaxError as e:
                print(f"[bold red]Sözdizimi hatası:[/bold red] '{file_path.name}' dosyasında hata var.")
                logger.exception(f"Modül yüklenirken sözdizimi hatası '{file_path}'")
            except ImportError as e:
                print(f"[bold red]İçe aktarma hatası:[/bold red] '{file_path.name}' - {e}")
                logger.exception(f"Modül yüklenirken import hatası '{file_path}'")
            except AttributeError as e:
                print(f"[bold red]Öznitelik hatası:[/bold red] '{file_path.name}' - Modül sınıfı doğru tanımlanmamış.")
                logger.exception(f"Modül yüklenirken öznitelik hatası '{file_path}'")
            except Exception as e:
                print(f"[bold red]Beklenmeyen hata:[/bold red] '{file_path.name}' yüklenirken hata oluştu.")
                logger.exception(f"Modül yüklenirken beklenmeyen hata '{file_path}'")
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
        except TypeError as e:
            print(f"[bold red]Argüman hatası:[/bold red] Modüle yanlış seçenek değeri verildi.")
            logger.exception(f"Modül '{module_path}' çalıştırılırken TypeError")
            return False
        except KeyboardInterrupt:
            print("\nModül çalışması kullanıcı tarafından kesildi.")
            logger.info(f"Modül '{module_path}' kullanıcı tarafından kesildi")
            return False
        except Exception as e:
            print(f"[bold red]Kritik hata:[/bold red] '{module_path}' çalıştırılırken beklenmeyen hata.")
            logger.exception(f"Modül '{module_path}' çalıştırılırken beklenmeyen hata")
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
