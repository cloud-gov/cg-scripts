#!/bin/bash

# Disable AWS pager so output goes straight to console
export AWS_PAGER=''

aws iam generate-credential-report
aws iam get-credential-report
aws iam get-account-summary
aws iam list-virtual-mfa-devices --output table
aws iam get-account-password-policy --output table
aws iam get-account-authorization-details --output table
aws iam list-instance-profiles --output table