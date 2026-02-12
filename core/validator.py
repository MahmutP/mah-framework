# Terminal arayüzünde kullanıcının girdiği komutları doğrulayan (validation) modül.
# prompt_toolkit kütüphanesinin 'Validator' özelliğini kullanır.

from prompt_toolkit.validation import Validator, ValidationError # Doğrulama için gerekli temel sınıflar.
from prompt_toolkit.document import Document
from typing import TYPE_CHECKING

# Type Checking sırasında döngüsel import (circular import) hatasını önlemek için.
if TYPE_CHECKING:
    from core.command_manager import CommandManager
    from core.module_manager import ModuleManager

class CLIValidator(Validator):
    """
    Komut Satırı Doğrulayıcısı (CLI Validator).
    
    Kullanıcı bir komut girip Enter tuşuna bastığında, bu sınıf devreye girer.
    Girdinin geçerli bir komut olup olmadığını kontrol eder.
    Eğer geçersizse, hata mesajı gösterir ve komutun çalışmasını engeller.
    """
    
    def __init__(self, command_manager: 'CommandManager', module_manager: 'ModuleManager'):
        """
        Validator'ü başlatır.

        Args:
            command_manager: Komutların geçerliliğini kontrol etmek için gerekli yönetici.
            module_manager: Modüllerin varlığını kontrol etmek için gerekli yönetici.
        """
        self.command_manager = command_manager 
        self.module_manager = module_manager 

    def validate(self, document: Document):
        """
        Doğrulama işleminin yapıldığı ana metod.
        
        Args:
            document (Document): Kullanıcının girdiği metin ve imleç bilgisi.
        
        Raises:
            ValidationError: Girdi geçersizse fırlatılan hata.
        """
        text = document.text.strip()
        
        # Yorum satırlarını (#) ve boş satırları doğrulama dışı bırak (geçerli say).
        if text.startswith('#'):
            return
        if not text:
            return 
            
        parts = text.split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # 1. Komutun var olup olmadığını kontrol et.
        resolved_command_name, is_alias = self.command_manager.resolve_command(command_name)
        
        if not resolved_command_name:
            # Komut bulunamadıysa hata fırlat (İmleci komut sonuna getir).
            raise ValidationError(
                message=f"Hata: '{command_name}' bilinmeyen bir komut veya alias.",
                cursor_position=len(command_name)
            )
            
        # 2. 'use' komutu özel kontrolü.
        if resolved_command_name == 'use':
            # Modül yolu girilmemişse hata ver.
            if not args:
                raise ValidationError(
                    message="Hata: 'use' komutu bir modül yolu gerektirir.",
                    cursor_position=len(text)
                )
            
            # Girilen modül yolu geçerli mi kontrol et.
            module_path = args.strip()
            if not self.module_manager.get_module(module_path):
                raise ValidationError(
                    message=f"Hata: '{module_path}' modülü bulunamadı.",
                    cursor_position=len(text)
                )