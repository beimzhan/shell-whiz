import typer

from .commands.ask import ask
from .commands.config import config

cli = typer.Typer(help="Shell Whiz: AI assistant for the command line")

cli.command()(ask)
cli.command()(config)
