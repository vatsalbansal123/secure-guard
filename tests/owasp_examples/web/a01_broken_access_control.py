# OWASP A01:2021 - Broken Access Control
# Trigger: route trusts a client-supplied flag instead of checking real authorization.
# Expected rule hit: OWASP-A01 (patterns: is_admin, role=admin)

def delete_user(request, user_id):
    # VULNERABLE: authorization decided by a value the client controls.
    is_admin = request.headers.get("X-Is-Admin") == "true"
    if is_admin:
        db.delete(user_id)          # no server-side role check
        return {"deleted": user_id}
    return {"error": "forbidden"}

# Also: object reference with no ownership check (IDOR).
def get_invoice(request, invoice_id):
    return db.query(f"SELECT * FROM invoices WHERE id = {invoice_id}")
