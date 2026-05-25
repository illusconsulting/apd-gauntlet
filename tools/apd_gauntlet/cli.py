"""apd-gauntlet CLI entry point."""
from __future__ import annotations
import click
from . import __version__


@click.group(
    name="apd-gauntlet",
    help="APD Gauntlet — validator and tooling for APD security architecture reviews.",
)
@click.version_option(__version__, prog_name="apd-gauntlet")
def main():
    """Root command group."""


if __name__ == "__main__":
    main()
