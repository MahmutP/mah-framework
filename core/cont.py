LOG_LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50
} # logging kütüphanesi için örnek bir cont.py değişkeni
DEFAULT_LOG_LEVEL = "INFO" # logging kütüphanesi için örnek cont.py değişkeni
LOG_DIR = "config/logs" # uygun bir logging sistemi geliştirilmeli
ALIASES_FILE = "config/aliases.json" # repl ortamı için alias dosyası
DEFAULT_TERMINAL_WIDTH = 120
LEFT_PADDING = 4  
COL_SPACING = 4   
TAB_SPING = 8     
COMMAND_CATEGORIES = {
    "core": "Core Commands",
    "module": "Module Commands",
    "system": "System Commands"
}# komut katagorileri
DEFAULT_REGEX = r".*" # default regex