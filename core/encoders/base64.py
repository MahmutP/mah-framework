import base64

class Base64Encoder:
    """
    Basit Base64 Encoder Wrapper.
    """
    @staticmethod
    def encode(data: str) -> str:
        """
        Verilen string veriyi Base64 formatına çevirir ve
        çalışma anında decode edip çalıştıracak bir Python stub'ı döndürür.
        """
        encoded_bytes = base64.b64encode(data.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        
        stub = f"""
import base64, sys
try:
    exec(base64.b64decode("{encoded_str}"))
except Exception as e:
    pass
"""
        return stub.strip()
