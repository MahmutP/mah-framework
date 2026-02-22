from typing import Any, List
from core.command import Command
from core.shared_state import shared_state
from core.module import BaseModule 
from rich import  print
import os

class Set(Command):
    """option'ları değiştirmeye yarıyan komut.

    Args:
        Command (_type_): Ana komut sınıfı.

    Returns:
        _type_: _description_
    """
    Name = "set"
    Description = "Seçili modülün seçeneklerini ayarlar."
    Category = "module"
    Aliases = []
    Usage = "set <seçenek_adı> <değer>"
    Examples = [
        "set RHOSTS 192.168.1.1",
        "set RPORT 21",
        "set TEXT \"test mesajı\"",
        "set ALGORITHM sha256"
    ]
    def __init__(self):
        """init fonksiyon
        """
        super().__init__()
        self.completer_function = self._set_completer 
    
    def _get_path_completions(self, current_input: str, default_dir: str = ".", extensions: list = None) -> List[str]:
        """Dosya yolu tamamlama mantığı.
        
        Args:
            current_input: Kullanıcının girdiği kısmi yol.
            default_dir: Varsayılan dizin.
            extensions: Sadece bu uzantılara sahip dosyaları göster (örn: ['.jpg', '.png']).
                        None ise tüm dosyalar gösterilir. Dizinler her zaman gösterilir.
        """
        # Eğer input boşsa varsayılan dizini kullan
        if not current_input:
            path = default_dir
        else:
            path = current_input
        
        dirname, basename = os.path.split(path)
        if not dirname: 
            dirname = "."
            
        suggestions = []
        try:
            if os.path.isdir(dirname):
                for name in os.listdir(dirname):
                    # Uzantı filtresi aktifse gizli dosyaları (. ile başlayan) atla
                    if extensions and name.startswith('.'):
                        continue
                    
                    if name.startswith(basename):
                        full_path = os.path.join(dirname, name)
                        # Eğer varsayılan dizin "." ise ve input boşsa "./" ekleme
                        if dirname == ".": 
                            full_path = name
                        
                        actual_path = os.path.join(dirname, name)
                        if os.path.isdir(actual_path):
                            suggestions.append(full_path + "/")
                        else:
                            # Uzantı filtresi varsa kontrol et
                            if extensions:
                                _, ext = os.path.splitext(name)
                                if ext.lower() not in extensions:
                                    continue
                            suggestions.append(full_path)
        except Exception:
            pass
            
        return sorted(suggestions)

    def _set_completer(self, text: str, word_before_cursor: str) -> List[str]:
        """set komutunun otomatik tamamlaması.

        Args:
            text (str): text girdi.
            word_before_cursor (str): imlecin solundaki text.

        Returns:
            List[str]: otomatik tamamlama listesi.
        """
        parts = text.split()
        selected_module: BaseModule = shared_state.get_selected_module()
        if not selected_module:
            return []
        options = selected_module.get_options()
        
        # "set " yazıldığında option isimlerini göster
        if len(parts) == 1 and text.endswith(' '): 
            return sorted(list(options.keys()))
        
        # "set TEX" yazıldığında option isimlerini tamamla
        elif len(parts) == 2 and not text.endswith(' '): 
            current_arg = parts[1]
            return sorted([name for name in options.keys() if name.startswith(current_arg)])
        
        # "set OPTION_NAME " yazıldığında değeri tamamla
        elif len(parts) == 2 and text.endswith(' '): 
            option_name = parts[1]
            if option_name in options:
                opt = options[option_name]
                
                # 1. Dosya yolu tamamlama önceliği: Option içinde tanımlı dizin
                if hasattr(opt, "completion_dir") and opt.completion_dir:
                    exts = getattr(opt, 'completion_extensions', None)
                    return self._get_path_completions("", default_dir=opt.completion_dir, extensions=exts)

                # 2. Choices varsa (Öncelikli)
                if opt.choices:
                    return [str(c) for c in opt.choices]

                # 3. İsim bazlı tahmin (Fallback)
                if 'WORDLIST' in option_name.upper():
                    return self._get_path_completions("", default_dir="config/wordlists/")
                elif any(x in option_name.upper() for x in ['FILE', 'PATH']):
                    return self._get_path_completions("")
                    
                # 3. Boolean tahmin
                current_val = str(opt.value).lower()
                if current_val in ['true', 'false', '0', '1', 'yes', 'no']:
                    return ['true', 'false']
            return []
        
        # "set OPTION_NAME deger" yazıldığında
        elif len(parts) >= 3:
            option_name = parts[1]
            current_value = parts[2] if len(parts) > 2 else ""
            
            if option_name in options:
                opt = options[option_name]
                
                # 1. Dosya yolu tamamlama
                if hasattr(opt, "completion_dir") and opt.completion_dir:
                    exts = getattr(opt, 'completion_extensions', None)
                    return self._get_path_completions(current_value, default_dir=opt.completion_dir, extensions=exts)
                
                choices = []
                if opt.choices:
                    choices = [str(c) for c in opt.choices]
                else: 
                     # İsim bazlı tahmin (Fallback) - Sadece choices yoksa bak
                    if 'WORDLIST' in option_name.upper():
                         return self._get_path_completions(current_value, default_dir="config/wordlists/")
                    elif any(x in option_name.upper() for x in ['FILE', 'PATH']):
                         return self._get_path_completions(current_value)

                    current_val = str(opt.value).lower()
                    if current_val in ['true', 'false', '0', '1', 'yes', 'no']:
                        choices = ['true', 'false']
                return sorted([c for c in choices if c.lower().startswith(current_value.lower())])
            return []
        
        return []
    def execute(self, *args: str, **kwargs: Any) -> bool:
        """Komut çalıştırılacak çalışacak kod.

        Returns:
            bool: Başarılı olup olmadığının sonucu.
        """
        selected_module: BaseModule = shared_state.get_selected_module()
        if not selected_module:
            print("Herhangi bir modül seçili değil. Lütfen önce 'use <modül_yolu>' komutunu kullanın.")
            return False
        if len(args) < 2:
            print("Kullanım: set <seçenek_adı> <değer>")
            return False
        option_name = args[0]
        option_value = " ".join(args[1:]) 
        options = selected_module.get_options()
        if option_name in options:
            if selected_module.set_option_value(option_name, option_value):
                # Çıktı formatı ve rengi düzeltildi
                print(f"{option_name} => {option_value}")
                return True
            else:
                print(f"Seçenek '{option_name}' değeri '{option_value}' olarak ayarlanamadı. Regex kontrolü başarısız olabilir.")
                return False
        else:
            print(f"Seçenek '{option_name}' bulunamadı. 'show options' ile mevcut seçenekleri listeleyebilirsiniz.")
            return False