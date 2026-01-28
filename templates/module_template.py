from core.module import BaseModule
from core.option import Option
from rich import print
import time

class MyCustomModule(BaseModule):
    def __init__(self):
        # --- Modül Bilgileri ---
        # Modülünüzün framework içinde nasıl görüneceğini belirleyin
        self.Name = "category/my_custom_module" # Örn: exploit/linux/ssh/bruteforce
        self.Description = "Bu modül ne işe yarar? (Kısa açıklama)"
        self.Author = "Yazar Adı"
        self.Category = "uncategorized" # exploit, auxiliary, scanner, payload vb.
        
        # --- Seçenekler (Options) ---
        # Kullanıcının 'set' komutuyla değiştirebileceği değişkenler
        self.Options = {
            # Örnek: Zorunlu bir IP adresi parametresi
            "RHOST": Option(
                name="RHOST",
                value="127.0.0.1",
                required=True,
                description="Hedef IP adresi",
                regex_check=True,
                regex=r"^\d{1,3}(\.\d{1,3}){3}$" # Basit IP regex'i
            ),
            # Örnek: Varsayılan değeri olan port parametresi
            "RPORT": Option(
                name="RPORT",
                value=80,
                required=True,
                description="Hedef port numarası"
            ),
            # Örnek: İsteğe bağlı bir metin parametresi
            "TEXT": Option(
                name="TEXT",
                value="Hello",
                required=False,
                description="Gönderilecek mesaj"
            )
        }
        
        # Üst sınıfı başlat (Bunu silmeyin!)
        super().__init__()

    def run(self, options):
        """
        Modül çalıştırıldığında (run komutu) burası tetiklenir.
        """
        # 1. Seçenekleri değişkenlere alalım
        target_ip = options.get("RHOST")
        target_port = options.get("RPORT")
        text = options.get("TEXT")

        # 2. Kullanıcıya bilgi verelim
        print(f"[bold blue][*][/bold blue] Hedef: {target_ip}:{target_port}")
        print(f"[bold blue][*][/bold blue] İşlem başlatılıyor...")
        
        try:
            # 3. Asıl iş mantığınızı buraya yazın
            # Örn: Soket bağlantısı, HTTP isteği, dosya okuma vb.
            
            # Simüle edilmiş işlem
            time.sleep(1) 
            print(f"[green][+][/green] Bağlantı başarılı!")
            print(f"Gönderilen mesaj: {text}")
            
            # İşlem başarılı ise True döndürün
            return True

        except Exception as e:
            # Hata durumunda kullanıcıya bilgi verin
            print(f"[bold red][!][/bold red] Hata oluştu: {e}")
            return False
