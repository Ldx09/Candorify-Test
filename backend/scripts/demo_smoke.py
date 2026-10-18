"""Runs the full midterm demo path against a running server and reports PASS/FAIL for each step:
health -> sign up -> log in -> load bill -> checks -> translate -> dispute letter -> request letter
-> delete bill -> delete account.

It creates a throwaway account and deletes it at the end, so it is safe to run against the live app.

Run from the backend folder:
    python -m scripts.demo_smoke                                  (local, http://127.0.0.1:8000)
    python -m scripts.demo_smoke https://your-app.onrender.com    (deployed)
"""
import sys
import time
import uuid

import httpx

EXPECTED_BILL_001 = {("line_math", 2), ("duplicate_line", 3)}  # known errors in sample BILL-001


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
    c = httpx.Client(base_url=base, timeout=90, follow_redirects=False)
    results: list[tuple[str, bool, str]] = []

    def step(name: str, ok: bool, info: str = "") -> bool:
        results.append((name, ok, info))
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({info})" if info else ""))
        return ok

    t0 = time.time()
    try:
        r = c.get("/health")  # a sleeping free-tier host can take ~1 minute to wake up here
        if not step("health check", r.status_code == 200 and r.json() == {"status": "ok"}, f"{time.time() - t0:.1f}s"):
            return 1

        email, pw = f"demo-{uuid.uuid4().hex[:10]}@example.com", "demo-pass-123"
        r = c.post("/api/auth/signup", json={"email": email, "password": pw, "full_name": "Demo User"})
        if not step("sign up", r.status_code == 201, str(r.status_code)):
            return 1
        r = c.post("/api/auth/login", json={"email": email, "password": pw})
        if not step("log in", r.status_code == 200 and "access_token" in r.json(), str(r.status_code)):
            return 1
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = c.post("/api/bills/sample", json={"sample_id": "BILL-001"}, headers=h)
        if not step("load sample bill BILL-001", r.status_code == 201 and len(r.json()["lines"]) == 5, str(r.status_code)):
            return 1
        bill_id = r.json()["id"]
        step("open bill", c.get(f"/api/bills/{bill_id}", headers=h).status_code == 200)
        step("bill appears in my bills", any(b["id"] == bill_id for b in c.get("/api/bills", headers=h).json()))

        r = c.post(f"/api/bills/{bill_id}/check", headers=h)
        found = {(f["rule"], f["line_no"]) for f in r.json().get("flags", [])} if r.status_code == 200 else set()
        step("checks find the 2 planted errors", found == EXPECTED_BILL_001, str(sorted(found)))

        t1 = time.time()
        r = c.get(f"/api/bills/{bill_id}/translate", headers=h)
        ok = r.status_code == 200 and all(ln["code_info"]["plain_english"] for ln in r.json()["lines"])
        sources = sorted({ln["code_info"]["source"] for ln in r.json()["lines"]}) if r.status_code == 200 else []
        step("translate every line to plain English", ok, f"sources={sources}, {time.time() - t1:.1f}s")
        r = c.get("/api/translate", params={"code": "J2405"}, headers=h)
        step("translate single code J2405", r.status_code == 200 and r.json()["plain_english"], r.json().get("source", ""))

        r = c.post("/api/letters", headers=h, json={"bill_id": bill_id, "letter_type": "dispute", "patient_name": "Demo User"})
        step("dispute letter lists exactly the flagged lines", r.status_code == 200 and r.json()["flagged_lines"] == [2, 3],
             str(r.json().get("flagged_lines")))
        r = c.post("/api/letters", headers=h, json={"bill_id": bill_id, "letter_type": "request"})
        step("request letter", r.status_code == 200 and "itemized bill" in r.json()["text"])

        r = c.post("/api/bills/sample", json={"defect": "mixed"}, headers=h)
        gen_ok = r.status_code == 201
        if gen_ok:
            rules = {f["rule"] for f in c.post(f"/api/bills/{r.json()['id']}/check", headers=h).json()["flags"]}
            gen_ok = rules == {"duplicate_line", "line_math"}
        step("generate a new synthetic bill + check it", gen_ok)

        step("delete one bill", c.delete(f"/api/bills/{bill_id}", headers=h).status_code == 204
             and c.get(f"/api/bills/{bill_id}", headers=h).status_code == 404)

        r = c.get("/health")
        step("security headers present", r.headers.get("x-content-type-options") == "nosniff")
        if base.startswith("https://"):
            insecure = httpx.get(base.replace("https://", "http://", 1) + "/api/bills", follow_redirects=False, timeout=60)
            step("plain HTTP is redirected to HTTPS", insecure.status_code in (301, 307, 308), str(insecure.status_code))

        step("delete account (one tap)", c.delete("/api/me", headers=h).status_code == 204)
        step("deleted account can't log in", c.post("/api/auth/login", json={"email": email, "password": pw}).status_code == 401)
    except httpx.HTTPError as exc:
        step("server reachable", False, f"{exc.__class__.__name__}: {exc}")

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} steps passed in {time.time() - t0:.1f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())