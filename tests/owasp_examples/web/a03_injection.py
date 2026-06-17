# OWASP A03:2021 - Injection (SQL + OS command)
# Trigger: untrusted input concatenated into a query and a shell command.
# Expected rule hit: OWASP-A03 (patterns: SELECT * FROM, cursor.execute(, os.system()

import os

def find_user(cursor, username):
    # VULNERABLE: string-built SQL -> SQL injection.
    cursor.execute("SELECT * FROM users WHERE name = '" + username + "'")
    return cursor.fetchall()

def ping(host):
    # VULNERABLE: shell command injection.
    os.system("ping -c 1 " + host)
