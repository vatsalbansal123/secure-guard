# OWASP A02:2021 - Cryptographic Failures
# Trigger: weak hashing + secrets/passwords stored in plaintext.
# Expected rule hit: OWASP-A02 (patterns: md5, sha1, password =, secret =)

import hashlib

def hash_password(pw: str) -> str:
    # VULNERABLE: MD5 is fast and broken; no salt.
    return hashlib.md5(pw.encode()).hexdigest()

# VULNERABLE: plaintext secrets in source.
password = "SuperSecret123"
secret = "stripe_live_key_abc"

def store(user):
    db.save(user.id, hash_password(user.pw))
