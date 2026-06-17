# OWASP A04:2021 - Insecure Design
# Trigger: unsafe deserialization + dynamic eval + disabled TLS verification.
# Expected rule hit: OWASP-A04 (patterns: eval(, pickle.loads(, yaml.load(, verify=False)

import pickle, yaml, requests

def load_session(blob):
    # VULNERABLE: deserializing untrusted data executes arbitrary code.
    return pickle.loads(blob)

def parse_config(text):
    return yaml.load(text)            # VULNERABLE: full-loader can build objects

def run(expr):
    return eval(expr)                 # VULNERABLE: arbitrary code execution

def fetch(url):
    return requests.get(url, verify=False)   # VULNERABLE: TLS verification off
