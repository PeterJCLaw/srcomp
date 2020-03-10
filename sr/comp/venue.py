"""Venue layout metadata library."""

from collections import Counter
from itertools import chain

from . import yaml_loader


class InvalidRegionException(Exception):
    """
    An exception that occurs when there are invalid regions mentioned in
    the shepherding data.
    """
    def __init__(self, region, area):
        tpl = "Invalid region '{0}' found in shepherding area '{1}'"
        super(InvalidRegionException, self).__init__(tpl.format(region, area))

        self.region = region
        self.area = area


class MismatchException(Exception):
    """
    An exception that occurs when there are duplicate, extra or missing items.
    """
    def __init__(self, tpl, duplicates, extras, missing):
        details = []

        for label, teams in (
            ("duplicates", duplicates),
            ("extras", extras),
            ("missing", missing),
        ):
            if teams:
                details.append("{0}: ".format(label) + ", ".join(sorted(teams)))

        assert details, "No bad items given to {0}!".format(self.__class__)

        detail = "; ".join(details)
        super(MismatchException, self).__init__(tpl.format(detail))

        self.duplicates = duplicates
        self.extras = extras
        self.missing = missing


class LayoutTeamsException(MismatchException):
    """
    An exception that occurs when there are duplicate, extra or missing
    teams in a layout.
    """
    def __init__(self, duplicate_teams, extra_teams, missing_teams):
        tpl = "Duplicate, extra or missing teams in the layout! ({0})"
        super(LayoutTeamsException, self).__init__(tpl, duplicate_teams, extra_teams, missing_teams)


class ShepherdingAreasException(MismatchException):
    """
    An exception that occurs when there are duplicate, extra or missing
    shepherding areas in the staging times.
    """
    def __init__(self, where, duplicate, extra, missing):
        tpl = "Duplicate, extra or missing shepherding areas {0}! ({{0}})".format(where)
        super(ShepherdingAreasException, self).__init__(tpl, duplicate, extra, missing)


class Venue(object):
    """A class providing information about the layout within the venue."""

    @staticmethod
    def _check_staging_times(shepherding_areas, staging_times):
        """
        Check that the given staging times contain signals for the right
        set of shepherding areas.

        Will throw a :class:`ShepherdingAreasException` if there are
        any missing, extra or duplicate areas found.

        :param list shepherding_areas: The reference list of shepherding
                                       areas at the competition.
        :param list teams_layout: A dict of staging times, containing at
                                  least a ``signal_shepherds`` key which
                                  is a map of times for each area.
        """

        shepherding_areas_set = set(shepherding_areas)
        staging_areas_set = set(staging_times['signal_shepherds'].keys())

        extra_areas = staging_areas_set - shepherding_areas_set
        missing_areas = shepherding_areas_set - staging_areas_set

        if extra_areas or missing_areas:
            raise ShepherdingAreasException(
                "in the staging times",
                [],
                extra_areas,
                missing_areas,
            )

    @staticmethod
    def _get_duplicates(items):
        return [item for item, count in Counter(items).items() if count > 1]

    @classmethod
    def check_teams(cls, teams, teams_layout):
        """
        Check that the given layout of teams contains the same set of
        teams as the reference.

        Will throw a :class:`LayoutTeamsException` if there are any
        missing, extra or duplicate teams found.

        :param list teans: The reference list of teams in the competition.
        :param list teams_layout: A list of maps with a list of teams
                                  under the ``teams`` key.
        """

        layout_teams = list(chain.from_iterable(r['teams'] for r in teams_layout))
        duplicate_teams = cls._get_duplicates(layout_teams)

        teams_set = set(teams)
        layout_teams_set = set(layout_teams)

        extra_teams = layout_teams_set - teams_set
        missing_teams = teams_set - layout_teams_set

        if duplicate_teams or extra_teams or missing_teams:
            raise LayoutTeamsException(duplicate_teams, extra_teams, missing_teams)

    def __init__(self, teams, layout_file, shepherding_file):

        layout_data = yaml_loader.load(layout_file)
        teams_layout = layout_data['teams']
        self.check_teams(teams, teams_layout)

        shepherding_data = yaml_loader.load(shepherding_file)
        shepherds = shepherding_data['shepherds']

        self._shepherding_areas = [a['name'] for a in shepherds]
        """
        A :class:`list` of shepherding zone names from the shepherding file.
        """

        duplicate_areas = self._get_duplicates(self._shepherding_areas)
        if duplicate_areas:
            raise ShepherdingAreasException(
                'in the shepherding data',
                duplicate_areas,
                [],
                [],
            )

        self.locations = {r['name']: r for r in teams_layout}
        """
        A :class:`dict` of location names (from the layout file) to location
        information, including which teams are in that location and the
        shepherding region which contains that location.
        """

        self._team_locations = {}

        for location in teams_layout:
            for team in location['teams']:
                self._team_locations[team] = location

        for area in shepherds:
            for region in area.get('regions', []):
                location = self.locations.get(region)
                if not location:
                    raise InvalidRegionException(region, area['name'])

                location['shepherds'] = {
                    'name': area['name'],
                    'colour': area['colour'],
                }

    def check_staging_times(self, staging_times):
        self._check_staging_times(self._shepherding_areas, staging_times)

    def get_team_location(self, team):
        """
        Get the name of the location allocated to the given team within
        the venue.

        :param str tean: The TLA of the team in question.
        :returns: The name of the location allocated to the team.
        """

        return self._team_locations[team]['name']
