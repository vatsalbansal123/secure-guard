# OWASP A10:2021 - Server-Side Request Forgery (SSRF)
# Trigger: server fetches a user-supplied URL with no allow-list.
# (No dedicated rule yet -- LLM analysis should flag the SSRF.)

import requests

def fetch_avatar(request):
    # VULNERABLE: attacker can point this at internal services, e.g.
    # http://169.254.169.254/latest/meta-data/ (cloud metadata credentials).
    url = request.args.get("url")
    return requests.get(url).content
