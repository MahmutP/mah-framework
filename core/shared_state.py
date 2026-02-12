# Uygulamanın çalışma zamanındaki durumunu (state) tutan ve tüm modüllerin erişebildiği merkezi yapı.
# Singleton tasarım deseni kullanılarak, uygulama genelinde tek bir örneğinin olması garanti altına alınmıştır.

class SharedState:
    """
    Paylaşılan Durum (Shared State) Sınıfı.
    
    Bu sınıf, uygulamanın farklı parçaları (Konsol, Komut Yöneticisi, Modül Yöneticisi vb.)
    arasında veri ve nesne paylaşımını sağlar. Global değişken kullanmak yerine bu güvenli yapı tercih edilir.
    """
    
    _instance = None # Singleton örneğini tutan sınıf değişkeni
    
    def __new__(cls):
        """
        Sınıfın yeni bir örneğini oluşturur.
        Eğer daha önce oluşturulmuşsa, mevcut örneği döndürür (Singleton Pattern).
        """
        if cls._instance is None:
            cls._instance = super(SharedState, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        Paylaşılan değişkenleri varsayılan değerleriyle başlatır.
        Sadece ilk kez nesne oluşturulduğunda çalışır.
        """
        # --- Modül Durumu ---
        # Kullanıcının o an seçtiği (use komutuyla girdiği) modül nesnesi.
        self.selected_module = None
        
        # --- Servis Referansları (Service Locator) ---
        # Döngüsel bağımlılıkları (circular imports) önlemek için yöneticiler buraya sonradan atanır.
        
        self.command_manager = None 
        """Komut yöneticisi referansı."""
        
        self.module_manager = None
        """Modül yöneticisi referansı."""
        
        self.console_instance = None
        """Aktif konsol nesnesi referansı."""
        
        self.plugin_manager = None
        """Plugin yöneticisi referansı."""
        
        self.session_manager = None
        """Oturum (Session) yöneticisi referansı."""
        
        # --- Makro ve Kayıt Özellikleri ---
        self.is_recording = False
        """Komut kaydının (makro) açık olup olmadığını belirtir."""
        
        self.recorded_commands = []
        """Kaydedilen komutların listesi."""


    def get_selected_module(self):
        """
        O anki seçili modülü döndürür.
        
        Returns:
            Seçili modül nesnesi veya None.
        """
        return self.selected_module

    def set_selected_module(self, module_obj):
        """
        Seçili modülü günceller.
        'use' komutu çalıştığında bu metod kullanılır.

        Args:
            module_obj: Yeni seçilen modül nesnesi.
        """
        self.selected_module = module_obj

# Uygulama genelinde kullanılacak tekil (singleton) nesne.
# Diğer modüller `from core.shared_state import shared_state` diyerek buna erişir.
shared_state = SharedState()