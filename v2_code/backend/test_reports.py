import requests, json, os, sys

url = "http://127.0.0.1:8000/api/analyze"
path = r"C:\Users\by4412\Desktop\NutriScope AI\test_reports\lft.pdf"

if not os.path.exists(path):
    print("PDF not found at:", path)
    sys.exit(1)

# Optional: quick health check
try:
    h = requests.get("http://127.0.0.1:8000/health", timeout=3)
    print("HEALTH:", h.status_code, h.text)
except Exception as e:
    print("Health check failed:", e)
    sys.exit(1)

with open(path, "rb") as f:
    files = {"file": ("Calcium.pdf", f, "application/pdf")}
    data = {"report_name": "Medical Test", "age": 23, "sex": "male"}
    try:
        resp = requests.post(url, data=data, files=files, timeout=60)
        print(resp.status_code)
        print(json.dumps(resp.json(), indent=2))
    except requests.exceptions.Timeout:
        print("Request timed out (try a larger timeout if needed).")
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
