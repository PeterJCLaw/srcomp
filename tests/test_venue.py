import unittest
from copy import deepcopy
from unittest import mock

from sr.comp.venue import (
    InvalidRegionException,
    LayoutTeamsException,
    ShepherdingAreasException,
    Venue,
)

TEAMS = ['ABC', 'DEF', 'GHI', 'JKL', 'MNO', 'PQR']
TIMES = {'signal_shepherds': {'Yellow': None, 'Pink': None}}


def mock_layout_loader():
    return {'teams': [
        {
            'name': 'a-group',
            'display_name': "A group",
            'teams': ['ABC', 'DEF', 'GHI'],
        },
        {
            'name': 'b-group',
            'display_name': "B group",
            'teams': ['JKL', 'MNO', 'PQR'],
        },
    ]}


def mock_shepherding_loader():
    return {'shepherds': [
        {
            'name': 'Yellow',
            'colour': 'colour-yellow',
            'regions': ['a-group'],
        },
        {
            'name': 'Pink',
            'colour': 'colour-pink',
            'regions': ['b-group'],
        },
    ]}


def mock_loader(name):
    if name == 'LYT':
        return mock_layout_loader()
    elif name == 'SHPD':
        return mock_shepherding_loader()
    else:
        raise ValueError("Unexpected file name passed '{0}'".format(name))


class VenueTests(unittest.TestCase):
    def test_invalid_region(self):
        def my_mock_loader(name):
            res = mock_loader(name)
            if name == 'SHPD':
                res['shepherds'][0]['regions'].append('invalid-region')
            return res

        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = my_mock_loader

            with self.assertRaises(
                InvalidRegionException,
                msg="Should have errored about the invalid region",
            ) as cm:
                Venue(TEAMS, 'LYT', 'SHPD')

            ire = cm.exception
            assert ire.region == 'invalid-region'
            assert ire.area == 'Yellow'

    def test_extra_teams(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            with self.assertRaises(
                LayoutTeamsException,
                msg="Should have errored about the extra teams",
            ) as cm:
                Venue(['ABC', 'DEF', 'GHI'], 'LYT', 'SHPD')

            lte = cm.exception
            assert lte.extras == set(['JKL', 'MNO', 'PQR'])
            assert lte.duplicates == []
            assert lte.missing == set()

    def test_duplicate_teams(self):
        def my_mock_loader(name):
            res = mock_loader(name)
            if name == 'LYT':
                res['teams'][1]['teams'].append('ABC')
            return res

        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = my_mock_loader

            with self.assertRaises(
                LayoutTeamsException,
                msg="Should have errored about the extra teams",
            ) as cm:
                Venue(TEAMS, 'LYT', 'SHPD')

            lte = cm.exception
            assert lte.duplicates == ['ABC']
            assert lte.extras == set()
            assert lte.missing == set()

    def test_missing_teams(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            with self.assertRaises(
                LayoutTeamsException,
                msg="Should have errored about the missing team",
            ) as cm:
                Venue(TEAMS + ['Missing'], 'LYT', 'SHPD')

            lte = cm.exception
            assert lte.missing == set(['Missing'])
            assert lte.duplicates == []
            assert lte.extras == set()

    def test_missing_and_extra_teams(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            with self.assertRaises(
                LayoutTeamsException,
                msg="Should have errored about the extra and missing teams",
            ) as cm:
                Venue(['ABC', 'DEF', 'GHI', 'Missing'], 'LYT', 'SHPD')

            lte = cm.exception
            assert lte.extras == set(['JKL', 'MNO', 'PQR'])
            assert lte.missing == set(['Missing'])
            assert lte.duplicates == []

    def test_right_shepherding_areas(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = Venue(TEAMS, 'LYT', 'SHPD')
            venue.check_staging_times(TIMES)

    def test_extra_shepherding_areas(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = Venue(TEAMS, 'LYT', 'SHPD')
            times = deepcopy(TIMES)
            times['signal_shepherds']['Blue'] = None

            with self.assertRaises(
                ShepherdingAreasException,
                msg="Should have errored about the extra shepherding area",
            ) as cm:
                venue.check_staging_times(times)

            lte = cm.exception
            assert lte.extras == set(['Blue'])
            assert lte.duplicates == []
            assert lte.missing == set()

    def test_missing_shepherding_areas(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = Venue(TEAMS, 'LYT', 'SHPD')
            times = deepcopy(TIMES)
            del times['signal_shepherds']['Pink']

            with self.assertRaises(
                ShepherdingAreasException,
                msg="Should have errored about the missing shepherding area",
            ) as cm:
                venue.check_staging_times(times)

            lte = cm.exception
            assert lte.missing == set(['Pink'])
            assert lte.extras == set()
            assert lte.duplicates == []

    def test_missing_and_extra_shepherding_areas(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = Venue(TEAMS, 'LYT', 'SHPD')
            times = deepcopy(TIMES)
            times['signal_shepherds']['Blue'] = None
            del times['signal_shepherds']['Pink']

            with self.assertRaises(
                ShepherdingAreasException,
                msg="Should have errored about the extra and missing shepherding areas",
            ) as cm:
                venue.check_staging_times(times)

            lte = cm.exception
            assert lte.missing == set(['Pink'])
            assert lte.extras == set(['Blue'])
            assert lte.duplicates == []

    def test_locations(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = Venue(TEAMS, 'LYT', 'SHPD')

            expected = {
                'a-group': {
                    'name': 'a-group',
                    'display_name': "A group",
                    'teams': ['ABC', 'DEF', 'GHI'],
                    'shepherds': {
                        'name': 'Yellow',
                        'colour': 'colour-yellow',
                    },
                },
                'b-group': {
                    'name': 'b-group',
                    'display_name': "B group",
                    'teams': ['JKL', 'MNO', 'PQR'],
                    'shepherds': {
                        'name': 'Pink',
                        'colour': 'colour-pink',
                    },
                },
            }

            locations = venue.locations
            assert locations == expected

    def test_get_team_location(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.side_effect = mock_loader

            venue = Venue(TEAMS, 'LYT', 'SHPD')
            loc = venue.get_team_location('DEF')
            assert loc == 'a-group', "Wrong location for team 'DEF'"
