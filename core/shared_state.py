class SharedState:
    """Paylaşılmış alan ana fonksiyonu.

    Returns:
        _type_: _description_
    """
    _instance = None
    def __new__(cls):
        """Yeni oluşturucu

        Returns:
            _type_: obje çıktısı.
        """
        if cls._instance is None:
            cls._instance = super(SharedState, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    def _initialize(self):
        """initialize ana fonksiyon.
        """
        self.selected_module = None  
        self.commands = {}           
        self.modules = {}            
        self.aliases = {}            
    def get_selected_module(self):
        """Seçili modülü çağırmaya yarıyan fonksiyon

        Returns:
            _type_: seçilen fonksiyon.
        """
        return self.selected_module
    def set_selected_module(self, module_obj):
        """Seçili modülü değiştirmeye yarıyan fonksiyon.

        Args:
            module_obj (_type_): Modül objesi.
        """
        self.selected_module = module_obj
    def get_commands(self):
        """Komutları çekmeye yarıyan fonksiyon.

        Returns:
            _type_: Komutlar.
        """
        return self.commands
    def add_command(self, command_name: str, command_obj):
        """Komut eklemeye yarıyan fonksiyon.

        Args:
            command_name (str): Komut ismi.
            command_obj (_type_): Komut objesi.
        """
        self.commands[command_name] = command_obj
    def get_modules(self):
        """Modülleri çekmeye yarıyan fonksiyon.

        Returns:
            _type_: Modüller.
        """
        return self.modules
    def add_module(self, module_path: str, module_obj):
        """Modül eklemeye yarıyan fonksiyon.

        Args:
            module_path (str): Modül yolu.
            module_obj (_type_): Modül objesi.
        """
        self.modules[module_path] = module_obj
    def get_aliases(self):
        """Alias'ları çekmeye yarıyan fonksiyon.

        Returns:
            _type_: alias'lar.
        """
        return self.aliases
    def add_alias(self, alias_name: str, target_command: str):
        """Alias eklemeye yarıyan fonksiyon.

        Args:
            alias_name (str): alias adı.
            target_command (str): hedef komut.
        """
        self.aliases[alias_name] = target_command
    def remove_alias(self, alias_name: str):
        """Alias silici.

        Args:
            alias_name (str): alias ismi.

        Returns:
            _type_: Başarılı olup olmadığının kontrolü.
        """
        if alias_name in self.aliases:
            del self.aliases[alias_name]
            return True
        return False
shared_state = SharedState()