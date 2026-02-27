from core.encoders.base64 import Base64Encoder
from core.encoders.xor import XorEncoder
from core.encoders.hex import HexEncoder
from core.encoders.rot13 import Rot13Encoder
from core.encoders.unicode_escape import UnicodeEncoder
from core.logger import logger
import random

def apply_encoding(data: str, encode_string: str) -> str:
    """
    Girilen virgülle ayrılmış encoder listesini (zincirini) uygular.
    Örn: encode_string="base64,rot13,hex" 
    İlk önce base64, onun çıktısını rot13, onun da çıktısını hex diyerek
    katman katman (matruşka gibi) kodlar. Hedef bilgisayarda ise zincirin tam tersi
    çalışarak katmanları tek tek açıp asıl kodu execute eder.
    
    Args:
        data (str): Ham payload kodu.
        encode_string (str): Virgülle ayrılmış şifreleme zinciri (örn: 'base64, xor').

    Returns:
        str: Katmanlı şifrelenmiş kod.
    """
    if not encode_string or encode_string.lower() == "none":
        return data

    # Boşlukları temizle ve listeye ayır. (Örn: ' base64 , xor ' -> ['base64', 'xor'])
    encoder_chain = [e.strip().lower() for e in encode_string.split(',')]
    current_data = data
    
    for enc in encoder_chain:
        if enc == "base64":
            current_data = Base64Encoder.encode(current_data)
        elif enc == "xor":
            # Her xor katmanında farklı bir anahtar üretilir
            current_data = XorEncoder.encode(current_data, key=random.randint(1, 255))
        elif enc == "hex":
            current_data = HexEncoder.encode(current_data)
        elif enc == "rot13":
            current_data = Rot13Encoder.encode(current_data)
        elif enc == "unicode_escape":
            current_data = UnicodeEncoder.encode(current_data)
        else:
            logger.warning(f"[!] Bilinmeyen encoder atlandı: '{enc}'")

    return current_data
