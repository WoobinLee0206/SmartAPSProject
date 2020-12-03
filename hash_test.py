from passlib.hash import pbkdf2_sha256

password = '1234'

hash_pw = pbkdf2_sha256.hash(password)
print(hash_pw)
print(pbkdf2_sha256.verify(password, hash_pw))