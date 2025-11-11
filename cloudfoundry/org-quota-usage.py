#!/usr/bin/env python3

"""Report Cloud Foundry organization memory usage by aggregating quota consumption across spaces, apps, and processes, with text and CSV outputs."""

import argparse
import csv
import json
import os
import re
import ssl
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

from concurrent.futures import ThreadPoolExecutor

def parse_args():
  """Parse command-line flags to determine which org to report and output format."""
  parser = argparse.ArgumentParser(description="Report Cloud Foundry org space usage.")
  parser.add_argument("org_name", help="Cloud Foundry organization name")
  parser.add_argument(
    "--format",
    choices=["text", "csv"],
    default="text",
    help="Output format (default: text)",
  )
  return parser.parse_args()

class CFClient:
  """Thin client that reuses a CF access token across requests for speed."""

  def __init__(self):
    self._config = self._load_config()
    target = self._config.get("Target")
    if not target:
      print("Cloud Foundry API target not configured. Run 'cf target'.", file=sys.stderr)
      sys.exit(1)
    self._base_url = target.rstrip("/") + "/"
    self._skip_ssl_validation = bool(self._config.get("SSLDisabled"))
    self._token_lock = threading.Lock()
    self._token = self._fetch_token()

  def _load_config(self):
    """Load CF CLI configuration so we can discover the target API endpoint."""
    config_path = os.path.expanduser("~/.cf/config.json")
    try:
      with open(config_path, "r", encoding="utf-8") as config_file:
        return json.load(config_file)
    except FileNotFoundError:
      print("CF CLI config not found. Run 'cf login' before using this script.", file=sys.stderr)
      sys.exit(1)
    except json.JSONDecodeError as exc:
      print(f"Unable to parse CF CLI config: {exc}", file=sys.stderr)
      sys.exit(1)

  def _fetch_token(self):
    """Ask the CF CLI for a fresh OAuth token."""
    result = subprocess.run(["cf", "oauth-token"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
      print(f"Error retrieving CF access token: {result.stderr.strip()}", file=sys.stderr)
      sys.exit(1)
    token = result.stdout.strip()
    return token if token.lower().startswith("bearer ") else f"bearer {token}"

  def _current_token(self):
    """Return the cached token in a threadsafe way."""
    with self._token_lock:
      return self._token

  def _refresh_token(self):
    """Refresh and cache a new token when the current one expires."""
    with self._token_lock:
      self._token = self._fetch_token()
      return self._token

  def api(self, path, method="GET", data=None, retry=True):
    """Perform an authenticated CF API call, retrying once on auth failure."""
    url = urllib.parse.urljoin(self._base_url, path.lstrip("/"))
    headers = {
      "Authorization": self._current_token(),
      "Accept": "application/json",
    }
    body = None
    if data is not None:
      headers["Content-Type"] = "application/json"
      body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    context = None
    if self._skip_ssl_validation:
      context = ssl.create_default_context()
      context.check_hostname = False
      context.verify_mode = ssl.CERT_NONE
    try:
      with urllib.request.urlopen(request, context=context) as response:
        payload = response.read()
    except urllib.error.HTTPError as exc:
      if exc.code == 401 and retry:
        self._refresh_token()
        return self.api(path, method=method, data=data, retry=False)
      detail = exc.read().decode("utf-8", errors="replace") if exc.fp else exc.reason
      print(f"Error calling CF API {path}: {detail}", file=sys.stderr)
      sys.exit(1)
    except urllib.error.URLError as exc:
      print(f"Error connecting to CF API: {exc.reason}", file=sys.stderr)
      sys.exit(1)
    if not payload:
      return {}
    return json.loads(payload)


_CF_CLIENT = None


def cf_api(path, method="GET", data=None):
  """Route requests through a singleton CF client for reuse."""
  global _CF_CLIENT
  if _CF_CLIENT is None:
    _CF_CLIENT = CFClient()
  return _CF_CLIENT.api(path, method=method, data=data)


def _build_query(params):
  """Turn a params dict into a URL query string."""
  return "&".join(
    f"{key}={urllib.parse.quote_plus(str(value), safe=',')}" for key, value in params.items()
  )


def fetch_paginated(path, params=None, per_page=200):
  """Yield every resource across paginated CF API responses."""
  base_params = dict(params or {})
  base_params.setdefault("per_page", per_page)
  page = 1
  while True:
    params_with_page = dict(base_params, page=page)
    query = _build_query(params_with_page) if params_with_page else ""
    full_path = f"{path}?{query}" if query else path
    resp = cf_api(full_path)
    for resource in resp.get("resources", []):
      yield resource
    if not resp.get("pagination", {}).get("next"):
      break
    page += 1

def get_org_guid(org_name):
  """Look up the org GUID and its quota GUID from the CF API."""
  resp = cf_api(f"/v3/organizations?names={org_name}")
  orgs = resp.get("resources", [])
  if not orgs:
    print(f"Organization '{org_name}' not found.", file=sys.stderr)
    sys.exit(1)
  org = orgs[0]
  relationships = org.get("relationships", {})
  quota_data = (
    relationships.get("quota")
    or relationships.get("organization_quota")
    or {}
  ).get("data", {})
  quota_guid = quota_data.get("guid")
  if not quota_guid:
    print(f"Quota GUID not found for organization '{org_name}'.", file=sys.stderr)
    sys.exit(1)
  return org["guid"], quota_guid

def get_quota_memory(quota_guid):
  """Determine the quota's total memory limit in megabytes."""
  resp = cf_api(f"/v3/organization_quotas/{quota_guid}")
  mem_mb = resp.get("apps", {}).get("total_memory_in_mb")
  if mem_mb is None:
    quota_name = resp.get("name")
    quota_cli = subprocess.run(["cf", "quota", quota_name], stdout=subprocess.PIPE, text=True)
    match = re.search(r"total memory:\s+(\d+)([MG])", quota_cli.stdout)
    if match:
      val, unit = match.groups()
      mem_mb = int(val) * (1024 if unit == "G" else 1)
  return mem_mb

def get_spaces(org_guid):
  """Return every space that belongs to the org."""
  return list(fetch_paginated("/v3/spaces", {"organization_guids": org_guid}))


def get_apps_by_space(org_guid):
  """Collect apps grouped by their space GUID for the entire org."""
  apps_by_space = {}
  for app in fetch_paginated("/v3/apps", {"organization_guids": org_guid}):
    space_guid = (
      app.get("relationships", {})
      .get("space", {})
      .get("data", {})
      .get("guid")
    )
    if not space_guid:
      continue
    apps_by_space.setdefault(space_guid, []).append(app)
  return apps_by_space

def chunked(seq, size):
  """Yield fixed-size slices from a sequence."""
  for idx in range(0, len(seq), size):
    yield seq[idx:idx + size]

def get_processes_for_apps(app_guids):
  """Load processes for the given app GUIDs and annotate them with runtime info."""
  processes = {}
  if not app_guids:
    return processes
  collected = []
  for chunk in chunked(app_guids, 50):
    params = {"app_guids": ",".join(chunk)}
    for proc in fetch_paginated("/v3/processes", params):
      app_relationship = proc.get("relationships", {}).get("app", {})
      app_guid = app_relationship.get("data", {}).get("guid")
      if not app_guid:
        continue
      processes.setdefault(app_guid, []).append(proc)
      collected.append(proc)
  stats_map = get_running_instances_bulk([proc.get("guid") for proc in collected if proc.get("guid")])
  for proc in collected:
    proc["_running_instances"] = stats_map.get(proc.get("guid"), 0)
  return processes

def get_running_instances_bulk(process_guids):
  """Fetch running instance counts for many processes concurrently."""
  if not process_guids:
    return {}
  try:
    configured = int(os.environ.get("ORG_QUOTA_USAGE_MAX_WORKERS", "8"))
  except ValueError:
    configured = 8
  max_workers = max(1, min(configured, len(process_guids)))

  def fetch(guid):
    resp = cf_api(f"/v3/processes/{guid}/stats")
    running = 0
    for inst in resp.get("resources", []):
      if inst.get("state") == "RUNNING":
        running += 1
    return guid, running

  results = {}
  with ThreadPoolExecutor(max_workers=max_workers) as executor:
    for guid, running in executor.map(fetch, process_guids):
      results[guid] = running
  return results

def summarize_app_usage(app_guid, processes):
  """Aggregate memory usage metrics for a single app."""
  app_processes = processes.get(app_guid, [])
  if not app_processes:
    return 0, 0, 0, 0, []
  total_usage = 0
  process_details = []
  for proc in app_processes:
    mem_mb = proc.get("memory_in_mb", 0)
    desired_instances = proc.get("instances", 0)
    running_instances = proc.get("_running_instances", 0)
    total_usage += mem_mb * running_instances
    process_details.append((proc.get("type", "unknown"), mem_mb, running_instances, desired_instances))
  primary = next((proc for proc in app_processes if proc.get("type") == "web"), app_processes[0])
  return (
    total_usage,
    primary.get("memory_in_mb", 0),
    primary.get("_running_instances", 0),
    primary.get("instances", 0),
    process_details,
  )

def percent(used, total):
  """Convert a used/total ratio into a percentage string."""
  return f"{(used/total*100):.1f}%" if total else "N/A"

def main():
  """Orchestrate the data fetch, aggregation, and output formatting."""
  args = parse_args()
  org_name = args.org_name
  org_guid, quota_guid = get_org_guid(org_name)
  quota_mb = get_quota_memory(quota_guid)
  spaces = get_spaces(org_guid)
  apps_by_space = get_apps_by_space(org_guid)
  all_app_guids = [app["guid"] for apps in apps_by_space.values() for app in apps]
  processes_by_app = get_processes_for_apps(all_app_guids)

  org_total = 0
  space_usages = []

  for space in spaces:
    space_guid = space["guid"]
    apps = apps_by_space.get(space_guid, [])
    space_total = 0
    app_usages = []
    for app in apps:
      usage, mem_mb, running_instances, desired_instances, process_details = summarize_app_usage(app["guid"], processes_by_app)
      space_total += usage
      app_usages.append((app["name"], usage, mem_mb, running_instances, desired_instances, process_details))
    org_total += space_total
    space_usages.append((space["name"], space_total, app_usages))

  space_labels = [f"  Space '{space_name}':" for space_name, _, _ in space_usages]
  max_space_label_len = max((len(label) for label in space_labels), default=0)
  app_labels = []
  process_labels = []
  for space_name, _, app_usages in space_usages:
    for app_name, _, _, _, _, process_details in app_usages:
      app_labels.append(f"      App '{app_name}':")
      if len(process_details) > 1:
        for proc_type, _, _, _ in process_details:
          process_labels.append(f"          Process '{proc_type}':")
  max_app_label_len = max((len(label) for label in app_labels), default=0)
  max_process_label_len = max((len(label) for label in process_labels), default=0)
  usage_mb_values = []
  detail_mem_values = []
  for _, space_total, app_usages in space_usages:
    usage_mb_values.append(space_total)
    for _, usage, mem_mb, _, _, process_details in app_usages:
      usage_mb_values.append(usage)
      if len(process_details) > 1:
        for _, proc_mem, _, _ in process_details:
          detail_mem_values.append(proc_mem)
      else:
        detail_mem_values.append(mem_mb)
  max_usage_mb_width = max((len(str(value)) for value in usage_mb_values), default=1)
  max_detail_mem_width = max((len(str(value)) for value in detail_mem_values), default=1)

  def format_usage_string(mb_value):
    return f"{mb_value:>{max_usage_mb_width}} MB ({percent(mb_value, quota_mb)})"

  usage_strings = []
  for _, space_total, app_usages in space_usages:
    usage_strings.append(format_usage_string(space_total))
    for _, usage, *_ in app_usages:
      usage_strings.append(format_usage_string(usage))
  max_usage_len = max((len(s) for s in usage_strings), default=0)
  value_column = max(max_space_label_len, max_app_label_len, max_process_label_len, 0) + 1

  if args.format == "csv":
    writer = csv.writer(sys.stdout)
    writer.writerow([
      "org_name",
      "org_quota_mb",
      "org_used_mb",
      "space_name",
      "space_used_mb",
      "app_name",
      "process_type",
      "process_usage_mb",
      "process_usage_percent_quota",
      "process_memory_mb",
      "process_running_instances",
      "process_desired_instances",
    ])
    for space_name, space_total, app_usages in space_usages:
      for (
        app_name,
        usage,
        mem_mb,
        running_instances,
        desired_instances,
        process_details,
        ) in app_usages:
        if not process_details:
          writer.writerow([
            org_name,
            quota_mb,
            org_total,
            space_name,
            space_total,
            app_name,
            "",
            0,
            percent(0, quota_mb),
            0,
            0,
            desired_instances,
          ])
          continue
        for proc_type, proc_mem, proc_running, proc_desired in process_details:
          process_usage = proc_mem * proc_running
          writer.writerow([
            org_name,
            quota_mb,
            org_total,
            space_name,
            space_total,
            app_name,
            proc_type,
            process_usage,
            percent(process_usage, quota_mb),
            proc_mem,
            proc_running,
            proc_desired,
          ])
    return

  print(f"Org '{org_name}'")
  print(f"  Quota: {quota_mb} MB")
  print(f"  Used: {org_total} MB ({percent(org_total, quota_mb)})")
  for space_name, space_total, app_usages in space_usages:
    space_label = f"  Space '{space_name}':"
    space_info = format_usage_string(space_total)
    print(f"{space_label.ljust(value_column)} {space_info.ljust(max_usage_len)}")
    for app_name, usage, mem_mb, running_instances, desired_instances, process_details in app_usages:
      app_label = f"      App '{app_name}':"
      app_usage = format_usage_string(usage)
      desired_display = f"{desired_instances}" if desired_instances is not None else "?"
      app_usage_padded = app_usage.ljust(max_usage_len)
      if len(process_details) > 1:
        print(f"{app_label.ljust(value_column)} {app_usage_padded}")
        for proc_type, proc_mem, proc_running, proc_desired in process_details:
          proc_label = f"          Process '{proc_type}':"
          proc_desired_display = f"{proc_desired}" if proc_desired is not None else "?"
          process_detail = f"[{proc_mem:>{max_detail_mem_width}} MB x {proc_running}/{proc_desired_display} running]"
          proc_info = f"{' ' * max_usage_len} {process_detail}"
          print(f"{proc_label.ljust(value_column)} {proc_info}")
      else:
        process_detail = f"[{mem_mb:>{max_detail_mem_width}} MB x {running_instances}/{desired_display} running]"
        detail_suffix = f" {process_detail}"
        print(f"{app_label.ljust(value_column)} {app_usage_padded}{detail_suffix}")

if __name__ == "__main__":
  main()