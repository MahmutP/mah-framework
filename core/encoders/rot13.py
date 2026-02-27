import codecs

class Rot13Encoder:
    """
    Kodu ROT13 şifreleme algoritmasıyla maskeleyen encoder.
    """
    
    @staticmethod
    def encode(data: str, **kwargs) -> str:
        """
        Verilen kaynak kodunu ROT13 formatına çevirir.
        
        Args:
            data (str): Şifrelenecek ham Python kodu.
            
        Returns:
            str: Şifrelenmiş ve çalıştırılabilir stub kodu.
        """
        encoded_str = codecs.encode(data, 'rot13')
        
        # Orijinal koddaki escape karakterlerinin (örn \n) rot13 sonrası decode
        # edilirken sorun yaratmaması için raw string veya üçlü tırnak kullanıyoruz.
        stub = f'''
import codecs
try:
    exec(codecs.decode("""{encoded_str}""", 'rot13'))
except Exception:
    pass
'''
        return stub.strip()
