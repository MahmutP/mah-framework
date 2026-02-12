# Bu dosya, tüm komutların türetileceği temel 'Command' sınıfını tanımlar.
# Type hinting (tür ipuçları) için gerekli kütüphaneler içe aktarılıyor.
from typing import List, Dict, Any, Callable, Optional 

# Uygulamanın genel durumunu (shared state) paylaşmak için kullanılan modül.
# Bu sayede komutlar arasında veya komutlar ile ana uygulama arasında veri paylaşımı yapılabilir.
from core.shared_state import shared_state 

# Komut kategorilerini tanımlayan sabit sözlük.
# Bu sözlük, komutların kullanıcı arayüzünde gruplandırılmasına yardımcı olur.
from core.cont import COMMAND_CATEGORIES

# Konsol çıktılarını renklendirmek ve biçimlendirmek için 'rich' kütüphanesi kullanılıyor.
from rich import print

class Command:
    """
    Tüm komutların miras alacağı temel (base) sınıf.
    Her yeni komut bu sınıftan türetilmeli ve gerekli özellikleri/metodları eze (override) etmelidir.
    """
    
    # Komutun adı. Konsolda bu isim yazılarak komut çalıştırılır.
    Name: str = "COMMAND" 
    
    # Komutun ne işe yaradığını açıklayan kısa bir metin. Yardım çıktılarında görünür.
    Description: str = "Description for command" 
    
    # Komutun ait olduğu kategori (örn: 'core', 'module', 'network').
    # Bu kategori, help komutunda komutların gruplanmasını sağlar.
    Category: str = "core" 
    
    # Komut için alternatif isimler (takma adlar).
    # Örneğin 'list' komutu için ['ls', 'dir'] gibi alias'lar tanımlanabilir.
    # Bu özellik, aliases.json dosyasından bağımsız olarak kod içinde alias tanımlamaya olanak tanır.
    Aliases: List[str] = [] 
    
    # Komutun nasıl kullanılacağını gösteren sözdizimi (syntax).
    # Örn: "set <option> <değer>"
    Usage: str = "" 
    
    # Komutun örnek kullanım senaryoları. Kullanıcıya rehberlik etmek için listelenir.
    Examples: List[str] = [] 
    
    # Otomatik tamamlama (tab completion) fonksiyonu.
    # prompt_toolkit veya benzeri kütüphanelerle entegre çalışarak komut argümanlarını tamamlar.
    # Opsiyoneldir, her komut için tanımlanmak zorunda değildir.
    completer_function: Optional[Callable] = None 

    def __init__(self):
        """
        Komut sınıfının yapıcı metodudur (constructor).
        Komut örneği oluşturulduğunda çalışır ve paylaşılan durumu (shared_state) sınıfa bağlar.
        """
        # Komutların uygulama durumuna erişebilmesi için shared_state nesnesi atanır.
        self.shared_state = shared_state

    def execute(self, *args: str, **kwargs: Any) -> bool:
        """
        Komutun asıl işlevini yerine getiren metod.
        Her alt sınıf bu metodu eze (override) etmeli ve kendi mantığını buraya yazmalıdır.
        
        Args:
            *args: Komuta verilen pozisyonel argümanlar.
            **kwargs: Komuta verilen isimlendirilmiş argümanlar (anahtar-değer çiftleri).
            
        Returns:
            bool: Komut başarıyla çalıştıysa True, hata varsa veya başarısızsa False döner.
        """
        # Temel sınıfta bu metod sadece True döner, alt sınıflar bunu ezecektir.
        return True

    def get_category_display_name(self) -> str:
        """
        Komutun kategorisinin kullanıcı dostu (görünen) adını döndürür.
        core.cont.COMMAND_CATEGORIES sözlüğünü kullanarak kategori kodunu (örn: 'core') 
        okunabilir bir isme çevirir.
        
        Returns:
            str: Kategorinin görünen adı. Eğer kategori bulunamazsa varsayılan olarak "Diğer Komutlar" döner.
        """
        # self.Category.lower() ile kategori adı küçük harfe çevrilerek aranır.
        # Eğer sözlükte karşılığı yoksa ikinci argüman olan "Diğer Komutlar" döndürülür.
        return COMMAND_CATEGORIES.get(self.Category.lower(), "Diğer Komutlar")

    def get_completions(self, text: str, word_before_cursor: str) -> List[str]:
        """
        Komut argümanları için otomatik tamamlama önerileri sunar.
        Eğer bu komut için özel bir 'completer_function' tanımlanmışsa, onu çağırır.
        
        Args:
            text (str): Kullanıcının o ana kadar yazdığı tüm metin.
            word_before_cursor (str): İmlecin hemen öncesindeki kelime (tamamlanacak kısım).
            
        Returns:
            List[str]: Önerilen tamamlamaların listesi.
        """
        # Eğer özel bir tamamlama fonksiyonu atanmışsa
        if self.completer_function:
            try:
                # Fonksiyonu çağır ve sonuçları döndür.
                return self.completer_function(text, word_before_cursor)
            except Exception as e:
                # Tamamlama sırasında bir hata oluşursa, hatayı ekrana bas ve boş liste dön.
                # Bu sayede bir komutun tamamlama hatası tüm programı çökertmez.
                print(f"Komut '{self.Name}' tamamlama fonksiyonunda hata: {e}")
                return []
        
        # Eğer tamamlama fonksiyonu yoksa boş liste dön.
        return []
