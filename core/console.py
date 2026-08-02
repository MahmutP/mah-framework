# Terminal tabanlı kullanıcı arayüzünü (Console UI) yöneten modül.
# prompt_toolkit kütüphanesi kullanılarak zengin bir etkileşim deneyimi sunar:
# - Otomatik tamamlama
# - Komut geçmişi (History)
# - Klavye kısayolları (Key bindings)
# - Renklendirilmiş çıktı

import datetime
import os
import shutil
from typing import Any

from prompt_toolkit import (
    PromptSession,  # Kullanıcıdan girdi almak için oturum yönetimi
)
from prompt_toolkit.auto_suggest import (
    AutoSuggestFromHistory,  # Geçmişten gelen komutları silik bir şekilde önermek için
)
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import (
    HTML,  # Prompt metnini HTML benzeri etiketlerle biçimlendirmek için
)
from prompt_toolkit.history import (
    FileHistory,  # Komut geçmişini dosyada tutmak için (Kalıcı)
)
from prompt_toolkit.key_binding import KeyBindings  # Özel klavye tuş kombinasyonları
from prompt_toolkit.styles import Style  # Terminaldeki renk ve stilleri tanımlamak için
from prompt_toolkit.validation import ValidationError, Validator
from rich import print

from core import logger
from core.command_manager import CommandManager
from core.completer import CLICompleter  # Özel tamamlama mantığı
from core.cont import DEFAULT_TERMINAL_WIDTH
from core.hooks import HookType
from core.module_manager import ModuleManager

# Framework'ün diğer bileşenleri
from core.shared_state import shared_state

MAX_HISTORY_LINES = 2000
_PROMPT_UNSET = object()


def _trim_history_file(history_file: str, max_lines: int = MAX_HISTORY_LINES) -> None:
    """Büyük .mah_history dosyasını son N satıra indirger (prompt gecikmesini keser)."""
    try:
        if not os.path.exists(history_file):
            return
        with open(history_file, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        if len(lines) <= max_lines:
            return
        with open(history_file, "w", encoding="utf-8") as f:
            f.writelines(lines[-max_lines:])
    except OSError:
        pass


class CLIValidator(Validator):
    """
    Komut Satırı Doğrulayıcısı (CLI Validator).

    Kullanıcı bir komut girip Enter tuşuna bastığında, bu sınıf devreye girer.
    Girdinin geçerli bir komut olup olmadığını kontrol eder.
    Eğer geçersizse, hata mesajı gösterir ve komutun çalışmasını engeller.
    """

    def __init__(
        self, command_manager: "CommandManager", module_manager: "ModuleManager"
    ):
        """
        Validator'ü başlatır.

        Args:
            command_manager: Komutların geçerliliğini kontrol etmek için gerekli yönetici.
            module_manager: Modüllerin varlığını kontrol etmek için gerekli yönetici.
        """
        self.command_manager = command_manager
        self.module_manager = module_manager

    def validate(self, document: Document) -> None:
        """
        Doğrulama işleminin yapıldığı ana metod.

        Args:
            document (Document): Kullanıcının girdiği metin ve imleç bilgisi.

        Raises:
            ValidationError: Girdi geçersizse fırlatılan hata.
        """
        text = document.text.strip()

        # Yorum satırlarını (#) ve boş satırları doğrulama dışı bırak (geçerli say).
        if text.startswith("#"):
            return
        if not text:
            return

        parts = text.split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # 1. Komutun var olup olmadığını kontrol et.
        resolved_command_name, _is_alias = self.command_manager.resolve_command(
            command_name
        )

        if not resolved_command_name:
            # Komut bulunamadıysa hata fırlat (İmleci komut sonuna getir).
            raise ValidationError(
                message=f"Hata: '{command_name}' bilinmeyen bir komut veya alias.",
                cursor_position=len(command_name),
            )

        # 2. 'use' komutu özel kontrolü.
        if resolved_command_name == "use":
            # Modül yolu girilmemişse hata ver.
            if not args:
                raise ValidationError(
                    message="Hata: 'use' komutu bir modül yolu gerektirir.",
                    cursor_position=len(text),
                )

            # Katalogda var mı bak (lazy load tetikleme — get_module kullanma).
            module_path = args.strip()
            has_module = getattr(self.module_manager, "has_module", None)
            exists = (
                has_module(module_path)
                if callable(has_module)
                else module_path in self.module_manager.get_all_modules()
            )
            if not exists:
                raise ValidationError(
                    message=f"Hata: '{module_path}' modülü bulunamadı.",
                    cursor_position=len(text),
                )


class Console:
    """
    Ana Konsol Sınıfı.
    Kullanıcı ile framework arasındaki etkileşimi yöneten döngüyü (REPL - Read-Eval-Print Loop) barındırır.
    """

    def __init__(
        self,
        command_manager: CommandManager,
        module_manager: ModuleManager,
        context: Any = None,
    ) -> None:
        """
        Konsol nesnesini başlatır ve gerekli bileşenleri hazırlar.

        Args:
            command_manager (CommandManager): Komutları işlemek için gerekli yönetici.
            module_manager (ModuleManager): Modüllerle ilgili işlemler için gerekli yönetici.
            context (Any, optional): AppContext örneği (DI için).
        """
        self.command_manager = command_manager
        self.module_manager = module_manager
        self._context = context
        self._prompt_cache_key: Any = _PROMPT_UNSET
        self._prompt_cache: HTML | None = None

        # Komut geçmişini başlat (Kalıcı olarak dosyada tutulur)
        # Framework root dizinini bul (core klasörünün bir üstü)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        history_file = os.path.join(base_dir, ".mah_history")
        _trim_history_file(history_file, max_lines=2000)
        self.history = FileHistory(history_file)

        # Otomatik tamamlama nesnesini oluştur
        self.completer = CLICompleter(command_manager, module_manager)

        # Girdi doğrulayıcı nesnesini oluştur
        self.validator = CLIValidator(command_manager, module_manager)

        # Prompt oturumunu yapılandır
        self.session = self._create_session()

        # Konsol döngüsünün çalışıp çalışmadığını kontrol eden bayrak
        self.running = True

    def _create_session(self) -> PromptSession:
        """
        prompt_toolkit oturumunu (session) oluşturur ve yapılandırır.
        Stiller, tuş atamaları ve tamamlama ayarları burada yapılır.

        Returns:
            PromptSession: Hazırlanan oturum nesnesi.
        """
        bindings = KeyBindings()

        # Ctrl+C tuş kombinasyonu için özel işlem
        @bindings.add("c-c")
        def _(event: Any) -> None:
            """
            Kullanıcı Ctrl+C'ye bastığında çalışacak fonksiyon.
            Normal terminal davranışının aksine, uygulamayı kapatmak yerine
            sadece o anki satırı temizler (SIGINT iptali).
            """
            # Prompt üzerindeyken Ctrl+C sadece girdiyi temizlemelidir.
            # event.app.current_buffer.text = '' ile satır içeriği silinir.
            event.app.current_buffer.text = ""
            # İsteğe bağlı olarak kullanıcıya bilgi verilebilir:
            # print("Girdi temizlendi.")

        # Oturumu başlat ve ayarları uygula
        return PromptSession(
            history=self.history,  # Geçmiş yönetimi (Artık FileHistory)
            auto_suggest=AutoSuggestFromHistory(),  # Geçmişten öneriler (sağ ok ile tamamlama)
            completer=self.completer,  # Tab ile tamamlama mantığı
            validator=self.validator,  # Girdi doğrulama
            key_bindings=bindings,  # Tuş atamaları
            style=Style.from_dict(
                {
                    # Otomatik tamamlama menüsünün renkleri
                    "completion-menu.completion": "bg:#008888 #ffffff",  # Seçili olmayan öğe
                    "completion-menu.completion.current": "bg:#00aaaa #000000",  # Seçili öğe
                    "scrollbar.arrow": "bg:#00aaaa #000000",
                    "scrollbar.background": "bg:#003333",
                    "scrollbar.button": "bg:#00aaaa",
                }
            ),
        )

    def _get_prompt_string(self) -> HTML:
        """
        Kullanıcıya gösterilecek komut istemi (prompt) metnini dinamik olarak oluşturur.
        Modül seçimi değişmedikçe cache'lenir.
        """
        selected_module = shared_state.get_selected_module()
        cache_key = selected_module.Path if selected_module else None
        if cache_key == self._prompt_cache_key and self._prompt_cache is not None:
            return self._prompt_cache

        if selected_module:
            module_path = selected_module.Path
            prompt = HTML(
                f'<u>mahmut</u> (<style fg="ansired">{module_path}</style>) > '
            )
        else:
            prompt = HTML("<u>mahmut</u> > ")

        self._prompt_cache_key = cache_key
        self._prompt_cache = prompt
        return prompt

    def get_terminal_width(self) -> int:
        """
        Mevcut terminal penceresinin genişliğini (sütun sayısı) döndürür.
        Çıktıları hizalamak için kullanılır.

        Returns:
            int: Sütun sayısı (genişlik). Başarısız olursa varsayılan değeri döner.
        """
        try:
            return shutil.get_terminal_size().columns
        except OSError:
            # Terminal boyutu alınamazsa (örn: pipe içine yazılıyorsa) varsayılanı kullan.
            print(
                f"Terminal genişliği alınamadı, varsayılan {DEFAULT_TERMINAL_WIDTH} kullanılıyor."
            )
            return DEFAULT_TERMINAL_WIDTH

    def _handle_input(self, user_input: str) -> None:
        """
        Kullanıcıdan alınan ham metin girdisini işler.

        Bu metod, Kullanıcı Arayüzü (UI) ile İş Mantığı (Logic) arasındaki köprüdür.
        Console sınıfı 'ne zaman' komut çalıştırılacağını bilir,
        CommandManager ise 'nasıl' çalıştırılacağını bilir.

        Args:
            user_input (str): Kullanıcının enter tuşuna bastığında gönderdiği satır.
        """
        processed_line = user_input.strip()

        # Boş satırları (sadece enter) ve yorum satırlarını (# ile başlayan) yoksay.
        if not processed_line or processed_line.startswith("#"):
            return

        # Komutun çalıştırılması için CommandManager'a devret.
        self.command_manager.execute_command(processed_line)

    def start(self) -> None:
        """
        Konsol döngüsünü (Main Loop) başlatan ana metod.

        Görevleri:
        1. Prompt'u ekrana basmak.
        2. Kullanıcı girdisini beklemek.
        3. Girdiyi alıp işleyiciye göndermek.
        4. Hataları (Ctrl+C, EOF) yakalamak.
        """
        logger.info("Konsol başlatıldı")
        while self.running:
            try:
                # Kullanıcıdan girdi al (Bloklayıcı işlem)
                line = self.session.prompt(self._get_prompt_string())

                # Girdiyi işle
                self._handle_input(line)

            except EOFError:
                # Kullanıcı Ctrl+D tuşuna bastığında (End Of File)
                print("EOF algılandı, uygulamadan çıkılıyor.")
                logger.info("EOF algılandı, uygulama kapatılıyor")
                self.running = False
            except KeyboardInterrupt:
                # Kullanıcı Ctrl+C tuşuna bastığında (genellikle prompt session içinde yakalanır ama burası güvenlik ağıdır)
                print("Klavye kesintisi algılandı (Ctrl+C).")
                logger.info("Klavye kesintisi (Ctrl+C)")
            except Exception:
                # Beklenmeyen diğer tüm hatalar için
                print(
                    "[bold red]Beklenmedik hata:[/bold red] Konsol döngüsünde hata oluştu."
                )
                logger.exception("Konsol döngüsünde beklenmedik hata")

    def shutdown(self) -> None:
        """
        Konsolu güvenli bir şekilde kapatmak için çağrılır.
        Kapanış hook'larını tetikler ve döngüyü sonlandırır.
        """
        if not self.running:  # Zaten kapalıysa işlem yapma
            return

        # Otomatik kayıt kontrolü
        if shared_state.is_recording and shared_state.recorded_commands:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"autosave_{timestamp}.rc"
            print("[bold yellow]Uyarı:[/bold yellow] Kayıt bitirilmeden çıkış yapıldı.")
            print(
                f"Komutlar otomatik olarak '[bold cyan]{filename}[/bold cyan]' dosyasına kaydediliyor..."
            )

            # Record komutunu 'stop' parametresiyle çağırarak kaydetme işlemini yap
            self.command_manager.execute_command(f"record stop {filename}")

        self.running = False

        # Eklentilere kapanış sinyali gönder (ON_SHUTDOWN hook)
        if shared_state.plugin_manager:
            shared_state.plugin_manager.trigger_hook(HookType.ON_SHUTDOWN)

        # Tüm iletişim oturumlarını ve arka plan handler dinleyicilerini durdur
        if shared_state.session_manager:
            shared_state.session_manager.shutdown_all()

        logger.info("Konsol kapatılıyor")
        print("Konsol kapatıldı.")
