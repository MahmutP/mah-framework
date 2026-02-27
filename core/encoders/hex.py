import binascii

class HexEncoder:
    """
    Kodu Hexadecimal formata çeviren ve çalışma anında
    unhexlify ile decode edip çalıştıran encoder.
    """
    
    @staticmethod
    def encode(data: str, **kwargs) -> str:
        """
        Verilen kaynak kodunu Hex formatına çevirir.
        
        Args:
            data (str): Şifrelenecek ham Python kodu.
            
        Returns:
            str: Şifrelenmiş ve çalıştırılabilir stub kodu.
        """
        encoded_hex = binascii.hexlify(data.encode('utf-8')).decode('utf-8')
        
        stub = f"""
import binascii
try:
    exec(binascii.unhexlify("{encoded_hex}"))
except Exception:
    pass
"""
        return stub.strip()
