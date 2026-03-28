"""A sample Click CLI tool for testing."""

import click


@click.group()
def cli():
    """Sample CLI tool."""
    pass


@cli.command()
@click.argument("name")
@click.option("--count", default=1, help="Number of times to greet.")
def greet(name: str, count: int) -> None:
    """Greet NAME count times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")


@cli.command()
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
def status(verbose: bool) -> None:
    """Show status information."""
    click.echo("Status: OK")
    if verbose:
        click.echo("All systems operational.")


@cli.command()
@click.argument("input_file", type=click.Path(exists=False))
@click.argument("output_file", type=click.Path())
def process(input_file: str, output_file: str) -> None:
    """Process INPUT_FILE and write to OUTPUT_FILE."""
    # TODO: implement actual processing
    click.echo(f"Processing {input_file} -> {output_file}")


if __name__ == "__main__":
    cli()
