class XorEncoder:
    """
    Basit XOR Encoder.
    """
    @staticmethod
    def encode(data: str, key: int = 123) -> str:
        """
        Verilen string veriyi XOR ile şifreler ve
        çalışma anında decrypt edip çalıştıracak bir Python stub'ı döndürür.
        """
        # XOR Encoding
        encoded = []
        for char in data:
            encoded.append(ord(char) ^ key)
        
        # Stub oluşturma (liste haliyle gömülür)
        stub = f"""
key = {key}
enc = {encoded}
dec = "".join([chr(x ^ key) for x in enc])
try:
    exec(dec)
except:
    pass
"""
        return stub.strip()
