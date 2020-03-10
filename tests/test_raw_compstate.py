
import os.path
import subprocess

from sr.comp.comp import SRComp
from sr.comp.match_period import Match, MatchType
from sr.comp.raw_compstate import RawCompstate


DUMMY_PATH = os.path.dirname(os.path.abspath(__file__)) + '/dummy'


def build_match(num, arena, teams = None, start_time = None, \
                end_time = None, type_ = None, use_resolved_ranking = False):
    return Match(num, "Match {n}".format(n=num), arena, teams,
                 start_time, end_time, type_, use_resolved_ranking)


def test_load():
    state = RawCompstate(DUMMY_PATH, local_only=True)
    comp = state.load()
    assert isinstance(comp, SRComp)


def test_get_score_path():
    m = build_match(0, 'A', type_=MatchType.league)
    state = RawCompstate(DUMMY_PATH, local_only=True)
    path = state.get_score_path(m)
    assert os.path.exists(path), "Path expected to exist within dummy state"


def test_load_score():
    m = build_match(0, 'A', type_=MatchType.league)
    state = RawCompstate(DUMMY_PATH, local_only=True)
    score = state.load_score(m)

    assert score['arena_id'] == 'A', score
    assert score['match_number'] == 0, score

    teams = list(sorted(score['teams'].keys()))
    expected = ['CLY', 'TTN']
    assert expected == teams, score



def test_load_shepherds():
    state = RawCompstate(DUMMY_PATH, local_only=True)
    shepherds = state.load_shepherds()

    expected = [
        {'name': 'Blue',
         'colour': '#A9A9F5',
         'regions': ['a-group'],
         'teams': ['BAY', 'BDF', 'BGS', 'BPV', 'BRK', 'BRN', 'BWS', \
                   'CCR', 'CGS', 'CLF', 'CLY', 'CPR', 'CRB', 'DSF', \
                   'EMM', 'GRD', 'GRS', 'GYG', 'HRS', 'HSO', 'HYP', \
                   'HZW', 'ICE', 'JMS', 'KDE', 'KES', 'KHS', 'LFG'],
        },
        {'name': 'Green',
         'colour': 'green',
         'regions': ['b-group'],
         'teams': ['LSS', 'MAI', 'MAI2', 'MEA', 'MFG', 'NHS', 'PAG', \
                   'PAS', 'PSC', 'QEH', 'QMC', 'QMS', 'RED', 'RGS', \
                   'RUN', 'RWD', 'SCC', 'SEN', 'SGS', 'STA', 'SWI', \
                   'TBG', 'TTN', 'TWG', 'WYC'],
        }
    ]

    assert expected == shepherds, "Wrong shepherds data loaded"


def test_shepherding():
    state = RawCompstate(DUMMY_PATH, local_only=True)
    assert state.shepherding


def test_layout():
    state = RawCompstate(DUMMY_PATH, local_only=True)
    assert state.layout


def test_contains_HEAD():
    state = RawCompstate(DUMMY_PATH, local_only=True)

    has_HEAD = state.has_commit('HEAD')
    assert has_HEAD, "Should have HEAD commit!"


def test_git_return_output():
    state = RawCompstate(DUMMY_PATH, local_only=True)

    output = state.git(['show'], return_output=True)

    assert output.startswith('commit '), output


def test_git_no_return_output():
    state = RawCompstate(DUMMY_PATH, local_only=True)

    output = state.git(['rev-parse', 'HEAD'])

    assert output == 0, "Should succeed and return exit code"


def test_git_return_output_when_error():
    state = RawCompstate(DUMMY_PATH, local_only=True)

    try:
        output = state.git(['this-is-not-a-valid-command'], return_output=True)
    except subprocess.CalledProcessError:
        pass
    else:
        msg = "Should have errored about bad command (returned '{0}').".format(output)
        raise AssertionError(msg)


def test_git_when_error():
    state = RawCompstate(DUMMY_PATH, local_only=True)

    try:
        output = state.git(['this-is-not-a-valid-command'])
    except subprocess.CalledProcessError:
        pass
    else:
        msg = "Should have errored about bad command (returned '{0}').".format(output)
        raise AssertionError(msg)


def test_git_converts_error():
    state = RawCompstate(DUMMY_PATH, local_only=True)
    error_msg = "Our message that something went wrong"

    try:
        output = state.git(['this-is-not-a-valid-command'], err_msg=error_msg)
    except RuntimeError as re:
        assert error_msg in str(re)
    else:
        msg = "Should have errored about bad command (returned '{0}').".format(output)
        raise AssertionError(msg)
