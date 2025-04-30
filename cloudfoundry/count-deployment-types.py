#!/usr/bin/env python3
"""
Count Cloud Foundry deployment types across all apps.

Result: one line per “method”, tab-separated:

    ruby_buildpack	       73
    java_buildpack	       41
    nodejs_buildpack	   29
    python_buildpack	   18
    staticfile_buildpack	12
    docker		           7
    unknown		           2

- Buildpack apps are grouped by the name of the *detected* buildpack in their
  current droplet.
- Docker apps stay under a single “docker” bucket.
- Any app with no current droplet is counted as “unknown”.

Prereqs
  CF_API   – e.g. https://api.sys.example.com
  Logged-in `cf` CLI **or** CF_TOKEN env var
"""

import os, sys, requests, subprocess, concurrent.futures as cf

API = os.getenv("CF_API")
if not API:
    sys.exit("export CF_API=https://api.sys.yourcf.com")

def oauth() -> str:
    tok = os.getenv("CF_TOKEN")
    if tok:
        return tok.strip()
    try:
        return subprocess.check_output(["cf", "oauth-token"], text=True).strip()
    except Exception:
        sys.exit("Need CF_TOKEN or a logged-in `cf` CLI")

HEADERS = {"Authorization": oauth()}

# --- helpers ---------------------------------------------------------------
def get_json(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def droplet_buildpack(droplet_guid: str) -> str:
    droplet = get_json(f"{API}/v3/droplets/{droplet_guid}")
    bps = droplet.get("buildpacks") or []
    return bps[0]["name"] if bps else "unknown"

# --- collect all apps ------------------------------------------------------
apps, url = [], f"{API}/v3/apps?per_page=5000"
while url:
    page = get_json(url)
    apps.extend(page["resources"])
    nxt = page["pagination"]["next"]
    url = nxt and nxt["href"]

# --- tally -----------------------------------------------------------------
counts = {}
docker_key = "docker"

# fetch buildpack names in parallel for speed
with cf.ThreadPoolExecutor(max_workers=20) as pool:
    futures = []

    for app in apps:
        typ = app["lifecycle"]["type"]
        if typ == "docker":
            counts[docker_key] = counts.get(docker_key, 0) + 1
        else:  # buildpack
            droplet_rel = app["relationships"]["current_droplet"]["data"]
            guid = droplet_rel and droplet_rel["guid"]
            if not guid:
                counts["unknown"] = counts.get("unknown", 0) + 1
            else:
                futures.append(pool.submit(droplet_buildpack, guid))

    for f in cf.as_completed(futures):
        bp = f.result()
        counts[bp] = counts.get(bp, 0) + 1

# --- output ----------------------------------------------------------------
for method, num in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
    print(f"{method}\t{num}")
