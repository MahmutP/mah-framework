# Bu modül, framework içindeki komutların yüklenmesi, yönetilmesi ve çalıştırılmasından sorumludur.
# Komutların dinamik olarak yüklenmesi, alias (takma ad) yönetimi ve komut yürütme akışı burada kontrol edilir.

from pathlib import Path
import importlib.util
import json # Alias'ları JSON formatında okumak ve yazmak için kullanılır.
from typing import Dict, Optional, List, Tuple, Callable
from core.command import Command # Temel Komut sınıfı
# Sabitler: Alias dosya yolu ve komut kategorileri
from core.cont import ALIASES_FILE, COMMAND_CATEGORIES 
from core.hooks import HookType
from core.shared_state import shared_state
from core import logger
from rich import print

class CommandManager:
    """
    Komut Yönetim Sınıfı (CommandManager).
    
    Bu sınıfın temel görevleri:
    1. Belirtilen dizindeki (varsayılan: 'commands') komut dosyalarını tarayıp yüklemek.
    2. Komutlara ait alias'ları (kısa yolları) yönetmek (ekleme, silme, kaydetme).
    3. Kullanıcıdan gelen metin girdisini ayrıştırıp ilgili komutu çalıştırmak.
    """
    
    def __init__(self, commands_dir: str = "commands") -> None:
        """
        CommandManager başlatıcı metod.

        Args:
            commands_dir (str, optional): Komut dosyalarının bulunduğu dizin yolu. Varsayılan: "commands".
        """
        self.commands_dir = Path(commands_dir) # Komutların aranacağı dizin
        self.commands: Dict[str, Command] = {} # Yüklenen komut nesnelerini tutan sözlük (İsim -> Obje)
        self.aliases: Dict[str, str] = {} # Yüklenen alias'ları tutan sözlük (Alias -> Hedef Komut)
        
        # Alias dosyasının varlığından emin ol, yoksa oluştur.
        self._ensure_aliases_file() 
        
    def _ensure_aliases_file(self) -> None:
        """
        Alias dosyasının (genellikle aliases.json) diskte var olup olmadığını kontrol eder.
        Eğer dosya yoksa, boş bir JSON dosyası oluşturur. 
        Bu, uygulamanın ilk çalıştırılmasında dosya bulunamadı hatalarını önler.
        """
        aliases_path = Path(ALIASES_FILE)
        if not aliases_path.exists():
            # Dosyanın ebeveyn klasörlerini de gerekirse oluştur.
            aliases_path.parent.mkdir(parents=True, exist_ok=True)
            with open(aliases_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4) # Boş bir JSON objesi yaz.
            print(f"Varsayılan alias dosyası oluşturuldu: {ALIASES_FILE}")

    def load_aliases(self) -> None:
        """
        Alias dosyasını okur ve belleğe yükler.
        Bu metod, uygulamanın başlangıcında veya alias'lar diskten tekrar okunmak istendiğinde çağrılır.
        """
        try:
            with open(ALIASES_FILE, 'r', encoding='utf-8') as f:
                loaded_aliases = json.load(f)
                self.aliases.clear() # Mevcut hafızadaki aliasları temizle
                for alias, target in loaded_aliases.items():
                    self.aliases[alias] = target 
            # Başarılı yükleme sonrası loglanabilir veya sessiz geçilebilir.
            # print(f"{len(self.aliases)} alias yüklendi.")
        except FileNotFoundError:
            # Dosya bir şekilde silindiyse tekrar oluşturmayı dener.
            print(f"Alias dosyası bulunamadı: {ALIASES_FILE}. Yeni bir dosya oluşturulacak.")
            self._ensure_aliases_file()
        except json.JSONDecodeError as e:
            # json dosyası bozuk formatta ise hata verir ve alias listesini temizler.
            print(f"Alias dosyası okunurken hata oluştu '{ALIASES_FILE}': {e}. Dosya bozuk olabilir.")
            self.aliases.clear() 

    def save_aliases(self) -> None:
        """
        Mevcut alias listesini JSON dosyasına kaydeder.
        Alias eklendiğinde veya silindiğinde bu metod çağrılmalıdır.
        """
        try:
            with open(ALIASES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.aliases, f, indent=4) # Okunabilir (indent=4) formatta kaydet.
            # print(f"Aliaslar dosyaya kaydedildi: {ALIASES_FILE}")
        except PermissionError:
            print(f"Aliaslar kaydedilirken izin hatası: {ALIASES_FILE}")
            logger.exception("Alias dosyası yazma izni hatası")
        except IOError as e:
            print(f"Aliaslar kaydedilirken dosya hatası oluştu: {e}")
            logger.exception("Alias dosyası yazma hatası")

    def add_alias(self, alias_name: str, target_command: str) -> bool:
        """
        Yeni bir alias ekler ve dosyaya kaydeder.

        Args:
            alias_name (str): Kullanıcının kullanacağı kısa ad (örn: 'ls').
            target_command (str): Alias'ın çalıştıracağı asıl komut (örn: 'list files').

        Returns:
            bool: Ekleme başarılı ise True, alias zaten varsa False döner.
        """
        # Eğer bu isimde bir komut veya başka bir alias zaten varsa eklemeye izin verme.
        if alias_name in self.commands or alias_name in self.aliases:
            # print(f"'{alias_name}' zaten bir komut veya alias olarak mevcut.")
            return False
            
        self.aliases[alias_name] = target_command
        self.save_aliases() # Değişikliği kalıcı hale getir.
        # print(f"Alias '{alias_name}' -> '{target_command}' eklendi.")
        return True

    def remove_alias(self, alias_name: str) -> bool:
        """
        Mevcut bir alias'ı siler ve dosyayı günceller.

        Args:
            alias_name (str): Silinecek alias'ın adı.

        Returns:
            bool: Silme başarılı ise True, alias bulunamazsa False döner.
        """
        if alias_name in self.aliases:
            del self.aliases[alias_name]
            self.save_aliases() # Değişikliği kalıcı hale getir.
            # (f"Alias '{alias_name}' kaldırıldı.")
            return True
        # (f"Alias '{alias_name}' bulunamadı.")
        return False

    def get_aliases(self) -> Dict[str, str]:
        """
        Tüm aktif alias'ların listesini döndürür.

        Returns:
            Dict[str, str]: Alias -> Hedef Komut eşleşmeleri.
        """
        return self.aliases

    def load_commands(self) -> None:
        """
        Commands dizinindeki tüm Python dosyalarını tarar ve bu dosyalardaki 
        Command sınıfından türetilmiş sınıfları bularak yükler.
        
        Bu metod, Python'un dinamik import yeteneklerini kullanır (importlib),
        böylece yeni komut dosyaları eklendiğinde ana kodu değiştirmeye gerek kalmaz.
        """
        self.commands.clear()
        
        # Önce kullanıcı tanımlı aliasları yükle.
        # Bu işlem komut yüklemesinden önce yapılır, ancak komutlar yüklenirken
        # alias kontrolleri tekrar yapılabilir.
        self.load_aliases()
        
        # commands dizinindeki tüm .py dosyalarını gez
        for file_path in self.commands_dir.glob('*.py'):
            # __init__.py dosyasını atla, o bir komut değildir.
            if file_path.name == '__init__.py':
                continue
                
            command_name = file_path.stem  # Dosya adını uzantısız (örn: 'list.py' -> 'list') alır
            
            try:
                # 1. Modül spesifikasyonunu oluştur
                spec = importlib.util.spec_from_file_location(command_name, str(file_path))
                if spec is None or spec.loader is None:
                    print(f"Komut spesifikasyonu alınamadı: {file_path}")
                    continue
                
                # 2. Modülü spesifikasyondan oluştur
                command_module = importlib.util.module_from_spec(spec)
                
                # 3. Modülü çalıştır (kodunu execute et)
                spec.loader.exec_module(command_module)
                
                # 4. Modül içindeki nesneleri tara
                for name, obj in command_module.__dict__.items():
                    # Eğer nesne bir sınıfsa VE Command sınıfından türetilmişse VE Command sınıfının kendisi değilse
                    if isinstance(obj, type) and issubclass(obj, Command) and obj is not Command:
                        # Komut sınıfından bir örnek (instance) oluştur.
                        command_instance = obj()
                        
                        # Komutu yönetici sözlüğüne ekle.
                        self.commands[command_instance.Name] = command_instance 
                        
                        # Komut içinde kodlanmış (hardcoded) alias'ları da sisteme ekle.
                        for alias in command_instance.Aliases:
                            self.add_alias(alias, command_instance.Name) 
                        
                        # Bir dosyada birden fazla komut sınıfı olabilir ama genelde bir tane olur,
                        # ilk bulduğumuzu alıp çıkıyoruz (break). Eğer birden fazla desteklenecekse break kaldırılmalı.
                        break 
                        
            except SyntaxError as e:
                # Kodda yazım hatası varsa
                print(f"[bold red]Sözdizimi hatası:[/bold red] '{file_path.name}' dosyasında hata var.")
                logger.exception(f"Komut yüklenirken sözdizimi hatası '{file_path}'")
            except ImportError as e:
                # Modül yüklenirken başka bir modülü bulamazsa
                print(f"[bold red]İçe aktarma hatası:[/bold red] '{file_path.name}' - {e}")
                logger.exception(f"Komut yüklenirken import hatası '{file_path}'")
            except AttributeError as e:
                # Komut sınıfı beklenen özellikleri sağlamıyorsa
                print(f"[bold red]Öznitelik hatası:[/bold red] '{file_path.name}' - Komut sınıfı doğru tanımlanmamış.")
                logger.exception(f"Komut yüklenirken öznitelik hatası '{file_path}'")
            except Exception as e:
                # Diğer tüm hatalar
                print(f"[bold red]Beklenmeyen hata:[/bold red] '{file_path.name}' yüklenirken hata oluştu.")
                logger.exception(f"Komut yüklenirken beklenmeyen hata '{file_path}'")
                
        logger.info(f"{len(self.commands)} komut yüklendi") 

    def resolve_command(self, command_input: str) -> Tuple[Optional[str], bool]:
        """
        Verilen komut girdisinin (string) gerçek bir komut mu yoksa bir alias mı olduğunu çözer.

        Args:
            command_input (str): Kullanıcının girdiği ilk kelime (komut adı).

        Returns:
            Tuple[Optional[str], bool]: 
                - str: Çözümlenen komutun veya alias'ın hedef değeri. Bulunamazsa None.
                - bool: True ise bir alias bulundu, False ise doğrudan komut bulundu.
        """
        if command_input in self.commands:
            # Doğrudan bir komut adı (örn: 'help')
            return command_input, False 
        elif command_input in self.aliases:
            # Bir alias (örn: 'h' -> 'help')
            return self.aliases[command_input], True 
            
        return None, False 

    def execute_command(self, command_line: str) -> bool:
        """
        Kullanıcıdan alınan komut satırını işler ve ilgili komutu çalıştırır.
        
        Süreç:
        1. PRE_COMMAND hook tetiklenir (eklenti sistemi için).
        2. Komut satırı parçalanır (komut adı ve argümanlar).
        3. Alias çözümlemesi yapılır. Eğer alias ise argümanlar yeniden düzenlenir.
        4. Komut nesnesi bulunur ve execute metodu çağrılır.
        5. POST_COMMAND hook tetiklenir (sonuç başarılı veya başarısız).

        Args:
            command_line (str): Kullanıcının girdiği tam satır.

        Returns:
            bool: Komut başarıyla çalıştıysa True, aksi halde False.
        """
        # Kullanıcı boşluklar girmişse temizle
        parts = command_line.strip().split(maxsplit=1)
        if not parts:
            return False
            
        # İlk parça komut adıdır (veya alias)
        command_name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        # Komutu çöz (Alias mı, gerçek komut mu?)
        resolved_command_name, is_alias = self.resolve_command(command_name)
        
        # PRE_COMMAND hook'unu tetikle (Komut çalışmadan hemen önce)
        # Bu, eklentilerin komutları izlemesine veya engellemesine olanak tanır.
        if shared_state.plugin_manager:
            shared_state.plugin_manager.trigger_hook(
                HookType.PRE_COMMAND,
                command_line=command_line
            )
        
        if resolved_command_name:
            # Makro kaydı (record komutu hariç)
            if shared_state.is_recording and not resolved_command_name.strip().lower().startswith("record"):
                shared_state.recorded_commands.append(command_line)
                
            # Eğer bir alias kullanıldıysa karmaşık bir işleme gerekebilir.
            # Çünkü alias birden fazla kelimeden oluşabilir (örn: 'pull' -> 'git pull')
            if is_alias:
                full_target_command_line = self.aliases[command_name]
                
                # Kullanıcının girdiği ek argümanları alias'ın sonuna ekle
                if len(parts) > 1:
                    full_target_command_line += " " + parts[1]
                
                # Yeni komut satırını tekrar parçala
                target_parts = full_target_command_line.strip().split(maxsplit=1)
                resolved_command_name = target_parts[0].lower() # Artık asıl komut adı (örn: git)
                args = target_parts[1].split() if len(target_parts) > 1 else [] # Argümanlar güncellendi

            # Çözümlenen isme karşılık gelen komut nesnesini al
            command_obj = self.commands.get(resolved_command_name)
            
            if command_obj:
                try:
                    logger.info(f"Komut çalıştırıldı: {resolved_command_name}")
                    # Komutu çalıştır (*args ile listeyi argümanlara dök)
                    result = command_obj.execute(*args)
                    
                    # POST_COMMAND hook'unu tetikle (başarılı durum)
                    if shared_state.plugin_manager:
                        shared_state.plugin_manager.trigger_hook(
                            HookType.POST_COMMAND,
                            command_line=command_line,
                            success=result
                        )
                    return result

                except TypeError as e:
                    # Komuta yanlış sayıda veya türde argüman verilirse
                    print(f"[bold red]Argüman hatası:[/bold red] '{resolved_command_name}' komutuna yanlış argüman verildi.")
                    logger.exception(f"Komut '{resolved_command_name}' yürütülürken TypeError")
                    
                    if shared_state.plugin_manager:
                        shared_state.plugin_manager.trigger_hook(
                            HookType.POST_COMMAND, command_line=command_line, success=False
                        )
                    return False
                    
                except KeyboardInterrupt:
                    # Kullanıcı CTRL+C'ye basarsa
                    print("\nKomut kullanıcı tarafından kesildi.")
                    logger.info(f"Komut '{resolved_command_name}' kullanıcı tarafından kesildi")
                    
                    if shared_state.plugin_manager:
                        shared_state.plugin_manager.trigger_hook(
                            HookType.POST_COMMAND, command_line=command_line, success=False
                        )
                    return False
                    
                except Exception as e:
                    # Diğer tüm beklenmeyen hatalar
                    print(f"[bold red]Kritik hata:[/bold red] '{resolved_command_name}' yürütülürken beklenmeyen hata.")
                    logger.exception(f"Komut '{resolved_command_name}' yürütülürken beklenmeyen hata")
                    
                    if shared_state.plugin_manager:
                        shared_state.plugin_manager.trigger_hook(
                            HookType.POST_COMMAND, command_line=command_line, success=False
                        )
                    return False
            else:
                # Alias çözüldü ama hedef komut (örneğin 'git') framework'te yüklü değil
                print(f"'{resolved_command_name}' komutu bulunamadı.")
                logger.warning(f"Komut bulunamadı: {resolved_command_name}")
                return False
        else:
            # Komut ne alias ne de yüklü bir komut
            print(f"'{command_name}' bilinmeyen bir komut veya alias.")
            logger.warning(f"Bilinmeyen komut: {command_name}")
            return False

    def get_all_commands(self) -> Dict[str, Command]:
        """
        Yüklü tüm komut nesnelerini döndürür.

        Returns:
            Dict[str, Command]: Komut Adı -> Komut Nesnesi
        """
        return self.commands

    def get_categorized_commands(self) -> Dict[str, Dict[str, Command]]:
        """
        Komutları kategorilerine göre gruplayarak döndürür.
        Bu genellikle 'help' komutunda çıktıyı düzenlemek için kullanılır.

        Returns:
            Dict[str, Dict[str, Command]]: Kategori Adı -> (Komut Adı -> Komut Nesnesi)
        """
        categorized_commands: Dict[str, Dict[str, Command]] = {}
        for cmd_name, cmd_obj in self.commands.items():
            category_display_name = cmd_obj.get_category_display_name()
            
            if category_display_name not in categorized_commands:
                categorized_commands[category_display_name] = {}
            
            categorized_commands[category_display_name][cmd_name] = cmd_obj
            
        return categorized_commands

    def get_command_completer_function(self, command_name: str) -> Optional[Callable]:
        """
        Belirli bir komut için tanımlanmış otomatik tamamlama fonksiyonunu döndürür.

        Args:
            command_name (str): Komutun adı.

        Returns:
            Optional[Callable]: Varsa tamamlama fonksiyonu, yoksa None.
        """
        command_obj = self.commands.get(command_name)
        if command_obj:
            return command_obj.completer_function
        return None