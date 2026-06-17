# OWASP A05:2021 - Security Misconfiguration
# Trigger: debug mode on in production + wildcard CORS.
# Expected rule hit: OWASP-A05 (patterns: debug=True, allow_origins=['*'])

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(debug=True)             # VULNERABLE: leaks stack traces

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],             # VULNERABLE: any origin can call the API
    allow_credentials=True,
    allow_methods=['*'],
)
