# OWASP A07:2021 - Identification and Authentication Failures
# Trigger: hardcoded default credentials + comparison against a constant password.
# Expected rule hit: OWASP-A07 (patterns: password == 'admin', default_password)

default_password = "admin"

def login(username, password):
    # VULNERABLE: hardcoded credential check, no hashing, no rate limiting.
    if username == "admin" and password == 'admin':
        return {"token": "static-token-for-everyone"}
    return {"error": "invalid"}
