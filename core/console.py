# terminal(konsol) arayüzünde kullanmak için kodladım
# temel kütüphanesi prompt-toolkit
import sys
import os
import shutil 
from prompt_toolkit import PromptSession # prompt oluşturmak için
from prompt_toolkit.history import InMemoryHistory # bash history benzeri history kodlamak için
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory # prompt için geçmiş komut otomatik tamamlama
from prompt_toolkit.completion import Completer, Completion # otomatik tamamlama için temel kütüphane
from prompt_toolkit.key_binding import KeyBindings # klavye atamaları
from prompt_toolkit.styles import Style # terminal arayüzü için stilizasyon
from prompt_toolkit.formatted_text import HTML
from core.shared_state import shared_state
from core.command_manager import CommandManager # komut yönetimi için
from core.module_manager import ModuleManager # modül yönetimi için
from core.completer import CLICompleter # prompt içi komut ve komut içi otomatik tamamlaması
from core.validator import CLIValidator # validate lokal kütüphanesi
from core.cont import DEFAULT_TERMINAL_WIDTH
from core import logger
from rich import print
class Console:
    def __init__(self, command_manager: CommandManager, module_manager: ModuleManager):
        """init fonksiyon.

        Args:
            command_manager (CommandManager): Komut yöneticisi.
            module_manager (ModuleManager): Modül yöneticisi.
        """
        self.command_manager = command_manager
        self.module_manager = module_manager
        self.history = InMemoryHistory()
        self.completer = CLICompleter(command_manager, module_manager)
        self.validator = CLIValidator(command_manager, module_manager)
        self.session = self._create_session()
        self.running = True
    def _create_session(self) -> PromptSession: # oturum oluşturucu
        """Oturum oluşturucu fonksiyon.

        Returns:
            PromptSession: Oturum oluşturmak için kullanılan ana fonksiyon.
        """
        bindings = KeyBindings()
        @bindings.add('c-c')
        def _(event):
            """ctrl+c ile yapılınca olacak olay.

            Args:
                event (_type_): mevcut olay.
            """
            if shared_state.get_selected_module():
                print("Modül çalışması Ctrl+C ile kesildi (eğer çalışıyorsa).")
            else:
                event.app.current_buffer.text = '' 
                print("Girdi temizlendi.")
        return PromptSession(
            history=self.history,
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer,
            validator=self.validator,
            key_bindings=bindings,
            style=Style.from_dict({
                'completion-menu.completion': 'bg:#008888 #ffffff',
                'completion-menu.completion.current': 'bg:#00aaaa #000000',
                'scrollbar.arrow': 'bg:#00aaaa #000000',
                'scrollbar.background': 'bg:#003333',
                'scrollbar.button': 'bg:#00aaaa',
            })
        )
    def _get_prompt_string(self) -> HTML: # prompt stringi, arayüzde modifikasyon sağlayacak
        """Prompt string çekici.

        Returns:
            HTML: html text yapısı.
        """
        selected_module = shared_state.get_selected_module()
        if selected_module:
            module_path = f"{selected_module.Category}/{selected_module.Name}"
            return HTML(f'<style underline="true">mahmut</style> (<style fg="ansired">{module_path}</style>) > ')
        return HTML('mahmut > ')
    def get_terminal_width(self) -> int:
        try:
            return shutil.get_terminal_size().columns
        except OSError:
            print(f"Terminal genişliği alınamadı, varsayılan {DEFAULT_TERMINAL_WIDTH} kullanılıyor.")
            return DEFAULT_TERMINAL_WIDTH
    def start(self):
        """Konsol arayüzü başlatıcı.
        """
        #("Konsol başlatılıyor...")
        while self.running:
            try:
                line = self.session.prompt(self._get_prompt_string())
                processed_line = line.strip()
                if not processed_line or processed_line.startswith('#'):
                    continue
                self.command_manager.execute_command(processed_line)
            except EOFError:
                print("EOF algılandı, uygulamadan çıkılıyor.")
                logger.info("EOF algılandı, uygulama kapatılıyor")
                self.running = False
            except KeyboardInterrupt:
                print("Klavye kesintisi algılandı (Ctrl+C).")
                logger.info("Klavye kesintisi (Ctrl+C)")
            except Exception as e:
                print(f"Beklenmedik bir hata oluştu: {e}")
                logger.error(f"Beklenmedik hata: {e}")
                print(f"Hata detayı: {e}", exc_info=True) 
    def shutdown(self):
        """Oturumu kapatıcı
        """
        logger.info("Konsol kapatılıyor")
        print("Konsol kapatıldı.")
        sys.exit(0) 