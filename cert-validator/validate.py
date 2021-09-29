import boto3
from cryptography import x509


def get_all_certs(client):
    paginator = client.get_paginator("list_server_certificates")
    certs = []
    for page in paginator.paginate():
        certs.extend(page["ServerCertificateMetadataList"])
    return certs

def check_cert_signer(client, cert):
    cert_data = client.get_server_certificate(ServerCertificateName=cert["ServerCertificateName"])
    body = cert_data["ServerCertificate"]["CertificateBody"]
    body_bytes = bytes(body, "utf-8")
    xcert = x509.load_pem_x509_certificate(body_bytes)
    print(f"issuer: {xcert.issuer}, subject: {xcert.subject}, name: {cert_data['ServerCertificate']['ServerCertificateMetadata']['ServerCertificateName']}")

def main():
    client = boto3.client("iam")
    for cert in get_all_certs(client):
        check_cert_signer(client, cert)
        

if __name__ == "__main__":
    main()
