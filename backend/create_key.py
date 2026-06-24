"""Mint a new SecureGuard API key.

Usage (from the backend/ directory):
    python create_key.py "my dev key"

The plaintext key is printed ONCE. Store it now — only its hash is kept.
"""

import sys

from auth import create_api_key

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "default"
    key = create_api_key(name)
    print(f"API key created for '{name}'.")
    print("Store it now — it will not be shown again:\n")
    print(f"    {key}\n")
    print("Send it on requests as:  X-API-Key: <key>")
