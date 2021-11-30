#!/usr/bin/env python

# stdlib imports
import pathlib
from dataclasses import dataclass

# local imports
from losspager.run.pager_main import main
from losspager.utils.config import read_config, get_config_file


@dataclass
class Args:
    gridfile: None
    debug: False
    release: False
    cancel: False
    tsunami: False
    elapsed: 0


def test_pager_main():
    # if we're on a system where config file does not exist, don't run the test.
    # means we won't be able to test in CI scenario
    if get_config_file() is None:
        print(
            "We're not running on a system with PAGER data installed. Exiting this test."
        )
        return True
    thisdir = pathlib.Path(__file__).parent
    gridfile = (
        thisdir / ".." / "data" / "eventdata" / "northridge" / "northridge_grid.xml"
    )
    args = Args(
        gridfile=gridfile,
        debug=True,
        release=False,
        cancel=False,
        tsunami=False,
        elapsed=False,
    )
    config = read_config()
    main(args, config)


if __name__ == "__main__":
    test_pager_main()
