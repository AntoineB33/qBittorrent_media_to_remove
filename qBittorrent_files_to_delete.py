import requests
from datetime import datetime

# --- CONFIG ---
QBIT_URL = "http://localhost:8080"
USERNAME = "admin"
PASSWORD = "Cg644`#0UUwL"

# List of shows you don't want to include in the removal list (case-insensitive)
EXCLUDE_LIST = [
    "Sinners.2025.2160p.WEB-DL.DV.HDR10+.DDP5.1.Atmos.H265.MP4-BEN.THE.MEN",
    "www.UIndex.org    -    DAN.DA.DAN.S02E01.PROPER.1080p.WEB.H264-KAWAII",
    "www.UIndex.org    -    DAN DA DAN S02E02 The Evil Eye 1080p CR WEB-DL DUAL DDP2 0 H 264-Kitsune",
    "The.Bear.S01.2160p.HULU.WEB-DL.DDP5.1.x265-KOGi[rartv]",
    "No Hard Feelings (2023) [2160p] [4K] [WEB] [5.1] [YTS.MX]",
    "www.UIndex.org    -    Ne Zha 2 (2025) 2160p 4K WEB 5.1-WORLD"
    # Add more show names or keywords here
]

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
    if any(keyword.lower() in t["name"].lower() for keyword in EXCLUDE_LIST):
        continue

    size_gb = t["size"] / (1024**3)
    completion = datetime.fromtimestamp(t["completion_on"]) if t["completion_on"] > 0 else None
    uploaded_gb = t["uploaded"] / (1024**3)
    days_since_completion = (now - completion).days if completion else 0

    score = (size_gb * 2) + (days_since_completion * 0.5) - (uploaded_gb * 3)

    ranked.append({
        "hash": t["hash"],  # Needed for deletion
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
    exit()

# Ask how many to remove
try:
    to_remove_count = int(input("\nHow many torrents from the top do you want to remove? (Enter 0 to skip): "))
except ValueError:
    print("Invalid number. Exiting without removing anything.")
    exit()

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
