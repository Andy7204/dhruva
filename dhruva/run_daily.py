"""Canonical guarded CLI for the deterministic paper pipeline."""
import argparse

from dhruva.operations import run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-refresh', action='store_true', help='Use cache; all guards still apply')
    args = parser.parse_args(argv)
    return run(refresh=not args.no_refresh)


if __name__ == '__main__': main()
