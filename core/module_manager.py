# Framework'ün en kritik parçalarından biri olan Modül Yöneticisi (ModuleManager).
# Bu modül, sistemdeki tüm modüllerin (exploit, scanner vb.) bulunmasını, yüklenmesini,
# yönetilmesini ve çalıştırılmasını sağlar. Ayrıca eklenti (plugin) sistemiyle entegre çalışır.

from pathlib import Path
import importlib.util # Modülleri dinamik olarak (çalışma zamanında) yüklemek için gerekli.
from typing import Dict, Optional, Tuple
from core.module import BaseModule # Modüllerin türetilmesi gereken temel sınıf.
from core.hooks import HookType
from core.shared_state import shared_state
from rich import print
from core import logger

class ModuleManager:
    """
    Modül Yönetim Sınıfı.
    
    Görevleri:
    1. Belirtilen dizindeki tüm Python dosyalarını taramak.
    2. Bu dosyaları modül olarak yüklemek ve hafızada tutmak.
    3. Kullanıcı talebine göre modülleri bulmak, bilgilerini getirmek ve çalıştırmak.
    """
    
    def __init__(self, modules_dir: str = "modules") -> None:
        """
        ModuleManager başlatıcı.

        Args:
            modules_dir (str, optional): Modüllerin aranacağı kök dizin. Varsayılan: "modules".
        """
        self.modules_dir = Path(modules_dir) # Modül dizin yolu (Path nesnesi olarak)
        self.modules: Dict[str, BaseModule] = {} # Yüklenen modülleri tutan sözlük (Modül Yolu -> Modül Nesnesi)

    def load_modules(self) -> None:
        """
        Tüm modülleri diskten okuyup belleğe yükleyen ana metod.
        Bu işlem genellikle uygulama başlangıcında veya 'reload' komutuyla yapılır.
        """
        self.modules.clear() # Önceki yüklemeleri temizle (reload desteği için)
        
        # rglob('*.py') ile tüm alt klasörlerdeki .py dosyalarını özyineli (recursive) olarak bul.
        for file_path in self.modules_dir.rglob('*.py'):
            # __init__.py dosyaları Python paket dosyalarıdır, modül değildir. Atla.
            if file_path.name == '__init__.py':
                continue
                
            # Şablon (Template) dosyalarını kontrol et.
            # Bazı payload oluşturucular, içinde {{DEGISKEN}} barındıran şablon dosyaları kullanır.
            # Bunlar geçerli Python kodu olmayabilir veya doğrudan çalıştırılmaması gerekir.
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if '{{' in content and '}}' in content:
                    # Dosya BaseModule alt sınıfı tanımlıyorsa (örn: payload generator), modül olarak yükle.
                    if 'BaseModule' not in content:
                        logger.debug(f"Template dosyası atlandı: {file_path}")
                        continue
                    else:
                        logger.debug(f"Template içeren modül dosyası yükleniyor: {file_path}")
            except Exception:
                pass # Dosya okuma hatası olursa (izin vb.) yoksay ve devam et.

            # Modülün bağıl yolunu (relative path) hesapla.
            # Örn: /full/path/to/modules/exploit/linux/overflow.py -> exploit/linux/overflow.py
            relative_path = file_path.relative_to(self.modules_dir)
            
            # Dosya uzantısını (.py) kaldır ve dizin ayırıcılarını POSIX formatına (/) çevir.
            # Bu, modülün framework içindeki benzersiz kimliği (ID) olacaktır.
            # Örn: exploit/linux/overflow
            module_name_for_dict = relative_path.with_suffix('').as_posix()
            
            # Eğer modül kök dizindeyse (hiç / yoksa), 'uncategorized' kategorisine at.
            if '/' not in module_name_for_dict:
                module_name_for_dict = f"uncategorized/{module_name_for_dict}"
            
            try:
                # 1. Python'un import mekanizmasını kullanarak dosyadan modül spesifikasyonu oluştur.
                spec = importlib.util.spec_from_file_location(module_name_for_dict, str(file_path))
                if spec is None or spec.loader is None:
                    print(f"Modül spesifikasyonu alınamadı: {file_path}")
                    continue
                
                # 2. Modülü spesifikasyondan oluştur (Henüz kod çalıştırılmadı).
                module = importlib.util.module_from_spec(spec)
                
                # 3. Modül kodunu çalıştır (Class tanımları belleğe yüklenir).
                spec.loader.exec_module(module)
                
                # 4. Modül içindeki sınıfları tara ve BaseModule türevi olanı bul.
                for name, obj in module.__dict__.items():
                    # BaseModule'den türetilmiş OLACAK ama BaseModule'ün kendisi OLMAYACAK.
                    if isinstance(obj, type) and issubclass(obj, BaseModule) and obj is not BaseModule:
                        # Sınıftan bir örnek (instance) oluştur.
                        module_instance = obj()
                        
                        # Kategori tanımlanmamışsa varsayılanı ata.
                        if not module_instance.Category:
                            module_instance.Category = "uncategorized"
                        
                        # Modülün diskteki yolunu nesneye kaydet (Referans için).
                        module_instance.Path = module_name_for_dict
                        
                        # Modülün adını (module_instance.Name) elle değiştirmiyoruz,
                        # sınıf içinde tanımlanan 'Name' özelliğini kullanıyoruz.
                        
                        self.modules[module_name_for_dict] = module_instance 
                        break # Bir dosyada bir modül sınıfı bekliyoruz, bulduktan sonra çık.
                        
            except SyntaxError as e:
                # Modül kodunda yazım hatası varsa
                print(f"[bold red]Sözdizimi hatası:[/bold red] '{file_path.name}' dosyasında hata var.")
                logger.exception(f"Modül yüklenirken sözdizimi hatası '{file_path}'")
            except ImportError as e:
                # Modülün bağımlılıkları eksikse
                print(f"[bold red]İçe aktarma hatası:[/bold red] '{file_path.name}' - {e}")
                logger.exception(f"Modül yüklenirken import hatası '{file_path}'")
            except AttributeError as e:
                # Modül sınıfı eksik veya hatalı tanımlanmışsa
                print(f"[bold red]Öznitelik hatası:[/bold red] '{file_path.name}' - Modül sınıfı doğru tanımlanmamış.")
                logger.exception(f"Modül yüklenirken öznitelik hatası '{file_path}'")
            except Exception as e:
                # Diğer tüm hatalar
                print(f"[bold red]Beklenmeyen hata:[/bold red] '{file_path.name}' yüklenirken hata oluştu.")
                logger.exception(f"Modül yüklenirken beklenmeyen hata '{file_path}'")
                
        logger.info(f"{len(self.modules)} modül yüklendi")

    def get_module(self, module_path: str) -> Optional[BaseModule]:
        """
        Verilen yol (path) ile eşleşen modül nesnesini döndürür.

        Args:
            module_path (str): Modülün yolu (örn: exploit/linux/ssh_brute).

        Returns:
            Optional[BaseModule]: Modül nesnesi veya bulunamazsa None.
        """
        return self.modules.get(module_path)

    def get_all_modules(self) -> Dict[str, BaseModule]:
        """
        Yüklü tüm modülleri döndürür.

        Returns:
            Dict[str, BaseModule]: Modül Yolu -> Modül Nesnesi sözlüğü.
        """
        return self.modules

    def get_modules_by_category(self) -> Dict[str, Dict[str, BaseModule]]:
        """
        Modülleri kategorilerine göre gruplayarak döndürür.
        'show' veya 'search' komutlarında listeleme yapmak için kullanılır.

        Returns:
            Dict[str, Dict[str, BaseModule]]: Kategori Adı -> (Modül Yolu -> Modül Nesnesi)
        """
        categorized_modules: Dict[str, Dict[str, BaseModule]] = {}
        for module_path, module_obj in self.modules.items():
            # Kategori adının baş harfini büyüt (Görsellik için).
            category = module_obj.Category.capitalize() 
            
            if category not in categorized_modules:
                categorized_modules[category] = {}
            
            categorized_modules[category][module_path] = module_obj
            
        return categorized_modules

    def run_module(self, module_path: str) -> bool:
        """
        Belirtilen modülü çalıştırır (Execute).
        Bu metod, modül çalıştırma sürecinin (Lifecycle) tamamını yönetir:
        1. Modülü bulur.
        2. Zorunlu seçeneklerin (Options) dolu olup olmadığını kontrol eder.
        3. Pre-run hook'larını tetikler.
        4. Modüle seçenekleri geçirir ve çalıştırır.
        5. Post-run hook'larını tetikler.
        6. Hataları yakalar.

        Args:
            module_path (str): Çalıştırılacak modülün yolu.

        Returns:
            bool: Modül başarıyla tamamlandıysa True, hata aldıysa False.
        """
        module = self.get_module(module_path)
        
        # Modül yoksa hata ver ve çık.
        if not module:
            print(f"Modül bulunamadı: {module_path}")
            logger.warning(f"Modül bulunamadı: {module_path}")
            return False
        
        # Zorunlu seçenekler (Required Options) kontrolü.
        if not module.check_required_options():
            logger.warning(f"Modül çalıştırılamadı (eksik seçenekler): {module_path}")
            return False
        
        # Modül çalışmadan ÖNCE (PRE_MODULE_RUN) eklenti hook'unu tetikle.
        # Bu, eklentilerin araya girip doğrulama yapmasına veya çalıştırmayı engellemesine izin verir.
        if shared_state.plugin_manager:
            shared_state.plugin_manager.trigger_hook(
                HookType.PRE_MODULE_RUN,
                module_path=module_path,
                module=module
            )
        
        try:
            # Modül seçeneklerinin SADECE değerlerini içeren temiz bir sözlük oluştur.
            # Modülün run metodu Option nesnelerine değil, doğrudan değerlere ihtiyaç duyar.
            current_options = {name: opt.value for name, opt in module.get_options().items()}
            
            logger.info(f"Modül çalıştırılıyor: {module_path}")
            
            # --- MODÜLÜN ASIL ÇALIŞTIĞI YER ---
            module.run(current_options)
            # ----------------------------------
            
            # Modül çalıştıktan SONRA (POST_MODULE_RUN) başarılı hook'unu tetikle.
            if shared_state.plugin_manager:
                shared_state.plugin_manager.trigger_hook(
                    HookType.POST_MODULE_RUN,
                    module_path=module_path,
                    module=module,
                    success=True
                )
            return True
            
        except TypeError as e:
            # Modüle yanlış tipte veya sayıda argüman giderse.
            print(f"[bold red]Argüman hatası:[/bold red] Modüle yanlış seçenek değeri verildi.")
            logger.exception(f"Modül '{module_path}' çalıştırılırken TypeError")
            
            # Hata durumunda hook tetikle.
            if shared_state.plugin_manager:
                shared_state.plugin_manager.trigger_hook(
                    HookType.POST_MODULE_RUN,
                    module_path=module_path,
                    module=module,
                    success=False
                )
            return False
            
        except KeyboardInterrupt:
            # Kullanıcı Ctrl+C ile modülü durdurursa.
            print("\nModül çalışması kullanıcı tarafından kesildi.")
            logger.info(f"Modül '{module_path}' kullanıcı tarafından kesildi")
            
            if shared_state.plugin_manager:
                shared_state.plugin_manager.trigger_hook(
                    HookType.POST_MODULE_RUN,
                    module_path=module_path,
                    module=module,
                    success=False
                )
            return False
            
        except Exception as e:
            # Modül içinde herhangi bir beklenmedik hata oluşursa.
            # Modül geliştiricisi hatayı yakalamamış olabilir, framework çökmümemeli.
            print(f"[bold red]Kritik hata:[/bold red] '{module_path}' çalıştırılırken beklenmeyen hata.")
            logger.exception(f"Modül '{module_path}' çalıştırılırken beklenmeyen hata")
            
            if shared_state.plugin_manager:
                shared_state.plugin_manager.trigger_hook(
                    HookType.POST_MODULE_RUN,
                    module_path=module_path,
                    module=module,
                    success=False
                )
            return False

    def get_module_info(self, module_path: str) -> Optional[Tuple[str, str, str, str]]:
        """
        Belirtilen modülün temel bilgilerini (metadata) döndürür.
        'info' veya 'search' komutları tarafından kullanılır.

        Args:
            module_path (str): Modül yolu.

        Returns:
            Optional[Tuple[str, str, str, str]]: (Ad, Açıklama, Yazar, Kategori) demeti.
        """
        module = self.get_module(module_path)
        if module:
            return (module.Name, module.Description, module.Author, module.Category)
        return None
