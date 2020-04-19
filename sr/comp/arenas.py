"""Arena and corner loading routines."""

from collections import OrderedDict
from typing import Dict, NamedTuple, NewType

from . import yaml_loader
from .types import ArenaName, Colour

CornerNumber = NewType('CornerNumber', int)

Arena = NamedTuple('Arena', [
    ('name', ArenaName),
    ('display_name', str),
    ('colour', Colour),
])
Corner = NamedTuple('Corner', [
    ('number', CornerNumber),
    ('colour', Colour),
])


def load_arenas(filename: str) -> Dict[ArenaName, Arena]:
    """
    Load arenas from a YAML file.

    Parameters
    ----------
    filename : str
        The filename of the YAML file to load arenas from.

    Returns
    -------
    collections.OrderedDict
        A mapping of arena names to :class:`Arena` objects.
    """

    y = yaml_loader.load(filename)

    arenas_data = y['arenas']

    arenas = OrderedDict()
    for name in sorted(arenas_data.keys()):
        d = arenas_data[name]
        arenas[name] = Arena(name, d['display_name'], d.get('colour'))

    return arenas


def load_corners(filename: str) -> Dict[CornerNumber, Corner]:
    """
    Load corner colours from a YAML file.

    Parameters
    ----------
    filename : str
        The filename of the YAML file to load corners from.

    Returns
    -------
    collections.OrderedDict
        A mapping of corner numbers to :class:`Corner` objects.
    """

    y = yaml_loader.load(filename)

    corners = OrderedDict()
    for number, corner in y['corners'].items():
        corners[number] = Corner(number, corner['colour'])

    return corners
