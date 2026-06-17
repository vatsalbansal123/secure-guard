# OWASP A09:2021 - Security Logging and Monitoring Failures
# Trigger: security-relevant events swallowed; sensitive data logged.
# (No dedicated rule yet -- LLM analysis should flag both problems.)

import logging

def login(user, password):
    try:
        authenticate(user, password)
    except Exception:
        pass   # VULNERABLE: failed logins are silently swallowed -> no alerting

    # VULNERABLE: logging secrets in plaintext.
    logging.info("login attempt user=%s password=%s", user, password)
