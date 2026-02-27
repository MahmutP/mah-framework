import unittest
from core.encoders.hex import HexEncoder
from core.encoders.rot13 import Rot13Encoder
from core.encoders.unicode_escape import UnicodeEncoder
from core.encoders.manager import apply_encoding

class TestEncoders(unittest.TestCase):
    def setUp(self):
        self.raw_code = "print('hello from payload')"
        
    def check_execution_success(self, stub: str):
        """
        Üretilen stub kodunun python'ın exec() motorunda 
        varsayılan ortamlarda hata vermeden çalıştığını test eder.
        Orijinal kod string'ini print ettiği için, locals yakalanarak doğrulanabilir, 
        ancak burada sadece sentaks/çalışma hatası fırlatmadığını denetliyoruz.
        """
        try:
            exec(stub, {}, {})
            success = True
        except Exception as e:
            success = False
            print(f"Exec Error: {e}")
            
        self.assertTrue(success, "Üretilen encode stub kodu çalıştırılırken hata verdi!")

    def test_hex_encoder(self):
        encoded_stub = HexEncoder.encode(self.raw_code)
        self.assertIn("binascii.unhexlify", encoded_stub)
        self.assertNotIn("print('hello", encoded_stub)
        self.check_execution_success(encoded_stub)

    def test_rot13_encoder(self):
        encoded_stub = Rot13Encoder.encode(self.raw_code)
        self.assertIn("codecs.decode", encoded_stub)
        self.assertIn("rot13", encoded_stub)
        self.assertNotIn("print('hello", encoded_stub)
        self.check_execution_success(encoded_stub)

    def test_unicode_escape_encoder(self):
        encoded_stub = UnicodeEncoder.encode(self.raw_code)
        self.assertIn("unicode_escape", encoded_stub)
        self.assertNotIn("print('hello", encoded_stub)
        self.check_execution_success(encoded_stub)

    def test_manager_single_encoder(self):
        stub = apply_encoding(self.raw_code, "base64")
        self.assertIn("base64.b64decode", stub)
        self.check_execution_success(stub)

    def test_manager_multiple_encoders_chain(self):
        # Önce hex, sonra rot13, sonra base64 uygulayalım
        chain = "hex, rot13, base64"
        stub = apply_encoding(self.raw_code, chain)
        
        # En dıştaki (son uygulanan) base64 decode olmalıdır.
        self.assertIn("base64.b64decode", stub)
        
        # Orijinal metin kesinlikle görünmemeli
        self.assertNotIn("print('hello", stub)

        # Çalıştığında iç içe (matruşka) decode edip print edebilmeli
        self.check_execution_success(stub)

    def test_manager_unknown_encoder(self):
        # Bilinmeyen encoder ignore edilip ham datayı / sıradakini döndürmeli
        stub = apply_encoding(self.raw_code, "non_existent_encoder_123")
        self.assertEqual(stub, self.raw_code)

if __name__ == '__main__':
    unittest.main()
