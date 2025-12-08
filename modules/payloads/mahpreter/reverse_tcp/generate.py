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
        pass