import base64
import hashlib

from Cryptodome import Random
from Cryptodome.Hash import SHA
from Cryptodome.Math.Numbers import Integer
from Cryptodome.Util.number import ceil_div, bytes_to_long, long_to_bytes, size
from Cryptodome.Util.py3compat import bchr, bord, b
from Cryptodome.Cipher import PKCS1_v1_5

'''
pycrypto doesn't allow non hash objects in Cryptodome.Signature.PKCS115_SigScheme.
This modified PKCS115_Cipher function encrypts messages using (d,n) instead of (e,n)
and using 0xFF when padding rather than random bytes.
It's equivalent to the RSA/ECB/PKCS1Padding when encrypting data using private keys in Java.
'''


def cipher(key, message):
    mod_bits = size(key.n)
    k = ceil_div(mod_bits, 8)
    m_len = len(message)

    # Step 1
    if m_len > k - 11:
        raise ValueError("Plaintext is too long.")
    # Step 2a
    ps = []
    while len(ps) != k - m_len - 3:
        new_byte = bchr(0xFF)
        if bord(new_byte[0]) == 0x00:
            continue
        ps.append(new_byte)
    ps = b("").join(ps)
    assert (len(ps) == k - m_len - 3)
    # Step 2b
    em = b('\x00\x01') + ps + bchr(0x00) + message
    # Step 3a (OS2IP)
    em_int = bytes_to_long(em)
    # Step 3b (RSAEP)
    if not 0 < em_int < key._n:
        raise ValueError("Plaintext too large")
    m_int = int(pow(Integer(em_int), key._d, key._n))
    # Step 3c (I2OSP)
    c = long_to_bytes(m_int, k)
    return c


def rsa_encrypt(key, data):
    s = b''
    for a in [cipher(key, data[i:i + 117]) for i in range(0, len(data), 117)]:
        s += a
    return base64.b64encode(s)


def rsa_decrypt(key, data):
    a = Random.new().read(35)
    return PKCS1_v1_5.new(key).decrypt(base64.b64decode(data), a).decode('utf-8')


def md5_encrypt(s):
    hex_digits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
    m = hashlib.md5()
    m.update(s.encode('utf-8'))
    md5_str = ''
    for b in m.digest():
        md5_str += hex_digits[(b >> 4) & 15]
        md5_str += hex_digits[b % 15]
    return md5_str
