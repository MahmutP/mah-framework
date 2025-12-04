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
        