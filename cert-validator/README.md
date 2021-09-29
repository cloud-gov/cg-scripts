# Cert Validator

Quickly validate certs to make sure they look the same.
This was originally written to audit signers on certs after some 
certificates with untrusted signers were inadvertently introduced, but 
could conceivably be used to audit other facts about certificates.

## installation

Use of a python virtual environment is strongly recommended:

```
$ python3 -m venv venv
```

install requirements:

```
$ source venv/bin/activate
(venv)
$ python -m pip install -r requirements.txt
```

run the script:

```
$ aws-vault exec <my-aws-account> venv/bin/python validate.py
```
