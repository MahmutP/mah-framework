# Since I have a lot of problems when coding this library, writes the codes in this file by Chatgpt
class SharedState: # Thanks to Chatgpt for closing my deficiencies in object -oriented coding.
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SharedState, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    def _initialize(self):
        self.selected_module = None  
        self.commands = {}           
        self.modules = {}            
        self.aliases = {}            
    def get_selected_module(self):
        return self.selected_module
    def set_selected_module(self, module_obj):
        self.selected_module = module_obj
    def get_commands(self):
        return self.commands
    def add_command(self, command_name: str, command_obj):
        self.commands[command_name] = command_obj
    def get_modules(self):
        return self.modules
    def add_module(self, module_path: str, module_obj):
        self.modules[module_path] = module_obj
    def get_aliases(self):
        return self.aliases
    def add_alias(self, alias_name: str, target_command: str):
        self.aliases[alias_name] = target_command
    def remove_alias(self, alias_name: str):
        if alias_name in self.aliases:
            del self.aliases[alias_name]
            return True
        return False
shared_state = SharedState()