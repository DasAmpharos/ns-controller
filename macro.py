import click


@click.command()
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", default=9000, type=int, help="Server port")
def main(host: str, port: int) -> None:
    pass


if __name__ == "__main__":
    main()
