
import json
import urllib.request

BASE = "http://127.0.0.1:8000"

endpoints = [
    "headcount",
    "payroll-cost",
    "attendance-rate",
    "revenue",
    "operating-margin",
]

def get_json(path):
    with urllib.request.urlopen(BASE + path) as response:
        return json.loads(response.read().decode("utf-8"))

health = get_json("/health")
assert health["status"] == "ok"
assert health["database_exists"] is True
print("PASS: API health")

catalogue = get_json("/api/v1/metrics")
assert catalogue["count"] == 5
print("PASS: Five metrics listed")

for endpoint in endpoints:
    result = get_json(
        f"/api/v1/metrics/{endpoint}?period=2026-09"
    )
    assert "metric" in result
    assert "definition" in result["metric"]
    assert "lineage" in result
    assert "source_raw_table" in result["lineage"]
    assert "freshness" in result
    print(f"PASS: {endpoint}")

print("RESULT: ALL TASK 19 API CHECKS PASSED")
