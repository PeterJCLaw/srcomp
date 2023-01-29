"""
YAML loading routines.

This includes parsing of dates and times properly, and also ensures the C YAML
loader is used which is necessary for optimum performance.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import dateutil.parser
import dateutil.tz
import yaml

from .types import YAMLData

try:
    from yaml import CLoader as YAML_Loader
except ImportError:
    from warnings import warn

    from yaml import Loader as YAML_Loader  # type: ignore[assignment]
    warn(
        "Using pure-python PyYAML (without libyaml). "
        "srcomp reads many YAML files, this is liable to be very slow. "
        "Installing libyaml is highly recommended.",
    )


def time_constructor(_: Any, node: yaml.Node) -> datetime.datetime:
    return dateutil.parser.parse(node.value)


def add_time_constructor(loader: type[YAML_Loader]) -> None:
    loader.add_constructor(
        'tag:yaml.org,2002:timestamp',
        time_constructor,
    )


add_time_constructor(YAML_Loader)


def load(file_path: Path) -> YAMLData:
    """
    Load a YAML fie and return the results.

    :param Path file_path: The path to the YAML file.
    :return: The parsed contents.
    """
    with file_path.open(mode='r') as f:
        return yaml.load(f, Loader=YAML_Loader)
