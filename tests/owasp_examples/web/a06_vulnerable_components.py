# OWASP A06:2021 - Vulnerable and Outdated Components
# Trigger: pinning to known-vulnerable dependency versions.
# Expected rule hit: OWASP-A06 (patterns: requirements.txt, package.json)
#
# This sample documents the dependency manifest pattern. The real check happens
# with Snyk (see docs/SNYK_FINDINGS.md) -- our own scan flagged:
#   starlette 1.2.1 (High), python-multipart 0.0.30 (Medium).

REQUIREMENTS_TXT = """
starlette==1.2.1          # VULNERABLE: upgrade to 1.3.0
python-multipart==0.0.30  # VULNERABLE: upgrade to 0.0.31
requests==2.19.0          # VULNERABLE: many CVEs in old releases
"""
