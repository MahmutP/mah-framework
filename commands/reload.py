from core.command import Command
from core.shared_state import shared_state
from rich import print

class ReloadCommand(Command):
    Name = "reload"
    Description = "Tüm framework bileşenlerini veya sadece belirli bir modülü yeniden yükler."
    Aliases = []
    Category = "core"
    Usage = "reload [module_path]"
    Examples = [
        "reload                   # Tüm özellikleri baştan yükler (Tam temizlik)",
        "reload exploit/x/y       # Sadece belirtilen modülü (örneğin exploit/x/y) baştan yükler"
    ]

    def execute(self, *args) -> bool:
        if args and len(args) > 0:
            # Belirli modülü hot-reload yap
            module_path = args[0]
            print(f"[*] Sadece '{module_path}' modülü yeniden yükleniyor...")
            success = shared_state.module_manager.reload_module(module_path)
            if success:
                print(f"[+] '{module_path}' başarıyla yeniden yüklendi.")
            else:
                print(f"[-] '{module_path}' yüklenirken bir sorun oluştu.")
        else:
            # Tüm sistemi reload yap
            print("[*] Tüm framework bileşenleri yeniden yükleniyor...")
            try:
                # Modülleri yeniden tara ve yükle
                shared_state.module_manager.load_modules()
                
                # Eklentileri baştan yükle
                if shared_state.plugin_manager:
                    shared_state.plugin_manager.load_plugins()
                
                # Komutları baştan yükle
                if shared_state.command_manager:
                    # Mevcut komut registry'sini temizleyip yeniden komut dizinini taraması sağlanabilir
                    # (CommandManager class yapısına göre gerekirse eklenecek)
                    pass
                
                print("[+] Reload işlemi tamamlandı.")
            except Exception as e:
                print(f"[-] Reload sırasında hata oluştu: {e}")
                return False
                
        return True
