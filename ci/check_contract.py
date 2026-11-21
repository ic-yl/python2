"""Verify invariants of the published Workbench API contract."""
import hashlib
import json
import os
import sys
from pathlib import Path


CONTRACT_SHA256 = "363102e200ecc60126993251d46f13560b72987186d7741a32aa60a57cd8b3e4"
METHODS = {"get", "post", "patch", "delete"}
ROUTES = {
    ("/api/auth/bootstrap", "get"): "200",
    ("/api/auth/login", "post"): "200",
    ("/api/auth/logout", "post"): "204",
    ("/api/me", "get"): "200",
    ("/api/tasks", "get"): "200",
    ("/api/tasks", "post"): "201",
    ("/api/tasks/{taskId}", "get"): "200",
    ("/api/tasks/{taskId}", "patch"): "200",
    ("/api/tasks/{taskId}", "delete"): "204",
    ("/api/exports", "post"): "202",
    ("/api/exports/{jobId}", "get"): "200",
    ("/api/admin/queue", "get"): "200",
}
ANONYMOUS = {"/api/auth/bootstrap", "/api/auth/login"}


def verify(contract):
    operations = {
        (path, method): operation
        for path, entry in contract["paths"].items()
        for method, operation in entry.items()
        if method in METHODS
    }
    if set(operations) != ROUTES.keys():
        raise ValueError("unexpected route inventory")
    cookie = contract["components"]["securitySchemes"]["courseSession"]
    if (cookie["type"], cookie["in"], cookie["name"]) != ("apiKey", "cookie", "__Host-course_session"):
        raise ValueError("session cookie contract changed")
    for route, operation in operations.items():
        path, method = route
        responses = operation["responses"]
        if ROUTES[route] not in responses:
            raise ValueError(f"{route} lacks its frozen success response")
        if path not in ANONYMOUS and (operation.get("security") != [{"courseSession": []}] or "401" not in responses):
            raise ValueError(f"{route} lacks its documented session boundary")
        if method != "get":
            headers = {p["name"] for p in operation.get("parameters", []) if p.get("in") == "header"}
            if not {"Origin", "X-CSRF-Token"}.issubset(headers):
                raise ValueError(f"{route} lacks its documented request headers")
    return len(operations)


def main():
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CONTRACT_SHA256:
        raise ValueError("contract differs from the reviewed course release")
    operation_count = verify(json.loads(raw))
    report = {
        "scope": "Published Workbench OpenAPI contract verification",
        "sha256": digest,
        "operations": operation_count,
        "commit": os.environ.get("GITHUB_SHA"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "application_deployed": False,
    }
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
