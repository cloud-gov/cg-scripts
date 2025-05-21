#!/bin/env python3
import argparse
import pprint
from asg_tool import bind_asg, check_spaces, unbind_asg


def parse_args():
    parser = argparse.ArgumentParser(
        description="ASG tool to bind and check ASG's applied to CF spaces."
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Run <command> help for more information."
    )

    subparsers.add_parser("check-spaces", help="List all spaces and their ASG's.")
    bind_asg_parser = subparsers.add_parser(
        "bind-asg", help="Bind an ASG to all spaces."
    )
    bind_asg_parser.add_argument(
        "-an",
        "--asg-name",
        dest="asg_name",
        required=True,
        type=str,
        help="Name of ASG to bind",
    )

    unbind_asg_parser = subparsers.add_parser(
        "unbind-asg", help="Unbind an ASG from all spaces."
    )
    unbind_asg_parser.add_argument(
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
        if args.command == "check-spaces":
            spaces = check_spaces()
            pprint.pprint(spaces)
            return
        if args.command == "bind-asg":
            results = bind_asg(args.asg_name)
            print(results)
            return
        if args.command == "unbind-asg":
            results = unbind_asg(args.asg_name)
            print(results)
            return
        else:
            print("Please run 'python3 ./asg-tool --help'")
    except Exception as e:
        print(f"An error occurred while running `python3 ./asg-tool {args.command}`")
        print(str(e))
        print("Please revise your and try again.")
    finally:
        return


main()
