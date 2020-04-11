"""Classes that are useful for dealing with match periods."""

from collections import namedtuple
from enum import Enum, unique

Delay = namedtuple('Delay', [
    'delay',
    'time',
])


@unique
class MatchType(Enum):
    league = 'league'
    knockout = 'knockout'
    tiebreaker = 'tiebreaker'


Match = namedtuple('Match', [
    'num',
    'display_name',
    'arena',
    'teams',
    'start_time',
    'end_time',
    'type',
    'use_resolved_ranking',
])


class MatchPeriod(namedtuple('MatchPeriod', [
    'start_time',
    'end_time',
    'max_end_time',
    'description',
    'matches',
    'type',
])):

    __slots__ = ()

    def __str__(self):
        return "{} ({}–{})".format(
            self.description,
            self.start_time.strftime('%H:%M'),
            self.end_time.strftime('%H:%M'),
        )
