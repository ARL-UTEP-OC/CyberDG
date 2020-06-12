import hashlib


# Generates hash for exploit
def hash(file):
    f = file
    hashr = hashlib.md5()
    binary = f.read()
    if isinstance(binary, bytes):
        binary = binary.decode().replace('\r\n', '\n')
    if isinstance(binary, str):
        binary = binary.encode()
    binary = binary.strip()
    hashr.update(binary)
    return hashr.hexdigest()
