"""Golden evaluation set (Week 4, Weekend).

10 snippets with a known vulnerability, the OWASP category it should be detected
as, and acceptable fix patterns. Two ways to use it:

- Structure test (offline, runs in pytest):  validates the dataset is well-formed.
- Live evaluation (hits Azure):  RUN_LIVE_AGENT=1 python tests/golden_set.py
  Prints a detection/fix accuracy table for docs/GOLDEN_SET.md.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

# (id, language, code, expected_rule_id, acceptable_fix_substrings)
GOLDEN = [
    ("sql_injection", "python",
     'q = "SELECT * FROM users WHERE id = " + user_id\ncursor.execute(q)',
     "OWASP-A03", ["%s", "?", "execute(", "parameter"]),
    ("command_injection", "python",
     'import os\nos.system("ping " + host)',
     "OWASP-A03", ["subprocess.run", "shlex", "[", "shell=False"]),
    ("hardcoded_password", "python",
     'password = "admin123"\nif user_input == password:\n    grant()',
     "OWASP-A02", ["getenv", "environ", "secret", "vault"]),
    ("weak_hash_md5", "python",
     'import hashlib\nh = hashlib.md5(pw.encode()).hexdigest()',
     "OWASP-A02", ["bcrypt", "argon2", "scrypt", "sha256", "pbkdf2"]),
    ("eval_injection", "python",
     'result = eval(user_supplied_expression)',
     "OWASP-A04", ["ast.literal_eval", "json.loads", "remove eval", "without eval"]),
    ("unsafe_yaml", "python",
     'import yaml\ncfg = yaml.load(open("c.yml"))',
     "OWASP-A04", ["safe_load", "Loader=yaml.SafeLoader"]),
    ("debug_enabled", "python",
     'app.run(debug=True, host="0.0.0.0")',
     "OWASP-A05", ["debug=False", "debug = False"]),
    ("tls_verify_disabled", "python",
     'import requests\nrequests.get(url, verify=False)',
     "OWASP-A04", ["verify=True", "remove verify", "certifi"]),
    ("broken_access_control", "python",
     'def view(req):\n    if req.params.get("is_admin"):\n        return secret()',
     "OWASP-A01", ["role", "authoriz", "permission", "rbac", "check"]),
    ("weak_auth_compare", "python",
     "if password == 'admin':\n    login()",
     "OWASP-A07", ["bcrypt", "hash", "compare_digest", "verify"]),
]


def _evaluate():
    from agent import graph

    rows = []
    det_hits = fix_hits = fix_pattern_hits = 0
    for case_id, lang, code, expected, patterns in GOLDEN:
        state = graph.invoke({"code": code, "language": lang})
        findings = state.get("report_findings", [])
        confirmed = {f["rule_id"] for f in findings if f.get("status") == "confirmed"}
        detected = expected in confirmed

        fix_obj = next(
            (f.get("fix") for f in findings
             if f["rule_id"] == expected and f.get("status") == "confirmed" and f.get("fix")),
            None,
        )
        has_fix = bool(fix_obj and fix_obj.get("status") in ("verified", "needs_review"))
        fixed_code = (fix_obj or {}).get("fixed_code", "").lower()
        pattern_ok = bool(fix_obj) and any(p.lower() in fixed_code for p in patterns)

        det_hits += detected
        fix_hits += has_fix
        fix_pattern_hits += pattern_ok
        rows.append((case_id, expected, detected, has_fix,
                     (fix_obj or {}).get("status", "—"),
                     (fix_obj or {}).get("confidence", "—"), pattern_ok))

    n = len(GOLDEN)
    print(f"\n{'case':<24}{'owasp':<12}{'detect':<8}{'fix':<6}{'fixstatus':<14}{'conf':<7}{'pattern'}")
    print("-" * 80)
    for r in rows:
        print(f"{r[0]:<24}{r[1]:<12}{str(r[2]):<8}{str(r[3]):<6}{r[4]:<14}{str(r[5]):<7}{r[6]}")
    print("-" * 80)
    print(f"Detection accuracy:     {det_hits}/{n} ({100*det_hits//n}%)")
    print(f"Fix produced:           {fix_hits}/{n} ({100*fix_hits//n}%)")
    print(f"Fix matches pattern:    {fix_pattern_hits}/{n} ({100*fix_pattern_hits//n}%)")


# ---- offline structure test (runs in normal pytest) ----

def test_golden_set_is_wellformed():
    ids = [c[0] for c in GOLDEN]
    assert len(ids) == 10
    assert len(set(ids)) == 10  # unique
    valid_rules = {f"OWASP-A0{i}" for i in range(1, 8)}
    for case_id, lang, code, expected, patterns in GOLDEN:
        assert expected in valid_rules, case_id
        assert code.strip() and lang and patterns, case_id


if __name__ == "__main__":
    if os.getenv("RUN_LIVE_AGENT") != "1":
        print("Set RUN_LIVE_AGENT=1 to run the live evaluation (calls Azure).")
        sys.exit(0)
    _evaluate()
