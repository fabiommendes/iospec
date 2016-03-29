import argparse


# Parser for the CLI arguments.
parser = argparse.ArgumentParser(description='Process iospec files.')


def main():
    """Implements the CLI command iospec.

    This is also called when user executes ``python -m iospec``."""

    args = parser.parse_args()


if __name__ == '__main__':
    main()