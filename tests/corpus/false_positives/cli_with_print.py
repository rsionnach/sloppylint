"""CLI application with legitimate print statements.

This file should NOT trigger debug_print warnings because:
1. It imports click (CLI framework)
2. Print statements are for user output in CLI apps
"""

import click


@click.command()
@click.option("--name", default="World", help="Name to greet")
def main(name: str) -> None:
    """Greet someone."""
    print(f"Hello, {name}!")
    print("This is a CLI application")


if __name__ == "__main__":
    main()
