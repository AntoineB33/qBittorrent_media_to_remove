import requests
from datetime import datetime
import sys

# --- IMPORT CONFIG ---
try:
    from config import QBIT_URL, USERNAME, PASSWORD
except ImportError:
    print("❌ Could not import config.py. Make sure QBIT_URL, USERNAME, and PASSWORD are defined there.")
    sys.exit(1)

# --- READ EXCLUSION LIST ---
try:
    with open("exclusions.txt", "r", encoding="utf-8") as f:
        EXCLUDE_LIST = [line.strip().lower() for line in f if line.strip()]
except FileNotFoundError:
    print("⚠️ No exclusions.txt file found. No torrents will be excluded.")
    EXCLUDE_LIST = []

# --- CONNECT TO QBITTORRENT ---
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
    # Skip excluded shows
    if t["name"].lower() in EXCLUDE_LIST:
        continue

    size_gb = t["size"] / (1024**3)
    completion = datetime.fromtimestamp(t["completion_on"]) if t["completion_on"] > 0 else None
    uploaded_gb = t["uploaded"] / (1024**3)
    days_since_completion = (now - completion).days if completion else 0

    # --- SCORE FORMULA ---
    score = (size_gb * 2) + (days_since_completion * 0.5) - (uploaded_gb * 3)

    ranked.append({
        "hash": t["hash"],
        "name": t["name"],
        "size_gb": round(size_gb, 2),
        "days_since_completion": days_since_completion,
        "uploaded_gb": round(uploaded_gb, 2),
        "score": round(score, 2),
    })

# Sort descending by score
ranked.sort(key=lambda x: x["score"], reverse=True)

# Display results
print(f"{'INDEX':>5} | {'SCORE':>6} | {'SIZE(GB)':>7} | {'DAYS':>4} | {'UPLOADED(GB)':>11} | NAME")
print("-" * 110)
for idx, r in enumerate(ranked, start=1):
    print(f"{idx:>5} | {r['score']:>6} | {r['size_gb']:>7} | {r['days_since_completion']:>4} | {r['uploaded_gb']:>11} | {r['name']}")

if not ranked:
    print("\n✅ No torrents matched the removal criteria.")
    sys.exit(0)

# Ask how many to remove
try:
    to_remove_count = int(input("\nHow many torrents from the top do you want to remove? (Enter 0 to skip): "))
except ValueError:
    print("Invalid number. Exiting without removing anything.")
    sys.exit(1)

if to_remove_count > 0:
    to_remove = ranked[:to_remove_count]

    print("\nThe following torrents will be removed:")
    for t in to_remove:
        print(f"- {t['name']} (score: {t['score']})")

    confirm = input("\nType 'yes' to confirm deletion (this will also delete files from disk): ").strip().lower()
    if confirm == "yes":
        hashes = "|".join([t["hash"] for t in to_remove])
        delete_resp = session.post(
            f"{QBIT_URL}/api/v2/torrents/delete",
            data={"hashes": hashes, "deleteFiles": "true"}
        )
        if delete_resp.status_code == 200:
            print(f"\n✅ Successfully removed {to_remove_count} torrents and deleted their files.")
        else:
            print(f"\n⚠️ Failed to remove torrents: {delete_resp.text}")
    else:
        print("\n❌ Deletion cancelled. No torrents were removed.")
else:
    print("\nNo torrents removed.")
