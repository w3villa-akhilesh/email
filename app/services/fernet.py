import os
from cryptography.fernet import Fernet

def encrypt_text(plaintext: str, FERNET_KEY) -> str:
    fernet = Fernet(FERNET_KEY)

    return fernet.encrypt(plaintext.encode()).decode()

def decrypt_text(ciphertext: str, FERNET_KEY) -> str:
    fernet = Fernet(FERNET_KEY)

    return fernet.decrypt(ciphertext.encode()).decode()

if __name__ == "__main__":
    import sys
    
    key = Fernet.generate_key()
    # print(key.decode())  # Save this securely!
    FERNET_KEY = "lMYfExawG7duyzTBpTr87W4soCWy0m3WahyUF-nUM4o="

    raw_key = "sk-I_XONfhP_xpEOuX5JDAbvw"
    encrypted = encrypt_text(raw_key, FERNET_KEY)
    print("Encrypted Key:", encrypted)

    # Example decrypt (can be removed or replaced in prod)
    print("Decrypted Back:", decrypt_text(encrypted, FERNET_KEY))