from __future__ import annotations

import sys

from super_dl.app import run


def main() -> int:
    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
