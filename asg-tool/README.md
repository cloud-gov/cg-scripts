asg-tool
========

CLI tool to work with CF app security groups (ASG).

## Dependencies

This cli tool expects you to have the CF CLI version 7 installed on your machine and the CLI authenticated to run queries against the API with `cf curl` or commands to update space ASGs with `cf bind-security-group`.

## Run tests

```
$ python3 asg-tool/tests.py
```

## Usage

This is a CLI to list and bind ASG's to CloudFoundry spaces. This tool will help you quickly update and check the ASG's related to spaces.

See CLI options:
```
$ python3 ./asg-tool --help

ASG tool to bind and check ASG's applied to CF spaces.

positional arguments:
  {spaces-asg,bind-asg}
                        Run <command> help for more information.
    spaces-asg          List all spaces and their ASG's.
    bind-asg            Bind an ASG to all spaces.

optional arguments:
  -h, --help            show this help message and exit
```

### Bind an ASG to all CF spaces

### List all CF spaces and their ASG's
