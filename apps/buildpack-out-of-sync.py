#!/usr/bin/env python3

from subprocess import run
from shlex import split as cmd
from json import loads, dump
from packaging import version
from pprint import pprint
from argparse import ArgumentParser
import re

class BuildpackSyncer(object):
    """
    Buildpack version syncer.
    """
    def __init__(self, app_name: str, org_name: str, explain: bool):
        self.app_name = app_name
        self.org_name = org_name
        self.target_org_guid = ""
        self.target_app_guid = ""
        self.version_matcher = re.compile("(\d+\.\d+\.\d+)")
        self.explain = explain

    def fetch_app(self) -> bool:
        """

        """
        org_data = self._runner("cf curl /v3/organizations/", "will list out the organizations so we can get the guid.")
        for org in org_data["resources"]:
            if org["name"] == self.org_name:
                self.target_org_guid = org["guid"]
        
        apps_payload = self._runner("cf curl /v3/apps?organization_guids={}".format(self.target_org_guid), "will get all the apps in our target org.")
        for app in apps_payload["resources"]:
            if app["name"] == self.app_name:
                self.target_app_guid = app["guid"]
        return True if self.target_app_guid != "" else False

    def fetch_buildpacks(self) -> bool: self.buildpacks = self._runner("cf curl /v3/buildpacks/", "fetches all of the available buildpacks.")["resources"]

    def fetch_specific_buildpack(self, buildpack_guid: str) -> dict: return self._runner("cf curl /v3/buildpacks/{}".format(buildpack_guid), "will return our specific buildpack needed.")

    def _extract_app_buildpacks(self) -> list:
        res = self._runner("cf curl /v3/apps/{0}/droplets".format(self.target_app_guid), "fetches all the droplets used by the app we're looking for.")["resources"]
        buildpacks = []
        for resource in res:
            if len(resource["buildpacks"]) == 1:
                buildpacks.append(resource["buildpacks"][0])
            else:
                for buildpack in resource["buildpacks"]:
                    buildpacks.append(buildpack)
        return buildpacks

    def _find_platform_buildpack(self, target_buildpack: str) -> dict:
        for platform_buildpack in self.buildpacks:
            if platform_buildpack["name"] == target_buildpack:
                return platform_buildpack
        return None

    def sync(self) -> list:
        app_buildpacks = self._extract_app_buildpacks()
        out_of_sync_buildpacks = []
        for app_buildpack in app_buildpacks:
            target_platform_buildpack = self._find_platform_buildpack(app_buildpack["name"])
            if target_platform_buildpack is not None:
                target_buildpack = self.fetch_specific_buildpack(target_platform_buildpack["guid"])
                platform_buildpack_version = self.version_matcher.findall(target_buildpack["filename"])[0]
                if version.parse(app_buildpack["version"]) < version.parse(platform_buildpack_version):
                    out_of_sync_buildpacks.append({
                        "app_name": self.app_name,
                        "buildpacks": {
                            "buildpack_name": target_buildpack["name"],
                            "buildpack_version": platform_buildpack_version,
                            "app_buildpack_version": app_buildpack["version"]
                        },
                        "needs_updating": True,
                    })
                else:
                    out_of_sync_buildpacks.append({
                        "app_name": self.app_name,
                        "buildpacks": {
                            "buildpack_name": target_buildpack["name"],
                            "buildpack_version": platform_buildpack_version,
                            "app_buildpack_version": app_buildpack["version"]
                        },
                        "needs_updating": False,
                    })
        return out_of_sync_buildpacks

    def _runner(self, command: str, reason: str) -> dict:
        if self.explain:
            print("{0} ... {1}".format(command, reason))
        return loads(run(cmd(command), capture_output=True, text=True).stdout)
        

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--app-name", help="name of the app to review.")
    parser.add_argument("--org-name", help="name of the org where the app resides.")
    parser.add_argument("--explain", help="explain what we're doing.", action="store_true")
    args = parser.parse_args()
    syncer = BuildpackSyncer(args.app_name, args.org_name, args.explain)
    found = syncer.fetch_app()
    if not found:
        print("cannot find {0} in {1}".format(syncer.app_name, syncer.org_name))
    syncer.fetch_buildpacks()
    results = syncer.sync()
    pprint(results)
