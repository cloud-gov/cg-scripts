#!/bin/env python3
import argparse
from asg_tool import get_spaces, bind_asg


def parse_args():
    parser = argparse.ArgumentParser(
        description="ASG tool to bind and check ASG's applied to CF spaces."
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Run <command> help for more information."
    )

    subparsers.add_parser("spaces-asg", help="List all spaces and their ASG's.")
    bind_asg = subparsers.add_parser("bind-asg", help="Bind an ASG to all spaces.")
    bind_asg.add_argument(
        "-an",
        "--asg-name",
        dest="asg_name",
        required=True,
        type=str,
        help="Name of ASG to bind",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    try:
        if args.command == "spaces-asg":
            spaces = get_spaces()
            print(spaces)
        if args.command == "bind-asg":
            results = bind_asg(args.asg_name)
            print(results)
        else:
            print("Please run 'python3 ./asg-tool --help'")
    except Exception as e:
        print(str(e))
    finally:
        return


main()
