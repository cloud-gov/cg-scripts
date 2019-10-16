import glob
import json
import re
from argparse import Namespace, ArgumentParser
from logging import Formatter
from os import path
from typing import Dict
import importlib
import subprocess
import sys

LOG_FORMAT = Formatter(fmt="[%(asctime)s %(levelname)s %(module)s.%(name)s.%(funcName)s:%(lineno)d] %(message)s")

EXTERNAL_DEPENDENCIES = {
    "logzero": "logzero",
    "pyyaml": "yaml"
}


class Bootstrap(object):
    """
    Bootstrap a new set of packages not included in the Python3 stdlib.
    """

    def __init__(self, packages: dict, **kwargs):
        self.__dict__.update(**kwargs)
        self.packages = packages
        self._init()

    def _init(self):
        for package, import_name in self.packages.items():
            subprocess.call([sys.executable, "-m", "pip", "install", package])
            globals()[package] = importlib.import_module(import_name)


class Filer(object):
    """
    Handles file operations.
    """

    def __init__(self, cmd_args: ArgumentParser, *args, **kwargs):
        self.cmd_args = cmd_args
        self.debug = self.cmd_args.debug
        self.args = args
        self.kwargs = kwargs
        self.all_files = {
            "prod": [],
            "prod_cloud_config": {},
            "staging": [],
            "staging_cloud_config": {},
            "dev": [],
            "dev_cloud_config": {},
        }

        from logzero import setup_logger
        if self.debug:
            self.logger = setup_logger(name=self.__class__.__name__, level=10, formatter=LOG_FORMAT)
        else:
            self.logger = setup_logger(name=self.__class__.__name__, level=20, formatter=LOG_FORMAT)

    def load_all(self) -> Dict:
        """
        Load all files.

        The format of the dictionary returned from Filer.load_all() is as follows:

        dict = {
            "env": [
                { manifest }
            ]
        }

        For example:

        dict = {
            "prod": [
                {
                  "addons": [
                    {
                      "exclude": {
                        "jobs": [
                          {
                            "name": "smoke_tests",
                            "release": "cf-smoke-tests"
                          }
                        ]
                      },
                      ...
                }
            ]
        }

        :rtype: Dict
        :return:
        """
        import yaml

        prod_manifest = re.compile(self.cmd_args.prod_file_pattern)
        staging_manifest = re.compile(self.cmd_args.staging_file_pattern)
        dev_manifest = re.compile(self.cmd_args.dev_file_pattern)

        prod_cloud_config = re.compile(self.cmd_args.prod_cloud_config_pattern)
        staging_cloud_config = re.compile(self.cmd_args.staging_cloud_config_pattern)
        dev_cloud_config = re.compile(self.cmd_args.dev_cloud_config_pattern)

        for f in glob.glob(path.join(self.cmd_args.root_path, "*.yml")):
            self.logger.debug("loading file {0}".format(f))
            with open(f, "r") as stream:

                # grab the file name.
                f = f.split("/")[-1]

                try:
                    self.logger.debug("opening {0}".format(f))
                    data = yaml.safe_load(stream)
                except Exception as e:
                    self.logger.exception(e)
                    continue

                if prod_cloud_config.match(f):
                    self.all_files["prod_cloud_config"] = data
                    continue
                if prod_manifest.match(f):
                    self.all_files["prod"].append(data)
                    continue
                if staging_cloud_config.match(f):
                    self.all_files["staging_cloud_config"] = data
                    continue
                if staging_manifest.match(f):
                    self.all_files["staging"].append(data)
                    continue
                if dev_cloud_config.match(f):
                    self.all_files["dev_cloud_config"] = data
                    continue
                if dev_manifest.match(f):
                    self.all_files["dev"].append(data)
                    continue
        return self.all_files

    def store(self, path: str):
        """
        Store a file in a given path.
        :type path: str
        """
        pass


class Parser(object):
    """
    Handles parsing a BOSH YAML manifest.
    """

    def __init__(self, cmd_args: ArgumentParser, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.cmd_args = cmd_args
        self.debug = self.cmd_args.debug

        from logzero import setup_logger
        if self.debug:
            self.logger = setup_logger(name=self.__class__.__name__, level=10, formatter=LOG_FORMAT)
        else:
            self.logger = setup_logger(name=self.__class__.__name__, level=20, formatter=LOG_FORMAT)

    def count_instances(self, deployment: dict, cloud_config: dict) -> Dict:
        """
        Count the instance types in a deployment.
        :param cloud_config: BOSH cloud config.
        :param deployment: BOSH deployment.
        :return: Dict of values.
        """
        vms = {}

        self.logger.info("counting instances in {0}".format(deployment["name"]))

        for group in deployment["instance_groups"]:
            if "vm_type" in group:
                bosh_vm_type = group["vm_type"]
                aws_vm_type = ""
                for types in cloud_config["vm_types"]:
                    if types["name"] == bosh_vm_type:
                        aws_vm_type = types["cloud_properties"]["instance_type"]

                # for some reason this errors out on the first iteration, and I have no idea why.
                if bosh_vm_type not in vms:
                    vms[aws_vm_type] = {}
                    vms[aws_vm_type]["count"] = 0
                    vms[aws_vm_type]["bosh_vm_type"] = bosh_vm_type

                vms[aws_vm_type]["count"] += group["instances"]

        return vms


def args() -> Namespace:
    args_root = ArgumentParser(usage="Generate a report of deployed VM types for RI purchasing.")
    args_root.add_argument("--debug", help="Enable debug logging.", action="store_true")
    args_root.add_argument("--root-path", help="Path where all manifests and cloud-configs reside.",
                           type=str)
    args_root.add_argument("--prod-file-pattern", help="Pattern for the production manifests. Defaults to `prodbosh*`.",
                           type=str,
                           default="prodbosh-*")
    args_root.add_argument("--staging-file-pattern",
                           help="Pattern for the staging manifests. Defaults to `stagingbosh*`.",
                           type=str,
                           default="stagingbosh-*")
    args_root.add_argument("--dev-file-pattern",
                           help="Pattern for the development manifests. Defaults to `devbosh*`.",
                           type=str,
                           default="devbosh-*")
    args_root.add_argument("--prod-cloud-config-pattern",
                           help="Pattern for the cloud-config manifest. Defaults to `prodbosh*`.",
                           type=str,
                           default="prodbosh-cloud*")
    args_root.add_argument("--staging-cloud-config-pattern",
                           help="Pattern for the cloud-config manifests. Defaults to `stagingbosh*`.",
                           type=str,
                           default="stagingbosh-cloud*")
    args_root.add_argument("--dev-cloud-config-pattern",
                           help="Pattern for the cloud-config manifests. Defaults to `devbosh*`.",
                           type=str,
                           default="devbosh-cloud*")

    for g in args_root._action_groups:
        g._group_actions.sort(key=lambda x: x.dest)

    return args_root.parse_args()


def main():
    Bootstrap(packages=EXTERNAL_DEPENDENCIES)
    cmd_args = args()

    from logzero import setup_logger

    if cmd_args.debug:
        logger = setup_logger("main", level=10, formatter=LOG_FORMAT)
    else:
        logger = setup_logger("main", level=20, formatter=LOG_FORMAT)

    logger.info("loading files")

    f = Filer(cmd_args=cmd_args)
    files = f.load_all()

    p = Parser(cmd_args=cmd_args)

    # store all of our instance data.
    instance_types_global = []

    # prod
    prod_data = [p.count_instances(deployment=depl, cloud_config=files["prod_cloud_config"]) for depl in files["prod"]]
    for instance_types in prod_data:
        keys = instance_types.keys()
        for key in keys:
            instance_types_global.append(key)

    # staging
    staging_data = [p.count_instances(deployment=depl, cloud_config=files["staging_cloud_config"]) for depl in
                    files["staging"]]
    for instance_types in staging_data:
        keys = instance_types.keys()
        for key in keys:
            instance_types_global.append(key)

    # dev
    dev_data = [p.count_instances(deployment=depl, cloud_config=files["dev_cloud_config"]) for depl in
                files["dev"]]
    for instance_types in dev_data:
        keys = instance_types.keys()
        for key in keys:
            instance_types_global.append(key)

    all_instance_types = set(instance_types_global)
    all_instance_types_count = {}
    for itype in all_instance_types:
        all_instance_types_count[itype] = 0

    for instance_type in all_instance_types:
        for depl in prod_data + staging_data + dev_data:
            if instance_type in depl:
                all_instance_types_count[instance_type] += depl[instance_type]["count"]

    print(json.dumps(all_instance_types_count, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
