"""Core competition functions."""

from __future__ import annotations

import runpy
import sys
import warnings
from copy import copy
from pathlib import Path
from subprocess import check_output
from typing import Any, cast

from . import arenas, matches, ranker, scores, teams, venue
from .types import CalcRankedPointsHook, ScorerType
from .winners import compute_awards


def load_scorer(root: Path) -> ScorerType:
    """
    Load the scorer module from Compstate repo.

    :param Path root: The path to the compstate repo.
    """

    # Deep path hacks
    score_directory = root / 'scoring'
    score_source = score_directory / 'score.py'

    saved_path = copy(sys.path)
    sys.path.insert(0, str(score_directory))

    try:
        score = runpy.run_path(str(score_source))
    finally:
        sys.path = saved_path

    return cast(ScorerType, score['Scorer'])


def load_ranker(root: Path) -> CalcRankedPointsHook:
    """
    Load the ranker module from Compstate repo.

    :param Path root: The path to the compstate repo.
    """

    # Deep path hacks
    score_directory = root / 'scoring'
    ranker_source = score_directory / 'ranker.py'

    if not ranker_source.exists():
        # By default we support using the `league-ranker` package without
        # modifications.
        return ranker.default_calc_ranked_points

    saved_path = copy(sys.path)
    sys.path.insert(0, str(score_directory))

    try:
        ranker_module_dict: dict[str, Any]
        ranker_module_dict = runpy.run_path(str(ranker_source))
    finally:
        sys.path = saved_path

    if 'calc_positions' in ranker_module_dict:
        warnings.warn(
            (
                f"{ranker_source} has unexpected member "
                "'calc_positions'. This attribute may become part of the API in "
                "future. Consider using a different attribute name."
            ),
            FutureWarning,
            stacklevel=3,
        )

    calc_ranked_points: CalcRankedPointsHook = ranker_module_dict['calc_ranked_points']

    return calc_ranked_points


class SRComp:
    """
    A class containing all the various parts of a competition.

    :param Path root: The root path of the ``compstate`` repo.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

        self.state = check_output(
            ('git', 'rev-parse', 'HEAD'),
            text=True,
            cwd=str(self.root),
        ).strip()
        """The current commit of the Compstate repository."""

        self.teams = teams.load_teams(self.root / 'teams.yaml')
        """A mapping of TLAs to :class:`sr.comp.teams.Team` objects."""

        self.arenas = arenas.load_arenas(self.root / 'arenas.yaml')
        """A :class:`collections.OrderedDict` mapping arena names to
        :class:`sr.comp.arenas.Arena` objects."""

        self.corners = arenas.load_corners(self.root / 'arenas.yaml')
        """A :class:`collections.OrderedDict` mapping corner numbers to
        :class:`sr.comp.arenas.Corner` objects."""

        self.num_teams_per_arena = len(self.corners)

        scorer = load_scorer(self.root)
        ranker = load_ranker(self.root)
        self.scores = scores.Scores.load(
            self.root,
            self.teams.keys(),
            scorer,
            ranker,
            self.num_teams_per_arena,
        )
        """A :class:`sr.comp.scores.Scores` instance."""

        self.schedule = matches.MatchSchedule.create(
            self.root / 'schedule.yaml',
            self.root / 'league.yaml',
            self.scores,
            self.arenas,
            self.num_teams_per_arena,
            self.teams,
        )
        """A :class:`sr.comp.matches.MatchSchedule` instance."""

        self.timezone = self.schedule.timezone
        """The timezone of the competition."""

        self.awards = compute_awards(
            self.scores,
            self.schedule.final_match,
            self.teams,
            self.root / 'awards.yaml',
        )
        """A :class:`dict` mapping :class:`sr.comp.winners.Award` objects to
        a :class:`list` of teams."""

        self.venue = venue.Venue(
            self.teams.keys(),
            self.root / 'layout.yaml',
            self.root / 'shepherding.yaml',
        )
        """A :class:`sr.comp.venue.Venue` instance."""

        self.venue.check_staging_times(self.schedule.staging_times)
