import argparse
import copy
import json
import os
import subprocess
import sys

import alb_certs

script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdn-id", help="the id of the cloudfront distribution")
    return parser.parse_args()


def get_cdn_info(cdn_id):
    command = [
        "aws", "cloudfront",
        "get-distribution-config",
        "--id", cdn_id
    ]
    out = subprocess.run(command, capture_output=True, check=True, text=True)
    return json.loads(out.stdout)


def domains_from_cdn_info(cdn_info):
    return cdn_info["DistributionConfig"]["Aliases"]["Items"]


def cert_id_from_cdn_info(cdn_info):
    return cdn_info["DistributionConfig"]["ViewerCertificate"]["IAMCertificateId"]


def get_all_certs():
    cert_metadata_list = []
    all_certs_command = [
        "aws", "iam",
        "list-server-certificates"
    ]
    out = subprocess.run(all_certs_command, capture_output=True, check=True, text=True)
    certs = json.loads(out.stdout)
    cert_metadata_list.extend(certs["ServerCertificateMetadataList"])
    while certs.get("NextToken", False):
        # list here is a shortcut to copy the list
        command = list(all_certs_command)
        command.extend(["--starting-token", certs["NextToken"]])
        out = subprocess.run(command, capture_output=True, check=True, text=True)
        certs = json.loads(out.stdout)
        cert_metadata_list.extend(certs["ServerCertificateMetadataList"])
    return cert_metadata_list


def cert_data_from_id(cert_id):
    certs = get_all_certs()
    for cert in certs:
        if cert["ServerCertificateId"] == cert_id:
            # dict here is shortcut to copy the cert
            return dict(cert)


def update_cdn_info(cdn_info, cert_data, cdn_id):
    cert_id = cert_data["ServerCertificateId"]
    cdn = copy.deepcopy(cdn_info)
    config = cdn["DistributionConfig"]
    etag = cdn["ETag"]
    config["ViewerCertificate"]["IAMCertificateId"] = cert_data["ServerCertificateId"]
    command = [
        "aws", "cloudfront",
        "update-distribution",
        "--distribution-config", json.dumps(config),
        "--if-match", etag, 
        "--id", cdn_id
    ]
    subprocess.run(command, check=True)



def main():
    args = get_args()
    if not os.getenv("CERTBOT_BUCKET_NAME"):
        raise RuntimeError("CERTBOT_BUCKET_NAME must be set")
    with alb_certs.cd(script_dir):
        print("getting CDN information")
        cdn_info = get_cdn_info(args.cdn_id)
        domains = domains_from_cdn_info(cdn_info)
        print("getting certificate information")
        old_cert_id = cert_id_from_cdn_info(cdn_info)
        cert_data = cert_data_from_id(old_cert_id)
        print(cert_data)
        guid = alb_certs.get_guid(cert_data["ServerCertificateName"])
        print("getting certificate")
        alb_certs.do_certbot(domains)
        print("uploading certificate")
        new_cert_info = alb_certs.upload_certs(domains[0], guid, "/cloudfront/cg-production/")
        alb_certs.wait_print(10, "waiting for IAM to figure out cert")
        update_cdn_info(cdn_info, new_cert_info, args.cdn_id)



if __name__ == "__main__":
    main()
