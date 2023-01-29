"""Venue layout metadata library."""

from __future__ import annotations

from collections import Counter
from itertools import chain
from pathlib import Path
from typing import Generic, Iterable, Mapping, TypeVar

from . import yaml_loader
from .matches import StagingOffsets
from .types import (
    LayoutData,
    Region,
    RegionData,
    RegionName,
    ShepherdData,
    ShepherdingArea,
    ShepherdingData,
    ShepherdName,
    TLA,
)

T = TypeVar('T')
T_str = TypeVar('T_str', bound=str)


class InvalidRegionException(Exception):
    """
    An exception that occurs when there are invalid regions mentioned in
    the shepherding data.
    """

    def __init__(self, region: RegionName, area: str) -> None:
        tpl = "Invalid region '{0}' found in shepherding area '{1}'"
        super().__init__(tpl.format(region, area))

        self.region = region
        self.area = area


class MismatchException(Exception, Generic[T_str]):
    """
    An exception that occurs when there are duplicate, extra or missing items.
    """

    def __init__(
        self,
        tpl: str,
        duplicates: Iterable[T_str],
        extras: Iterable[T_str],
        missing: Iterable[T_str],
    ) -> None:
        details = []

        for label, teams in (
            ("duplicates", duplicates),
            ("extras", extras),
            ("missing", missing),
        ):
            if teams:
                details.append(f"{label}: " + ", ".join(sorted(teams)))

        assert details, f"No bad items given to {self.__class__}!"

        detail = "; ".join(details)
        super().__init__(tpl.format(detail))

        self.duplicates = duplicates
        self.extras = extras
        self.missing = missing


class LayoutTeamsException(MismatchException[TLA]):
    """
    An exception that occurs when there are duplicate, extra or missing
    teams in a layout.
    """

    def __init__(
        self,
        duplicate_teams: Iterable[TLA],
        extra_teams: Iterable[TLA],
        missing_teams: Iterable[TLA],
    ):
        tpl = "Duplicate, extra or missing teams in the layout! ({0})"
        super().__init__(tpl, duplicate_teams, extra_teams, missing_teams)


class ShepherdingAreasException(MismatchException[str]):
    """
    An exception that occurs when there are duplicate, extra or missing
    shepherding areas in the staging times.
    """

    def __init__(
        self,
        where: str,
        duplicate: Iterable[str],
        extra: Iterable[str],
        missing: Iterable[str],
    ):
        tpl = f"Duplicate, extra or missing shepherding areas {where}! ({{0}})"
        super().__init__(tpl, duplicate, extra, missing)


class Venue:
    """A class providing information about the layout within the venue."""

    @staticmethod
    def _check_staging_times(
        shepherding_areas: Iterable[ShepherdName],
        staging_times: StagingOffsets,
    ) -> None:
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
    def _get_duplicates(items: Iterable[T]) -> list[T]:
        return [item for item, count in Counter(items).items() if count > 1]

    @classmethod
    def check_teams(cls, teams: Iterable[TLA], teams_layout: list[RegionData]) -> None:
        """
        Check that the given layout of teams contains the same set of
        teams as the reference.

        Will throw a :class:`LayoutTeamsException` if there are any
        missing, extra or duplicate teams found.

        :param list teams: The reference list of teams in the competition.
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

    @staticmethod
    def _match_regions_and_shepherds(
        shepherds: Iterable[ShepherdData],
        teams_layout: list[RegionData],
    ) -> Iterable[tuple[RegionData, ShepherdData]]:
        regions_by_name = {r['name']: r for r in teams_layout}

        for shepherd in shepherds:
            for region_name in shepherd.get('regions', []):
                region = regions_by_name.get(region_name)
                if not region:
                    raise InvalidRegionException(region_name, shepherd['name'])

                yield region, shepherd

    @staticmethod
    def _build_locations(
        regions_and_shepherds: Iterable[tuple[RegionData, ShepherdData]],
    ) -> Mapping[RegionName, Region]:

        return {
            region['name']: Region({
                'name': region['name'],
                'display_name': region['display_name'],
                'description': region.get('description', ""),
                'teams': region['teams'],
                'shepherds': ShepherdingArea({
                    'name': shepherd['name'],
                    'colour': shepherd['colour'],
                }),
            })
            for region, shepherd in regions_and_shepherds
        }

    def __init__(
        self,
        teams: Iterable[TLA],
        layout_file: Path,
        shepherding_file: Path,
    ):

        layout_data: LayoutData = yaml_loader.load(layout_file)
        teams_layout = layout_data['teams']
        self.check_teams(teams, teams_layout)

        shepherding_data: ShepherdingData = yaml_loader.load(shepherding_file)
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

        self.locations = self._build_locations(
            self._match_regions_and_shepherds(shepherds, teams_layout),
        )
        """
        A :class:`dict` of location names (from the layout file) to location
        information, including which teams are in that location and the
        shepherding region which contains that location.
        """

        self._team_locations: dict[TLA, Region] = {}

        for location in self.locations.values():
            for team in location['teams']:
                self._team_locations[team] = location

    def check_staging_times(self, staging_times: StagingOffsets) -> None:
        self._check_staging_times(self._shepherding_areas, staging_times)

    def get_team_location(self, team: TLA) -> RegionName:
        """
        Get the name of the location allocated to the given team within
        the venue.

        :param str team: The TLA of the team in question.
        :returns: The name of the location allocated to the team.
        """

        return self._team_locations[team]['name']
