# Terminal tabanlı kullanıcı arayüzünü (Console UI) yöneten modül.
# prompt_toolkit kütüphanesi kullanılarak zengin bir etkileşim deneyimi sunar:
# - Otomatik tamamlama
# - Komut geçmişi (History)
# - Klavye kısayolları (Key bindings)
# - Renklendirilmiş çıktı

import sys
import os
import shutil 
import datetime
from prompt_toolkit import PromptSession # Kullanıcıdan girdi almak için oturum yönetimi
from prompt_toolkit.history import FileHistory # Komut geçmişini dosyada tutmak için (Kalıcı)
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory # Geçmişten gelen komutları silik bir şekilde önermek için
from prompt_toolkit.completion import Completer, Completion # Otomatik tamamlama alt yapısı
from prompt_toolkit.key_binding import KeyBindings # Özel klavye tuş kombinasyonları
from prompt_toolkit.styles import Style # Terminaldeki renk ve stilleri tanımlamak için
from prompt_toolkit.formatted_text import HTML # Prompt metnini HTML benzeri etiketlerle biçimlendirmek için
# Framework'ün diğer bileşenleri
from core.shared_state import shared_state
from core.command_manager import CommandManager 
from core.module_manager import ModuleManager 
from core.completer import CLICompleter # Özel tamamlama mantığı
from core.validator import CLIValidator # Girdi doğrulama (henüz aktif kullanılmıyor olabilir)
from core.cont import DEFAULT_TERMINAL_WIDTH
from core.hooks import HookType
from core import logger
from rich import print

class Console:
    """
    Ana Konsol Sınıfı.
    Kullanıcı ile framework arasındaki etkileşimi yöneten döngüyü (REPL - Read-Eval-Print Loop) barındırır.
    """
    
    def __init__(self, command_manager: CommandManager, module_manager: ModuleManager) -> None:
        """
        Konsol nesnesini başlatır ve gerekli bileşenleri hazırlar.

        Args:
            command_manager (CommandManager): Komutları işlemek için gerekli yönetici.
            module_manager (ModuleManager): Modüllerle ilgili işlemler için gerekli yönetici.
        """
        self.command_manager = command_manager
        self.module_manager = module_manager
        
        # Komut geçmişini başlat (Kalıcı olarak dosyada tutulur)
        # Framework root dizinini bul (core klasörünün bir üstü)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        history_file = os.path.join(base_dir, ".mah_history")
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
        @bindings.add('c-c')
        def _(event):
            """
            Kullanıcı Ctrl+C'ye bastığında çalışacak fonksiyon.
            Normal terminal davranışının aksine, uygulamayı kapatmak yerine
            sadece o anki satırı temizler (SIGINT iptali).
            """
            # Prompt üzerindeyken Ctrl+C sadece girdiyi temizlemelidir.
            # event.app.current_buffer.text = '' ile satır içeriği silinir.
            event.app.current_buffer.text = '' 
            # İsteğe bağlı olarak kullanıcıya bilgi verilebilir:
            # print("Girdi temizlendi.") 

        # Oturumu başlat ve ayarları uygula
        return PromptSession(
            history=self.history, # Geçmiş yönetimi (Artık FileHistory)
            auto_suggest=AutoSuggestFromHistory(), # Geçmişten öneriler (sağ ok ile tamamlama)
            completer=self.completer, # Tab ile tamamlama mantığı
            validator=self.validator, # Girdi doğrulama
            key_bindings=bindings, # Tuş atamaları
            style=Style.from_dict({
                # Otomatik tamamlama menüsünün renkleri
                'completion-menu.completion': 'bg:#008888 #ffffff', # Seçili olmayan öğe
                'completion-menu.completion.current': 'bg:#00aaaa #000000', # Seçili öğe
                'scrollbar.arrow': 'bg:#00aaaa #000000',
                'scrollbar.background': 'bg:#003333',
                'scrollbar.button': 'bg:#00aaaa',
            })
        )

    def _get_prompt_string(self) -> HTML:
        """
        Kullanıcıya gösterilecek komut istemi (prompt) metnini dinamik olarak oluşturur.
        Örnek: 'mahmut (exploit/multi/handler) > '

        Returns:
            HTML: Biçimlendirilmiş prompt metni.
        """
        # Eğer bir modül seçiliyse, modül yolunu prompt'ta göster
        selected_module = shared_state.get_selected_module()
        if selected_module:
            module_path = selected_module.Path
            # Modül yolunu kırmızı renkte (<style fg="ansired">) göster
            return HTML(f'<u>mahmut</u> (<style fg="ansired">{module_path}</style>) > ')
        
        # Modül seçili değilse standart prompt
        return HTML('<u>mahmut</u> > ')

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
            print(f"Terminal genişliği alınamadı, varsayılan {DEFAULT_TERMINAL_WIDTH} kullanılıyor.")
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
        if not processed_line or processed_line.startswith('#'):
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
            except Exception as e:
                # Beklenmeyen diğer tüm hatalar için
                print(f"[bold red]Beklenmedik hata:[/bold red] Konsol döngüsünde hata oluştu.")
                logger.exception(f"Konsol döngüsünde beklenmedik hata")

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
            print(f"[bold yellow]Uyarı:[/bold yellow] Kayıt bitirilmeden çıkış yapıldı.")
            print(f"Komutlar otomatik olarak '[bold cyan]{filename}[/bold cyan]' dosyasına kaydediliyor...")
            
            # Record komutunu 'stop' parametresiyle çağırarak kaydetme işlemini yap
            self.command_manager.execute_command(f"record stop {filename}")
            
        self.running = False
        
        # Eklentilere kapanış sinyali gönder (ON_SHUTDOWN hook)
        if shared_state.plugin_manager:
            shared_state.plugin_manager.trigger_hook(HookType.ON_SHUTDOWN)
        
        logger.info("Konsol kapatılıyor")
        print("Konsol kapatıldı.")