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
        assert False, "Unexpected file name passed '{0}'".format(name)


def test_invalid_region():
    def my_mock_loader(name):
        res = mock_loader(name)
        if name == 'SHPD':
            res['shepherds'][0]['regions'].append('invalid-region')
        return res

    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = my_mock_loader

        try:
            Venue(TEAMS, 'LYT', 'SHPD')
        except InvalidRegionException as ire:
            assert ire.region == 'invalid-region'
            assert ire.area == 'Yellow'
        else:
            assert False, "Should have errored about the invalid region"


def test_extra_teams():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = mock_loader

        try:
            Venue(['ABC', 'DEF', 'GHI'], 'LYT', 'SHPD')
        except LayoutTeamsException as lte:
            assert lte.extras == set(['JKL', 'MNO', 'PQR'])
            assert lte.duplicates == []
            assert lte.missing == set()
        else:
            assert False, "Should have errored about the extra teams"


def test_duplicate_teams():
    def my_mock_loader(name):
        res = mock_loader(name)
        if name == 'LYT':
            res['teams'][1]['teams'].append('ABC')
        return res

    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = my_mock_loader

        try:
            Venue(TEAMS, 'LYT', 'SHPD')
        except LayoutTeamsException as lte:
            assert lte.duplicates == ['ABC']
            assert lte.extras == set()
            assert lte.missing == set()
        else:
            assert False, "Should have errored about the extra teams"


def test_missing_teams():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = mock_loader

        try:
            Venue(TEAMS + ['Missing'], 'LYT', 'SHPD')
        except LayoutTeamsException as lte:
            assert lte.missing == set(['Missing'])
            assert lte.duplicates == []
            assert lte.extras == set()
        else:
            assert False, "Should have errored about the missing team"


def test_missing_and_extra_teams():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = mock_loader

        try:
            Venue(['ABC', 'DEF', 'GHI', 'Missing'], 'LYT', 'SHPD')
        except LayoutTeamsException as lte:
            assert lte.extras == set(['JKL', 'MNO', 'PQR'])
            assert lte.missing == set(['Missing'])
            assert lte.duplicates == []
        else:
            assert False, "Should have errored about the extra and missing teams"


def test_right_shepherding_areas():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = mock_loader

        venue = Venue(TEAMS, 'LYT', 'SHPD')
        venue.check_staging_times(TIMES)


def test_extra_shepherding_areas():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = mock_loader

        venue = Venue(TEAMS, 'LYT', 'SHPD')
        times = deepcopy(TIMES)
        times['signal_shepherds']['Blue'] = None

        try:
            venue.check_staging_times(times)
        except ShepherdingAreasException as lte:
            assert lte.extras == set(['Blue'])
            assert lte.duplicates == []
            assert lte.missing == set()
        else:
            assert False, "Should have errored about the extra shepherding area"


def test_missing_shepherding_areas():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = mock_loader

        venue = Venue(TEAMS, 'LYT', 'SHPD')
        times = deepcopy(TIMES)
        del times['signal_shepherds']['Pink']

        try:
            venue.check_staging_times(times)
        except ShepherdingAreasException as lte:
            assert lte.missing == set(['Pink'])
            assert lte.extras == set()
            assert lte.duplicates == []
        else:
            assert False, "Should have errored about the missing shepherding area"


def test_missing_and_extra_shepherding_areas():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = mock_loader

        venue = Venue(TEAMS, 'LYT', 'SHPD')
        times = deepcopy(TIMES)
        times['signal_shepherds']['Blue'] = None
        del times['signal_shepherds']['Pink']

        try:
            venue.check_staging_times(times)
        except ShepherdingAreasException as lte:
            assert lte.missing == set(['Pink'])
            assert lte.extras == set(['Blue'])
            assert lte.duplicates == []
        else:
            assert False, "Should have errored about the extra and missing shepherding areas"


def test_locations():
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


def test_get_team_location():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.side_effect = mock_loader

        venue = Venue(TEAMS, 'LYT', 'SHPD')
        loc = venue.get_team_location('DEF')
        assert loc == 'a-group', "Wrong location for team 'DEF'"
