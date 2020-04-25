"""Core competition functions."""

import imp
import os
import sys
from copy import copy
from subprocess import check_output
from typing import cast

from . import arenas, matches, scores, teams, venue
from .types import ScorerType
from .winners import compute_awards


def load_scorer(root: str) -> ScorerType:
    """
    Load the scorer module from Compstate repo.

    :param str root: The path to the compstate repo.
    """

    # Deep path hacks
    score_directory = os.path.join(root, 'scoring')
    score_source = os.path.join(score_directory, 'score.py')

    saved_path = copy(sys.path)
    sys.path.append(score_directory)

    imported_library = imp.load_source('score.py', score_source)

    sys.path = saved_path

    scorer = imported_library.Scorer  # type: ignore[attr-defined]
    return cast(ScorerType, scorer)


class SRComp:
    """
    A class containing all the various parts of a competition.

    :param str root: The root path of the ``compstate`` repo.
    """

    def __init__(self, root: str) -> None:
        self.root = root

        self.state = check_output(
            ('git', 'rev-parse', 'HEAD'),
            universal_newlines=True,
            cwd=root,
        ).strip()
        """The current commit of the Compstate repository."""

        self.teams = teams.load_teams(os.path.join(root, 'teams.yaml'))
        """A mapping of TLAs to :class:`sr.comp.teams.Team` objects."""

        self.arenas = arenas.load_arenas(os.path.join(root, 'arenas.yaml'))
        """A :class:`collections.OrderedDict` mapping arena names to
        :class:`sr.comp.arenas.Arena` objects."""

        self.corners = arenas.load_corners(os.path.join(root, 'arenas.yaml'))
        """A :class:`collections.OrderedDict` mapping corner numbers to
        :class:`sr.comp.arenas.Corner` objects."""

        self.num_teams_per_arena = len(self.corners)

        scorer = load_scorer(root)
        self.scores = scores.Scores(
            root,
            self.teams.keys(),
            scorer,
            self.num_teams_per_arena,
        )
        """A :class:`sr.comp.scores.Scores` instance."""

        schedule_fname = os.path.join(root, 'schedule.yaml')
        league_fname = os.path.join(root, 'league.yaml')
        self.schedule = matches.MatchSchedule.create(
            schedule_fname,
            league_fname,
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
            os.path.join(root, 'awards.yaml'),
        )
        """A :class:`dict` mapping :class:`sr.comp.winners.Award` objects to
        a :class:`list` of teams."""

        self.venue = venue.Venue(
            self.teams.keys(),
            os.path.join(root, 'layout.yaml'),
            os.path.join(root, 'shepherding.yaml'),
        )
        """A :class:`sr.comp.venue.Venue` instance."""

        self.venue.check_staging_times(self.schedule.staging_times)
