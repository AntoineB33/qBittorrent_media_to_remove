import requests
from datetime import datetime

# --- CONFIG ---
QBIT_URL = "http://localhost:8080"
USERNAME = "admin"
PASSWORD = "Cg644`#0UUwL"

# Connect to qBittorrent Web API
session = requests.Session()
login = session.post(f"{QBIT_URL}/api/v2/auth/login", data={"username": USERNAME, "password": PASSWORD})

if login.text != "Ok.":
    raise RuntimeError("Failed to authenticate with qBittorrent API")

# Get torrent list
resp = session.get(f"{QBIT_URL}/api/v2/torrents/info")
torrents = resp.json()

now = datetime.now()
ranked = []

for t in torrents:
    size_gb = t["size"] / (1024**3)
    completion = datetime.fromtimestamp(t["completion_on"]) if t["completion_on"] > 0 else None
    uploaded_gb = t["uploaded"] / (1024**3)
    days_since_completion = (now - completion).days if completion else 0

    # --- SCORE FORMULA ---
    # Higher size -> higher score
    # Older torrents -> higher score
    # More uploaded -> lower score (reward good seeders)
    score = (size_gb * 2) + (days_since_completion * 0.5) - (uploaded_gb * 3)

    ranked.append({
        "name": t["name"],
        "size_gb": round(size_gb, 2),
        "days_since_completion": days_since_completion,
        "uploaded_gb": round(uploaded_gb, 2),
        "score": round(score, 2),
    })

# Sort descending by score (highest = remove first)
ranked.sort(key=lambda x: x["score"], reverse=True)

# Display results
print(f"{'SCORE':>6} | {'SIZE(GB)':>7} | {'DAYS':>4} | {'UPLOADED(GB)':>11} | NAME")
print("-"*100)
for r in ranked:
    print(f"{r['score']:>6} | {r['size_gb']:>7} | {r['days_since_completion']:>4} | {r['uploaded_gb']:>11} | {r['name']}")
