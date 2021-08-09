#!/bin/env python3
import argparse
import contextlib
import datetime
import re
import os
import sys
import subprocess
import json
import time

script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))

@contextlib.contextmanager
def cd(path):
   old_path = os.getcwd()
   os.chdir(path)
   try:
       yield
   finally:
       os.chdir(old_path)

def wait_print(seconds, description=""):
    print(description, end="", sep="", flush=True)
    for _ in range(seconds):
        time.sleep(1)
        print(".", end="", sep="", flush=True)
    print()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cert-name", required=True, help="name of expiring certificate")
    parser.add_argument("--alb-listener-arn", required=True, help="alb listener arn")
    return parser.parse_args()

def get_guid(cert_name):
    certificate_name_re = re.compile(r'(cdn-route|cf-domains)-(?P<guid>([^-]+-){4}[^-]+)-(?P<expiration>.+)')

    m = re.search(certificate_name_re, cert_name)
    guid = m.group("guid")
    print(f"guid: {guid}")
    return guid

def get_domains(guid):
    out = subprocess.run(["cf", "curl", f'/v3/service_instances/{guid}',], capture_output=True, check=True)

    service_data = json.loads(out.stdout)

    description = service_data["last_operation"]["description"]
    domains = description.split(';')[1].split(' ')[2:]
    domains = [domain.replace(",","") for domain in domains]
    print(f"domains: {domains}")
 
    return domains

def do_certbot(domains):
    config_dir = "./config"
    logs_dir = "./logs"
    work_dir = "./work"

    command = ["certbot", "certonly",
    "-m", "cloud-gov-operations@gsa.gov",
    "--non-interactive",
    "--agree-tos",
    "--preferred-challenges", "http",
    "--manual",
    "--manual-auth-hook", f"{script_dir}/manual_hook.sh",
    "--manual-cleanup-hook", f"{script_dir}/cleanup.sh",
    "--work-dir", work_dir,
    "--config-dir", config_dir,
    "--logs-dir", logs_dir, ]
    for domain in domains:
        command.extend(["-d", domain])

    out = subprocess.run(command, check=True)


def upload_certs(domain, guid, path):
    openssl_command = [
        "openssl", "x509",
        "-enddate",
        "-noout",
        "-in", f"config/live/{domain}/cert.pem"
        ]
    out = subprocess.run(openssl_command, capture_output=True, text=True, check=True)

    _, _, date = out.stdout.partition("=")
    date = date.rstrip()
    date = datetime.datetime.strptime(date, "%b %d %H:%M:%S %Y %Z")

    new_cert_name = f"cf-domains-{guid}-{date.strftime('%Y-%m-%d_%H-%M-%s')}"

    upload_command = [
        "aws", "iam", "upload-server-certificate",
        "--server-certificate-name", new_cert_name,
        "--certificate-body", "file://cert.pem",
        "--private-key", "file://privkey.pem",
        "--certificate-chain", "file://chain.pem", 
        "--path", path
    ]
    with cd(f"config/live/{domain}"):
        out = subprocess.run(upload_command, capture_output=True, text=True, check=True)
    data = json.loads(out.stdout)
    return data["ServerCertificateMetadata"]


def associate_certs(alb_listener_arn, cert_arn):
    wait_print(10, "waiting for cert to be available in IAM")
    command = [
        "aws", "elbv2",
        "add-listener-certificates",
        "--listener-arn", alb_listener_arn,
        "--certificates", f"CertificateArn={cert_arn}"
    ]
    out = subprocess.run(command, check=True)

def check_domain_using_new_cert(domain):
    # note that we're using shell=True and strings instead of arrays
    # this is to make piping work, but this could probably be redone without it

    # connect to host and get the cert. Read from /dev/null to terminate the connection
    connect_command = f"openssl s_client -connect {domain}:443 -servername {domain} < /dev/null 2>/dev/null"
    fingerprint_command = "openssl x509 -noout -fingerprint"
    
    get_live_fingerprint_command = "|".join([connect_command, fingerprint_command])

    local_fingerprint_command = fingerprint_command + f" -in config/live/{domain}/cert.pem"

    
    live = subprocess.run(get_live_fingerprint_command, shell=True, capture_output=True)
    local = subprocess.run(local_fingerprint_command, shell=True, capture_output=True)
    retries = 0
    while live.stdout != local.stdout:
        print(f"live: {live.stdout}")
        print(f"local: {local.stdout}")
        if retries > 6:
            raise RuntimeError("doesn't look like the cert uploaded")
        retries += 1
        wait_print(2**retries, "waiting for new cert to be active on listener")
        live = subprocess.run(get_live_fingerprint_command, shell=True, capture_output=True)
        local = subprocess.run(local_fingerprint_command, shell=True, capture_output=True)


def unassociate_old_cert(alb_listener_arn, cert_name):
    get_cert_command = [
        "aws", "iam",
        "get-server-certificate",
        "--server-certificate-name", cert_name
    ]
    out = subprocess.run(get_cert_command, capture_output=True, text=True, check=True)
    cert_data = json.loads(out.stdout)
    cert_arn = cert_data["ServerCertificate"]["ServerCertificateMetadata"]["Arn"]

    unassociate_command = [
        "aws", "elbv2",
        "remove-listener-certificates",
        "--listener-arn", alb_listener_arn,
        "--certificates", f"CertificateArn={cert_arn}"
    ]
    out = subprocess.run(unassociate_command)

def delete_cert(cert_name):
    wait_print(30, "waiting for old cert to be cleared from listener")
    command = [
        "aws", "iam",
        "delete-server-certificate",
        "--server-certificate-name", cert_name
    ]
    out = subprocess.run(command)

def main():
    args = parse_args()
    if not os.getenv("CERTBOT_BUCKET_NAME"):
        raise RuntimeError("CERTBOT_BUCKET_NAME must be set")

    with cd(script_dir):
        print("getting guid and domains")
        guid = get_guid(args.cert_name)
        try:
            domains = get_domains(guid)
        except:
            print(f"failed to get domains for {guid}")
            sys.exit()
        print("getting certificate")
        do_certbot(domains)
        print("uploading certificate")
        new_cert_data = upload_certs(domains[0], guid, "/domains/production/")
        print("adding new certificate to load balancer")
        associate_certs(args.alb_listener_arn, new_cert_data["Arn"])
        print("validating new cert is active")
        check_domain_using_new_cert(domains[0])
        print("removing old certificate from load balancer")
        unassociate_old_cert(args.alb_listener_arn, args.cert_name)
        print("deleting old certificate")
        delete_cert(args.cert_name)


if __name__ == "__main__":
    main()
