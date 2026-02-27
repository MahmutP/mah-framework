class UnicodeEncoder:
    """
    Kodu Unicode Escape (\\uXXXX veya \\xXX) dizilerine çeviren encoder.
    Statiği analiz eden bazı temel araçları atlatmak için kullanışlıdır.
    """
    
    @staticmethod
    def encode(data: str, **kwargs) -> str:
        """
        Verilen kaynak kodunu unicode_escape formatına çevirir.
        
        Args:
            data (str): Şifrelenecek ham Python kodu.
            
        Returns:
            str: Şifrelenmiş ve çalıştırılabilir stub kodu.
        """
        # Her karakteri zorla \uXXXX formatına çeviriyoruz ki tam bir obfuscation sağlansın.
        # Python'ın yerleşik 'unicode_escape' metodu normal ASCII karakterlerini olduğu gibi bırakır.
        encoded_str = "".join(f"\\\\u{ord(c):04x}" for c in data)
        
        stub = f"""
import codecs
try:
    exec(codecs.decode(b'''{encoded_str}''', 'unicode_escape').decode('utf-8'))
except Exception:
    pass
"""
        return stub.strip()
