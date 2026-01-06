from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar


def _extract_addresses(html: str) -> dict[str, str]:
    pattern = re.compile(r"<strong>([^<]+)</strong>:\s*<span>([^<]+)</span>")
    return {chain.strip(): address.strip() for chain, address in pattern.findall(html)}


def main() -> int:
    start_url = os.environ.get("AGENTTRACE_START_URL")
    email = os.environ.get("AGENTTRACE_EMAIL")
    password = os.environ.get("AGENTTRACE_PASSWORD")
    if not start_url or not email or not password:
        print(json.dumps({"error": {"message": "missing AGENTTRACE_START_URL or creds"}}))
        return 1

    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    login_url = start_url
    login_data = urllib.parse.urlencode({"email": email, "password": password}).encode(
        "utf-8"
    )
    login_req = urllib.request.Request(login_url, data=login_data, method="POST")
    with opener.open(login_req, timeout=5) as resp:
        login_body = resp.read().decode("utf-8", errors="replace")
        login_url_after = resp.geturl()

    if "/login" in login_url_after and "Invalid credentials" in login_body:
        print(json.dumps({"error": {"message": "login failed: invalid credentials"}}))
        return 1

    deposit_url = urllib.parse.urljoin(start_url, "/deposit")
    with opener.open(deposit_url, timeout=5) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        final_url = resp.geturl()

    if "/login" in final_url or "<h1>Login</h1>" in html:
        print(json.dumps({"error": {"message": "login failed: not authenticated"}}))
        return 1

    artifacts = _extract_addresses(html)
    if not artifacts:
        snippet = " ".join(html.split())[:200]
        print(
            json.dumps(
                {
                    "error": {
                        "message": f"no addresses found; page snippet: {snippet}"
                    }
                }
            )
        )
        return 1

    print(json.dumps({"artifacts": artifacts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
