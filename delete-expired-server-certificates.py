#!/usr/bin/env python3

import argparse
import subprocess
import datetime
import json

def get_certificates():
    command = ["aws", "iam", 
    "list-server-certificates"
    ]
    out = subprocess.run(command, check=True, capture_output=True)
    cert_obj = json.loads(out.stdout)
    return cert_obj["ServerCertificateMetadataList"]


def delete_certificate(name, dry_run):
    command = ["aws", "iam", 
    "delete-server-certificate",
    "--server-certificate-name", name]
    print(command)
    if not dry_run:
        subprocess.run(command)


def is_too_old(cert):
    now = datetime.datetime.now()
    expiration = cert["Expiration"]
    expiration = datetime.datetime.strptime(expiration, "%Y-%m-%dT%H:%M:%SZ")
    return expiration < now


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    certs = get_certificates()
    expired_certs = [cert for cert in certs if is_too_old(cert)]
    for cert in expired_certs:
        delete_certificate(cert["ServerCertificateName"], args.dry_run)


if __name__ == "__main__":
    main()
