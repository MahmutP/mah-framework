# framework için, terminal arayüzü, modüller ve komutlar için validator, kısaca doğrulayıcı yapısı
from prompt_toolkit.validation import Validator, ValidationError # doğrulama için temel fonksiyonlar
from prompt_toolkit.document import Document
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.command_manager import CommandManager
    from core.module_manager import ModuleManager
class CLIValidator(Validator):
    """Doğrulayıcı

    Args:
        Validator (_type_): doğrulama fonksiyonu.
    """
    def __init__(self, command_manager: 'CommandManager', module_manager: 'ModuleManager'):
        """init fonksiyon.

        Args:
            command_manager (CommandManager): komut yöneticisi.
            module_manager (ModuleManager): Modül yöneticisi.
        """
        self.command_manager = command_manager # komutların işlenmesi için
        self.module_manager = module_manager # modüllerin işlenmesi için
    def validate(self, document: Document): # ana fonksiyon
        """doğrulama ana fonksiyon.

        Args:
            document (Document): doğrulama için kullanılan document objesi.

        Raises:
            ValidationError: bilinmeyen bir komut hatası.
            ValidationError: use komutu yol gerektirir hatası.
            ValidationError: Modül bulunamadı hatası.
        """
        text = document.text.strip()
        if text.startswith('#'):
            return
        if not text:
            return 
        parts = text.split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        resolved_command_name, is_alias = self.command_manager.resolve_command(command_name)
        if not resolved_command_name:
            raise ValidationError(
                message=f"Hata: '{command_name}' bilinmeyen bir komut veya alias.",
                cursor_position=len(command_name)
            )
        if resolved_command_name == 'use':
            if not args:
                raise ValidationError(
                    message="Hata: 'use' komutu bir modül yolu gerektirir.",
                    cursor_position=len(text)
                )
            module_path = args.strip()
            if not self.module_manager.get_module(module_path):
                raise ValidationError(
                    message=f"Hata: '{module_path}' modülü bulunamadı.",
                    cursor_position=len(text)
                )