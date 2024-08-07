from __future__ import annotations

import datetime
import unittest
from collections.abc import Iterable
from pathlib import Path
from typing import cast, overload
from typing_extensions import Literal
from unittest import mock

from sr.comp.matches import StagingOffsets
from sr.comp.types import (
    Colour,
    LayoutData,
    RegionData,
    RegionName,
    ShepherdData,
    ShepherdingData,
    ShepherdName,
    TLA,
)
from sr.comp.venue import (
    InvalidRegionException,
    LayoutTeamsException,
    ShepherdingAreasException,
    Venue,
)

TEAMS = [TLA('ABC'), TLA('DEF'), TLA('GHI'), TLA('JKL'), TLA('MNO'), TLA('PQR')]


def build_staging_offsets(shepherds: Iterable[str] = ('Yellow', 'Pink')) -> StagingOffsets:
    return StagingOffsets({
        'signal_shepherds': {
            ShepherdName(x): datetime.timedelta() for x in shepherds
        },
        'opens': datetime.timedelta(),
        'closes': datetime.timedelta(),
        'duration': datetime.timedelta(),
        'signal_teams': datetime.timedelta(),
    })


def mock_layout_loader() -> LayoutData:
    return LayoutData({'teams': [
        RegionData({
            'name': RegionName('a-group'),
            'display_name': "A group",
            'description': '',
            'teams': [TLA('ABC'), TLA('DEF'), TLA('GHI')],
        }),
        RegionData({
            'name': RegionName('b-group'),
            'display_name': "B group",
            'description': '',
            'teams': [TLA('JKL'), TLA('MNO'), TLA('PQR')],
        }),
    ]})


def mock_shepherding_loader() -> ShepherdingData:
    return ShepherdingData({'shepherds': [
        ShepherdData({
            'name': ShepherdName('Yellow'),
            'colour': Colour('colour-yellow'),
            'regions': [RegionName('a-group')],
        }),
        ShepherdData({
            'name': ShepherdName('Pink'),
            'colour': Colour('colour-pink'),
            'regions': [RegionName('b-group')],
        }),
    ]})


@overload
def mock_loader(name: Literal['LYT']) -> LayoutData:
    ...


@overload
def mock_loader(name: Literal['SHPD']) -> ShepherdingData:
    ...


def mock_loader(
    name: Literal['LYT', 'SHPD'],
) -> LayoutData | ShepherdingData:
    if name == 'LYT':
        return mock_layout_loader()
    elif name == 'SHPD':
        return mock_shepherding_loader()
    else:
        raise ValueError(f"Unexpected file name passed '{name}'")


class VenueTests(unittest.TestCase):
    def build_venue(self, teams: Iterable[TLA]) -> Venue:
        # Cast the layout and shepherding files ids as we need the literals to
        # make the mock_loader(s) work.
        return Venue(teams, cast(Path, 'LYT'), cast(Path, 'SHPD'))

    def test_invalid_region(self) -> None:
        def my_mock_loader(name: Literal['LYT', 'SHPD']) -> LayoutData | ShepherdingData:
            if name == 'SHPD':
                res = mock_loader(name)
                res['shepherds'][0]['regions'].append(RegionName('invalid-region'))
                return res
            return mock_loader(name)

        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = my_mock_loader

            with self.assertRaises(
                InvalidRegionException,
                msg="Should have errored about the invalid region",
            ) as cm:
                self.build_venue(TEAMS)

            ire = cm.exception
            self.assertEqual('invalid-region', ire.region)
            self.assertEqual('Yellow', ire.area)

    def test_extra_teams(self) -> None:
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            with self.assertRaises(
                LayoutTeamsException,
                msg="Should have errored about the extra teams",
            ) as cm:
                self.build_venue([TLA('ABC'), TLA('DEF'), TLA('GHI')])

            lte = cm.exception
            self.assertEqual(set(['JKL', 'MNO', 'PQR']), lte.extras)
            self.assertEqual([], lte.duplicates)
            self.assertEqual(set(), lte.missing)

    def test_duplicate_teams(self) -> None:
        def my_mock_loader(name: Literal['LYT', 'SHPD']) -> LayoutData | ShepherdingData:
            if name == 'LYT':
                res = mock_loader(name)
                res['teams'][1]['teams'].append(TLA('ABC'))
                return res
            return mock_loader(name)

        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = my_mock_loader

            with self.assertRaises(
                LayoutTeamsException,
                msg="Should have errored about the extra teams",
            ) as cm:
                self.build_venue(TEAMS)

            lte = cm.exception
            self.assertEqual(['ABC'], lte.duplicates)
            self.assertEqual(set(), lte.extras)
            self.assertEqual(set(), lte.missing)

    def test_missing_teams(self) -> None:
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            with self.assertRaises(
                LayoutTeamsException,
                msg="Should have errored about the missing team",
            ) as cm:
                self.build_venue(TEAMS + [TLA('Missing')])

            lte = cm.exception
            self.assertEqual(set(['Missing']), lte.missing)
            self.assertEqual([], lte.duplicates)
            self.assertEqual(set(), lte.extras)

    def test_missing_and_extra_teams(self) -> None:
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            with self.assertRaises(
                LayoutTeamsException,
                msg="Should have errored about the extra and missing teams",
            ) as cm:
                self.build_venue([TLA('ABC'), TLA('DEF'), TLA('GHI'), TLA('Missing')])

            lte = cm.exception
            self.assertEqual(set(['JKL', 'MNO', 'PQR']), lte.extras)
            self.assertEqual(set(['Missing']), lte.missing)
            self.assertEqual([], lte.duplicates)

    def test_right_shepherding_areas(self) -> None:
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = self.build_venue(TEAMS)
            venue.check_staging_times(build_staging_offsets())

    def test_extra_shepherding_areas(self) -> None:
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = self.build_venue(TEAMS)
            times = build_staging_offsets(('Yellow', 'Pink', 'Blue'))

            with self.assertRaises(
                ShepherdingAreasException,
                msg="Should have errored about the extra shepherding area",
            ) as cm:
                venue.check_staging_times(times)

            lte = cm.exception
            self.assertEqual(set(['Blue']), lte.extras)
            self.assertEqual([], lte.duplicates)
            self.assertEqual(set(), lte.missing)

    def test_missing_shepherding_areas(self) -> None:
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = self.build_venue(TEAMS)
            times = build_staging_offsets(('Yellow',))

            with self.assertRaises(
                ShepherdingAreasException,
                msg="Should have errored about the missing shepherding area",
            ) as cm:
                venue.check_staging_times(times)

            lte = cm.exception
            self.assertEqual(set(['Pink']), lte.missing)
            self.assertEqual(set(), lte.extras)
            self.assertEqual([], lte.duplicates)

    def test_missing_and_extra_shepherding_areas(self) -> None:
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = self.build_venue(TEAMS)
            times = build_staging_offsets(('Yellow', 'Blue'))

            with self.assertRaises(
                ShepherdingAreasException,
                msg="Should have errored about the extra and missing shepherding areas",
            ) as cm:
                venue.check_staging_times(times)

            lte = cm.exception
            self.assertEqual(set(['Pink']), lte.missing)
            self.assertEqual(set(['Blue']), lte.extras)
            self.assertEqual([], lte.duplicates)

    def test_locations(self) -> None:
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = self.build_venue(TEAMS)

            expected = {
                'a-group': {
                    'name': 'a-group',
                    'display_name': "A group",
                    'description': "",
                    'teams': ['ABC', 'DEF', 'GHI'],
                    'shepherds': {
                        'name': 'Yellow',
                        'colour': 'colour-yellow',
                    },
                },
                'b-group': {
                    'name': 'b-group',
                    'display_name': "B group",
                    'description': "",
                    'teams': ['JKL', 'MNO', 'PQR'],
                    'shepherds': {
                        'name': 'Pink',
                        'colour': 'colour-pink',
                    },
                },
            }

            locations = venue.locations
            self.assertEqual(expected, locations)

    def test_get_team_location(self) -> None:
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = self.build_venue(TEAMS)
            loc = venue.get_team_location(TLA('DEF'))
            self.assertEqual(
                'a-group',
                loc,
                "Wrong location for team 'DEF'",
            )
