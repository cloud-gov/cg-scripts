import json
from argparse import Namespace, ArgumentParser
from logging import Formatter
import importlib
import subprocess
import sys

LOG_FORMAT = Formatter(fmt="[%(asctime)s %(levelname)s %(module)s.%(name)s.%(funcName)s:%(lineno)d] %(message)s")

EXTERNAL_DEPENDENCIES = {
    "logzero": "logzero",
    "boto3": "boto3"
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


def args() -> Namespace:
    args_root = ArgumentParser(usage="Generate a report of deployed VM types for RI purchasing.")
    args_root.add_argument("--debug", help="Enable debug logging.", action="store_true")
    args_root.add_argument("--install-dependencies", help="Install the needed dependencies to run this script.", action="store_true", default=False)
    args_root.add_argument("--aws-access-key-id", help="AWS access key for the account you want to report on.",
                           type=str)
    args_root.add_argument("--aws-secret-access-key", help="Matching AWS secret account key.",
                           type=str)

    for g in args_root._action_groups:
        g._group_actions.sort(key=lambda x: x.dest)

    return args_root.parse_args()


def main():
    cmd_args = args()

    if cmd_args.install_dependencies:
        Bootstrap(packages=EXTERNAL_DEPENDENCIES)

    from logzero import setup_logger

    if cmd_args.debug:
        logger = setup_logger("main", level=10, formatter=LOG_FORMAT)
    else:
        logger = setup_logger("main", level=20, formatter=LOG_FORMAT)

    logger.debug("building aws client")

    import boto3
    ec2client = boto3.client("ec2")

    instance_count = {}

    instance_resp = ec2client.describe_instances()
    for instances in instance_resp["Reservations"]:
        for instance in instances["Instances"]:
            if instance["InstanceType"] not in instance_count:
                instance_count[instance["InstanceType"]] = 0
            instance_count[instance["InstanceType"]] += 1

    print(json.dumps(instance_count, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
