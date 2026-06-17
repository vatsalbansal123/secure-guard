# OWASP A08:2021 - Software and Data Integrity Failures
# Trigger: downloading and executing code without integrity verification.
# (No dedicated rule yet -- candidate for a future OWASP-A08 rule; LLM analysis
#  should still flag this. Documents an integrity gap for the test suite.)

import urllib.request, subprocess

def install_plugin(url):
    # VULNERABLE: fetch remote code over the network and run it, no signature
    # check, no checksum, no pinned hash.
    urllib.request.urlretrieve(url, "/tmp/plugin.sh")
    subprocess.call(["bash", "/tmp/plugin.sh"])
