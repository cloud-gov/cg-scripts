#!/usr/bin/env python3

"""Report Cloud Foundry organization memory usage by aggregating quota consumption across spaces, apps, and processes, with text and CSV outputs."""

import argparse
import csv
import json
import re
import subprocess
import sys

def parse_args():
  parser = argparse.ArgumentParser(description="Report Cloud Foundry org space usage.")
  parser.add_argument("org_name", help="Cloud Foundry organization name")
  parser.add_argument(
    "--format",
    choices=["text", "csv"],
    default="text",
    help="Output format (default: text)",
  )
  return parser.parse_args()

def cf_api(path, method="GET", data=None):
  cmd = ["cf", "curl", path, "-X", method]
  if data:
    cmd += ["-d", json.dumps(data)]
  result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  if result.returncode != 0:
    print(f"Error calling cf curl {path}: {result.stderr}", file=sys.stderr)
    sys.exit(1)
  return json.loads(result.stdout)

def get_org_guid(org_name):
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
  resp = cf_api(f"/v3/spaces?organization_guids={org_guid}&per_page=100")
  return resp.get("resources", [])

def get_apps(space_guid):
  resp = cf_api(f"/v3/apps?space_guids={space_guid}&per_page=100")
  return resp.get("resources", [])

def chunked(seq, size):
  for idx in range(0, len(seq), size):
    yield seq[idx:idx + size]

def get_processes_for_apps(app_guids):
  processes = {}
  if not app_guids:
    return processes
  for chunk in chunked(app_guids, 50):
    page = 1
    while True:
      guids_param = ",".join(chunk)
      resp = cf_api(f"/v3/processes?app_guids={guids_param}&per_page=100&page={page}")
      for proc in resp.get("resources", []):
        app_relationship = proc.get("relationships", {}).get("app", {})
        app_guid = app_relationship.get("data", {}).get("guid")
        if not app_guid:
          continue
        running_instances = get_running_instances(proc["guid"])
        proc_with_runtime = dict(proc)
        proc_with_runtime["_running_instances"] = running_instances
        processes.setdefault(app_guid, []).append(proc_with_runtime)
      if not resp.get("pagination", {}).get("next"):
        break
      page += 1
  return processes

def get_running_instances(process_guid):
  resp = cf_api(f"/v3/processes/{process_guid}/stats")
  running = 0
  for inst in resp.get("resources", []):
    if inst.get("state") == "RUNNING":
      running += 1
  return running

def summarize_app_usage(app_guid, processes):
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
  return f"{(used/total*100):.1f}%" if total else "N/A"

def main():
  args = parse_args()
  org_name = args.org_name
  org_guid, quota_guid = get_org_guid(org_name)
  quota_mb = get_quota_memory(quota_guid)
  spaces = get_spaces(org_guid)

  org_total = 0
  space_usages = []

  for space in spaces:
    space_guid = space["guid"]
    apps = get_apps(space_guid)
    app_guids = [app["guid"] for app in apps]
    processes = get_processes_for_apps(app_guids)
    space_total = 0
    app_usages = []
    for app in apps:
      usage, mem_mb, running_instances, desired_instances, process_details = summarize_app_usage(app["guid"], processes)
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