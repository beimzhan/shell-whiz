import argparse
from importlib.metadata import version

from shell_whiz.constants import DEFAULT_MODEL, SW_DESCRIPTION


def create_argument_parser():
    parser = argparse.ArgumentParser(description=SW_DESCRIPTION)

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{SW_DESCRIPTION}. Version {version('shell-whiz')}.",
    )

    subparsers = parser.add_subparsers(dest="sw_command", required=True)

    subparsers.add_parser("config", help="Configure Shell Whiz")

    ask_parser = subparsers.add_parser(
        "ask", help="Ask Shell Whiz for a shell command"
    )
    ask_parser.add_argument(
        "-s", "--shell", type=str, help="set the shell executable"
    )
    ask_parser.add_argument(
        "-p",
        "--preferences",
        type=str,
        default="I use Bash on Linux",
        help="set your preferences (default: %(default)s)",
    )
    ask_parser.add_argument(
        "-m",
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="select the model to use",
    )
    ask_parser.add_argument(
        "--explain-using-gpt-4",  # TODO: remove this later
        action="store_true",
        help="use GPT-4 to explain",
    )
    ask_parser.add_argument(
        "--explain-using", type=str, help="select the model to explain"
    )
    ask_parser.add_argument(
        "-n",
        "--dont-explain",
        action="store_true",
        help="don't explain the command",
    )
    ask_parser.add_argument(
        "--dont-warn",
        action="store_true",
        help="don't warn about dangerous commands",
    )
    ask_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="don't show the menu, end immediately",
    )
    ask_parser.add_argument(
        "-o", "--output", type=str, help="output file to write the command to"
    )
    ask_parser.add_argument(
        "prompt", nargs="+", type=str, help="Prompt for Shell Whiz"
    )

    return parser
