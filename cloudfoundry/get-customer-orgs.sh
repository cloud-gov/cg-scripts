#!/bin/bash

cf orgs \
  | tail -n +4 \
  | grep -i -v 'sandbox\|.*-*test-*.*\|system\|tech\-talk\|^cf\|cloud-gov.*|3pao'
