from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from pathlib import Path
import base64


private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

Path("private_key.pem").write_bytes(private_pem)
Path("public_key.pem").write_bytes(public_pem)

print("Ключи успешно созданы.")

raw_public = (
    public_key.public_numbers().x.to_bytes(32, 'big') +
    public_key.public_numbers().y.to_bytes(32, 'big')
)
vapid_public_key_b64 = base64.urlsafe_b64encode(raw_public).rstrip(b'=')
print(f"Публичный ключ для клиента (JS): {vapid_public_key_b64.decode('utf-8')}")
