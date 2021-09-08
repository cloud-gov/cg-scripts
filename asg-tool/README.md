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

usage: asg-tool [-h] {check-spaces,bind-asg,unbind-asg} ...

ASG tool to bind and check ASG's applied to CF spaces.

positional arguments:
  {check-spaces,bind-asg,unbind-asg}
                        Run <command> help for more information.
    check-spaces        List all spaces and their ASG's.
    bind-asg            Bind an ASG to all spaces.
    unbind-asg          Unbind an ASG from all spaces.

optional arguments:
  -h, --help            show this help message and exit
```

### Bind an ASG from all CF spaces

Example
```
$ python3 ./asg-tool bind-asg -an example_security_group
Getting space information
Start binding security group example_security_group to all spaces
Bound example_security_group for NAME: space-1 - GUID: abcdefgh-1111-4444-zzzz-abcd12345678
Bound example_security_group for NAME: space-2 - GUID: aaaaaaaa-1111-bbbb-2222-qwertyuiopas
Bound example_security_group for NAME: space-3 - GUID: qwertyio-4321-1234-9191-azsxdcdcfvgg
Bound example_security_group for NAME: space-4 - GUID: asdfasdf-2211-1122-alal-asdfasdfasdf
```

### Unbind an ASG from all CF spaces

Example
```
$ python3 ./asg-tool unbind-asg -an example_security_group
Getting space information
Start unbinding security group example_security_group from all spaces
Unbond example_security_group for NAME: space-1 - GUID: abcdefgh-1111-4444-zzzz-abcd12345678
Unbond example_security_group for NAME: space-2 - GUID: aaaaaaaa-1111-bbbb-2222-qwertyuiopas
Unbond example_security_group for NAME: space-3 - GUID: qwertyio-4321-1234-9191-azsxdcdcfvgg
Unbond example_security_group for NAME: space-4 - GUID: asdfasdf-2211-1122-alal-asdfasdfasdf
```

### List all CF spaces and their ASG's

Example
```
$ python3 ./asg-tool check-spaces
Getting space information
[{'guid': 'asdfasdf-3333-2222-3333-asdfasdfasdf',
  'name': 'space-1',
  'security_groups': [{'guid': 'ffffffff-asdf-asdf-asdf-111112321222',
                       'name': 'group-1'},
                      {'guid': 'abababab-2222-oooo-2222-098765432123',
                       'name': 'group-2'}]....
```
