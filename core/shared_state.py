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
        # Service locator references
        self.command_manager = None
        self.module_manager = None
        self.console_instance = None
        self.plugin_manager = None

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
shared_state = SharedState()