from collections import defaultdict
from datetime import datetime, timedelta

from sr.comp.match_period import Match
from sr.comp.matches import MatchSchedule, parse_ranges
from sr.comp.teams import Team


def assert_times(expected, matches, message):
    def times(dts):
        return [dt.strftime("%H:%M") for dt in dts]

    starts = [m['A'].start_time for m in matches]
    expected_times = times(expected)
    start_times = times(starts)

    # Times alone are easier to debug
    assert expected_times == start_times, message + " (times)"

    assert expected == starts, message + " (datetimes)"


def get_basic_data():
    the_data = {
        'match_slot_lengths': {
            'pre': 90,
            'match': 180,
            'post': 30,
            'total': 300,
        },
        'staging': {
            'opens': 300,
            'closes': 120,
            'duration': 180,
            'signal_shepherds': {
                'Blue': 241,
                'Green': 181,
            },
            'signal_teams': 240,
        },
        'delays': [{
            'delay': 15,
            'time': datetime(2014, 3, 26, 13, 2),
        }],
        'match_periods': {
            'league': [{
                'description': "A description of the period",
                'start_time':   datetime(2014, 3, 26, 13),  # noqa:E241
                'end_time':     datetime(2014, 3, 26, 17, 30),  # noqa:E241
                'max_end_time': datetime(2014, 3, 26, 17, 40, 0),  # noqa:E241
            }],
            'knockout': [],
        },
        'league': {'extra_spacing': []},
        'matches': {
            0: {
                'A': ['CLY', 'TTN', 'SCC', 'DSF'],
                'B': ['GRS', 'QMC', 'GRD', 'BRK'],
            },
            1: {
                'A': ['WYC', 'QMS', 'LSS', 'EMM'],
                'B': ['BPV', 'BDF', 'NHS', 'MEA'],
            },
            2: {
                'A': ['WYC', 'QMS', 'LSS', 'EMM'],
            },
        },
    }
    return the_data


def load_data(the_data):
    teams = defaultdict(lambda: Team(None, None, False, None))
    teams['WYC'] = Team(None, None, False, 1)  # dropped out after match 1

    matches = MatchSchedule(
        the_data,
        the_data['matches'],
        teams,
        num_teams_per_arena=4,
    )
    return matches


def load_basic_data():
    matches = load_data(get_basic_data())
    assert len(matches.match_periods) == 1
    assert len(matches.matches) == 3
    return matches


def test_basic_data():
    matches = load_basic_data()

    first = matches.matches[0]
    assert len(first) == 2
    assert 'A' in first
    assert 'B' in first

    a = first['A']
    b = first['B']

    a_start = a.start_time
    b_start = b.start_time
    assert a_start == datetime(2014, 3, 26, 13)
    assert a_start == b_start

    a_end = a.end_time
    b_end = b.end_time
    assert a_end == datetime(2014, 3, 26, 13, 5)
    assert a_end == b_end

    expected_staging = {
        'opens': timedelta(seconds=300),
        'closes': timedelta(seconds=120),
        'duration': timedelta(seconds=180),
        'signal_shepherds': {
            'Blue': timedelta(seconds=241),
            'Green': timedelta(seconds=181),
        },
        'signal_teams': timedelta(seconds=240),
    }

    staging_times = matches.staging_times

    assert expected_staging == staging_times, "Wrong values loaded from state"


def test_get_staging_times():
    start = datetime(2014, 3, 26, 13, 0, 0)
    match = Match(0, None, 'A', [], start, None, None, None)

    matches = load_basic_data()

    staging_times = matches.get_staging_times(match)

    expected = {
        'opens':            datetime(2014, 3, 26, 12, 56, 30),  # noqa:E241
        'closes':           datetime(2014, 3, 26, 12, 59, 30),  # noqa:E241
        'duration':         timedelta(seconds=180),  # noqa:E241
        'signal_shepherds': {
            'Blue': datetime(2014, 3, 26, 12, 57, 29),
            'Green': datetime(2014, 3, 26, 12, 58, 29),
        },
        'signal_teams':     datetime(2014, 3, 26, 12, 57, 30),  # noqa:E241
    }

    assert expected == staging_times, "Wrong staging times for given match"


def test_extra_spacing_no_delays():
    the_data = get_basic_data()

    the_data['league']['extra_spacing'] = [{
        'match_numbers': '1',
        'duration': 30,
    }]
    the_data['delays'] = []

    matches = load_data(the_data)

    first_a = matches.matches[0]['A']
    first_b = matches.matches[0]['B']
    a_start = first_a.start_time
    b_start = first_b.start_time
    assert a_start == datetime(2014, 3, 26, 13)
    assert a_start == b_start

    second_a = matches.matches[1]['A']
    second_b = matches.matches[1]['B']
    a_start = second_a.start_time
    b_start = second_b.start_time
    assert a_start == datetime(2014, 3, 26, 13, 5, 30)
    assert a_start == b_start

    third_a = matches.matches[2]['A']
    a_start = third_a.start_time
    assert a_start == datetime(2014, 3, 26, 13, 10, 30)


def test_extra_spacing_first_match():
    the_data = get_basic_data()

    the_data['league']['extra_spacing'] = [{
        'match_numbers': '0',
        'duration': 30,
    }]
    the_data['delays'] = []

    matches = load_data(the_data)

    first_a = matches.matches[0]['A']
    first_b = matches.matches[0]['B']
    a_start = first_a.start_time
    b_start = first_b.start_time
    assert a_start == datetime(2014, 3, 26, 13, 0)
    assert a_start == b_start

    second_a = matches.matches[1]['A']
    second_b = matches.matches[1]['B']
    a_start = second_a.start_time
    b_start = second_b.start_time
    assert a_start == datetime(2014, 3, 26, 13, 5)
    assert a_start == b_start

    third_a = matches.matches[2]['A']
    a_start = third_a.start_time
    assert a_start == datetime(2014, 3, 26, 13, 10)


def test_extra_spacing_with_delays():
    the_data = get_basic_data()

    the_data['league']['extra_spacing'] = [{
        'match_numbers': '1',
        'duration': 30,
    }]

    matches = load_data(the_data)

    first_a = matches.matches[0]['A']
    first_b = matches.matches[0]['B']
    a_start = first_a.start_time
    b_start = first_b.start_time
    assert a_start == datetime(2014, 3, 26, 13)
    assert a_start == b_start

    second_a = matches.matches[1]['A']
    second_b = matches.matches[1]['B']
    a_start = second_a.start_time
    b_start = second_b.start_time
    assert a_start == datetime(2014, 3, 26, 13, 5, 45)
    assert a_start == b_start

    third_a = matches.matches[2]['A']
    a_start = third_a.start_time
    assert a_start == datetime(2014, 3, 26, 13, 10, 45)


def test_extra_spacing_overlapping_with_delays():
    the_data = get_basic_data()

    the_data['league']['extra_spacing'] = [{
        'match_numbers': '1',
        'duration': 30,
    }]
    # Inject a delay which occurs during our extra spcing time
    the_data['delays'] = [{
        'delay': 15,
        "time": datetime(2014, 3, 26, 13, 5, 10),
    }]

    matches = load_data(the_data)

    first_a = matches.matches[0]['A']
    first_b = matches.matches[0]['B']
    a_start = first_a.start_time
    b_start = first_b.start_time
    assert a_start == datetime(2014, 3, 26, 13)
    assert a_start == b_start

    second_a = matches.matches[1]['A']
    second_b = matches.matches[1]['B']
    a_start = second_a.start_time
    b_start = second_b.start_time
    assert a_start == datetime(2014, 3, 26, 13, 5, 45)
    assert a_start == b_start

    third_a = matches.matches[2]['A']
    a_start = third_a.start_time
    assert a_start == datetime(2014, 3, 26, 13, 10, 45)


def test_dropped_out_team():
    matches = load_basic_data()

    match = matches.matches[1]
    assert match['A'].teams == ['WYC', 'QMS', 'LSS', 'EMM']

    match = matches.matches[2]
    assert match['A'].teams == [None, 'QMS', 'LSS', 'EMM']


def test_period_at_start_time():
    match_sched = load_basic_data()

    when = datetime(2014, 3, 26, 13)
    period = match_sched.period_at(when)

    expected = match_sched.match_periods[0]

    assert period == expected


def test_period_between_max_and_end_time():
    match_sched = load_basic_data()

    # end time is 17:30, max_end is 17:40
    when = datetime(2014, 3, 26, 17, 35)
    period = match_sched.period_at(when)

    expected = match_sched.match_periods[0]

    assert period == expected


def test_no_period_at_max_end_time():
    match_sched = load_basic_data()

    # end time is 17:30, max_end is 17:40
    when = datetime(2014, 3, 26, 17, 40)
    period = match_sched.period_at(when)

    assert period is None


def test_no_period_at_time():
    match_sched = load_basic_data()

    when = datetime(2013, 3, 26)
    period = match_sched.period_at(when)

    assert period is None


def test_matches_at_no_delays():
    the_data = get_basic_data()

    the_data['delays'] = []

    matches = load_data(the_data)

    def check(expected, when):
        actual = list(matches.matches_at(when))
        assert expected == actual

    def match_list(num):
        return list(matches.matches[num].values())

    yield check, [],            datetime(2014, 3, 26, 12, 59, 59)  # noqa:E241

    yield check, match_list(0), datetime(2014, 3, 26, 13)
    yield check, match_list(0), datetime(2014, 3, 26, 13, 4, 59)

    yield check, match_list(1), datetime(2014, 3, 26, 13, 5)
    yield check, match_list(1), datetime(2014, 3, 26, 13, 9, 59)

    yield check, match_list(2), datetime(2014, 3, 26, 13, 10)
    yield check, match_list(2), datetime(2014, 3, 26, 13, 14, 59)

    yield check, [],            datetime(2014, 3, 26, 13, 15)  # noqa:E241


def test_matches_at_with_delays():
    matches = load_basic_data()

    def check(expected, when):
        actual = list(matches.matches_at(when))
        assert expected == actual

    def match_list(num):
        return list(matches.matches[num].values())

    yield check, match_list(0), datetime(2014, 3, 26, 13)
    yield check, match_list(0), datetime(2014, 3, 26, 13, 4, 59)

    yield check, [],            datetime(2014, 3, 26, 13, 5, 14)  # noqa:E241

    yield check, match_list(1), datetime(2014, 3, 26, 13, 5, 15)
    yield check, match_list(1), datetime(2014, 3, 26, 13, 10, 14)

    yield check, match_list(2), datetime(2014, 3, 26, 13, 10, 15)
    yield check, match_list(2), datetime(2014, 3, 26, 13, 15, 14)

    yield check, [],            datetime(2014, 3, 26, 13, 15, 15)  # noqa:E241


def test_no_matches():
    the_data = get_basic_data()
    the_data['matches'] = None
    matches = load_data(the_data)

    assert matches, "Should have at least loaded the data"

    n_matches = matches.n_matches()
    assert n_matches == 0, "Number actually scheduled"

    n_planned_matches = matches.n_planned_league_matches
    assert n_planned_matches == 0, "Number originally planned for the league"

    n_league_matches = matches.n_league_matches
    assert n_league_matches == 0, "Number actually scheduled for the league"


def test_delay_at_no_period():
    match_sched = load_basic_data()

    when = datetime(2013, 3, 26)
    delay = match_sched.delay_at(when)

    assert delay == timedelta()


def test_delay_at_no_delays():
    the_data = get_basic_data()
    the_data['delays'] = None
    match_sched = load_data(the_data)

    when = datetime(2014, 3, 26, 13, 10)
    delay = match_sched.delay_at(when)

    assert delay == timedelta()


def test_delay_at_before_delays():
    match_sched = load_basic_data()

    when = datetime(2014, 3, 26, 13, 1)
    delay = match_sched.delay_at(when)

    assert delay == timedelta()


def test_delay_at_at_delay_time():
    match_sched = load_basic_data()

    when = datetime(2014, 3, 26, 13, 2)
    delay = match_sched.delay_at(when)

    assert delay == timedelta(seconds=15)


def test_basic_delay():
    matches = load_basic_data()

    second = matches.matches[1]

    a = second['A']
    b = second['B']

    a_start = a.start_time
    b_start = b.start_time
    assert a_start == datetime(2014, 3, 26, 13, 5, 15)
    assert a_start == b_start

    a_end = a.end_time
    b_end = b.end_time
    assert a_end == datetime(2014, 3, 26, 13, 10, 15)
    assert a_end == b_end


def test_no_delays():
    the_data = get_basic_data()
    the_data['delays'] = None
    matches = load_data(the_data)

    first = matches.matches[0]
    assert len(first) == 2
    assert 'A' in first
    assert 'B' in first

    a = first['A']
    b = first['B']

    a_start = a.start_time
    b_start = b.start_time
    assert a_start == datetime(2014, 3, 26, 13)
    assert a_start == b_start

    a_end = a.end_time
    b_end = b.end_time
    assert a_end == datetime(2014, 3, 26, 13, 5)
    assert a_end == b_end


def test_two_overlapping_delays():
    the_data = get_basic_data()
    the_data['delays'] = [
        {'delay': 5 * 60, 'time': datetime(2014, 3, 26, 13, 2)},
        # Second delay 'starts' part-way through the first
        {'delay': 5 * 60, 'time': datetime(2014, 3, 26, 13, 6)},
    ]
    the_data['matches'][3] = {'A': ['SRZ', 'SRZ1', 'SRZ2', 'SRZ3']}
    matches = load_data(the_data)

    expected = [
        datetime(2014, 3, 26, 13, 0),  # first match unaffected by delays
        datetime(2014, 3, 26, 13, 15),  # second match gets both delays
        datetime(2014, 3, 26, 13, 20),
        datetime(2014, 3, 26, 13, 25),
    ]

    assert_times(expected, matches.matches, "Wrong compound match delays")


def test_two_sepearate_delays():
    the_data = get_basic_data()
    the_data['delays'] = [
        {'delay': 5 * 60, 'time': datetime(2014, 3, 26, 13, 2)},
        {'delay': 5 * 60, 'time': datetime(2014, 3, 26, 13, 12)},
    ]
    the_data['matches'][3] = {'A': ['SRZ', 'SRZ1', 'SRZ2', 'SRZ3']}
    matches = load_data(the_data)

    expected = [
        datetime(2014, 3, 26, 13, 0),  # first match unaffected by delays
        datetime(2014, 3, 26, 13, 10),  # second match gets first delay
        datetime(2014, 3, 26, 13, 20),  # third match gets first and second delays
        datetime(2014, 3, 26, 13, 25),  # fourth match gets no extra delays
    ]

    assert_times(expected, matches.matches, "Wrong compound match delays")


def test_period_end_simple():
    the_data = get_basic_data()
    # Don't care about delays for now
    the_data['delays'] = None
    # for a total of 4 matches
    the_data['matches'][3] = {'A': ['SRZ', 'SRZ1', 'SRZ2', 'SRZ3']}

    # Period is 12 minutes long. Since we measure by the start of matches
    # this is enough time to start 3 matches (at 5 minutes each)
    league = the_data['match_periods']['league'][0]
    start_time = league['start_time']
    league['end_time'] = start_time + timedelta(minutes=12)
    del league['max_end_time']

    matches = load_data(the_data)

    expected = [
        start_time,
        start_time + timedelta(minutes=5),
        start_time + timedelta(minutes=10),
    ]

    assert_times(
        expected,
        matches.matches,
        "4 matches planned in a 12 minute period, no delay",
    )


def test_period_end_with_delay():
    the_data = get_basic_data()
    # Simple delay
    the_data['delays'] = [
        {'delay': 60, 'time': datetime(2014, 3, 26, 13, 2)},
    ]
    # for a total of 4 matches
    the_data['matches'][3] = {'A': ['SRZ', 'SRZ1', 'SRZ2', 'SRZ3']}

    # Period is 12 minutes long. Since we measure by the start of matches
    # this is enough time to start 3 matches (at 5 minutes each)
    league = the_data['match_periods']['league'][0]
    start_time = league['start_time']
    league['end_time'] = start_time + timedelta(minutes=12)
    del league['max_end_time']

    matches = load_data(the_data)

    expected = [
        start_time,
        # 5 minute matches, 1 minute delay
        start_time + timedelta(minutes=6),
        start_time + timedelta(minutes=11),
    ]

    assert_times(
        expected,
        matches.matches,
        "4 matches planned in a 12 minute period, simple delay",
    )


def test_period_end_with_large_delay():
    the_data = get_basic_data()
    # Simple delay
    the_data['delays'] = [
        {'delay': 300, 'time': datetime(2014, 3, 26, 13, 1)},
    ]
    # for a total of 4 matches
    the_data['matches'][3] = {'A': ['SRZ', 'SRZ1', 'SRZ2', 'SRZ3']}

    # Period is 12 minutes long. Since we measure by the start of matches
    # this is enough time to start 3 matches (at 5 minutes each)
    league = the_data['match_periods']['league'][0]
    start_time = league['start_time']
    league['end_time'] = start_time + timedelta(minutes=12)
    del league['max_end_time']

    matches = load_data(the_data)

    expected = [
        start_time,
        # 5 minute matches, 5 minute delay
        start_time + timedelta(minutes=10),
    ]

    assert_times(
        expected,
        matches.matches,
        "4 matches planned in a 12 minute period, large delay",
    )


def test_period_max_end_simple():
    the_data = get_basic_data()
    # Don't care about delays for now
    the_data['delays'] = None
    # for a total of 4 matches
    the_data['matches'][3] = {'A': ['SRZ', 'SRZ1', 'SRZ2', 'SRZ3']}

    # Period is 12 minutes long. Since we measure by the start of matches
    # this is enough time to start 3 matches (at 5 minutes each)
    league = the_data['match_periods']['league'][0]
    start_time = league['start_time']
    league['end_time'] = start_time + timedelta(minutes=12)
    # Allow 5 minutes for overrun
    league['max_end_time'] = start_time + timedelta(minutes=17)

    matches = load_data(the_data)

    expected = [
        start_time,
        start_time + timedelta(minutes=5),
        start_time + timedelta(minutes=10),
    ]

    assert_times(
        expected,
        matches.matches,
        "4 matches planned in a 12 minute period, overrun allowed, no delay",
    )


def test_period_max_end_with_delay():
    the_data = get_basic_data()
    # Simple delay
    the_data['delays'] = [
        {'delay': 60, 'time': datetime(2014, 3, 26, 13, 2)},
    ]
    # for a total of 4 matches
    the_data['matches'][3] = {'A': ['SRZ', 'SRZ1', 'SRZ2', 'SRZ3']}

    # Period is 12 minutes long. Since we measure by the start of matches
    # this is enough time to start 3 matches (at 5 minutes each)
    league = the_data['match_periods']['league'][0]
    start_time = league['start_time']
    league['end_time'] = start_time + timedelta(minutes=12)
    # Allow 5 minutes for overrun
    league['max_end_time'] = start_time + timedelta(minutes=17)

    matches = load_data(the_data)

    expected = [
        start_time,
        # 5 minute matches, 1 minute delay
        start_time + timedelta(minutes=6),
        start_time + timedelta(minutes=11),
    ]

    assert_times(
        expected,
        matches.matches,
        "4 matches planned in a 12 minute period, overrun allowed, simple delay",
    )


def test_period_max_end_with_large_delay():
    the_data = get_basic_data()
    # Simple delay
    the_data['delays'] = [
        {'delay': 300, 'time': datetime(2014, 3, 26, 13, 1)},
    ]
    # for a total of 4 matches
    the_data['matches'][3] = {'A': ['SRZ', 'SRZ1', 'SRZ2', 'SRZ3']}

    # Period is 12 minutes long. Since we measure by the start of matches
    # this is enough time to start 3 matches (at 5 minutes each)
    league = the_data['match_periods']['league'][0]
    start_time = league['start_time']
    league['end_time'] = start_time + timedelta(minutes=12)
    # Allow 5 minutes for overrun
    league['max_end_time'] = start_time + timedelta(minutes=17)

    matches = load_data(the_data)

    expected = [
        start_time,
        # 5 minute matches, 5 minute delay
        start_time + timedelta(minutes=10),
        # Third match would have originally been at start+10, so is allowed to occur in the overrun period
        start_time + timedelta(minutes=15),
    ]

    assert_times(
        expected,
        matches.matches,
        "4 matches planned in a 12 minute period, overrun allowed, large delay",
    )


def test_planned_matches():
    the_data = get_basic_data()

    extra_match = {
        'A': ['WYC2', 'QMS2', 'LSS2', 'EMM2'],
        'B': ['BPV2', 'BDF2', 'NHS2', 'MEA2'],
    }
    the_data['matches'][2] = extra_match

    league = the_data['match_periods']['league'][0]
    league['end_time'] = league['start_time'] + timedelta(minutes=10)
    del league['max_end_time']

    matches = load_data(the_data)

    n_matches = matches.n_matches()
    assert n_matches == 2, "Number actually scheduled"

    n_planned_matches = matches.n_planned_league_matches
    assert n_planned_matches == 3, "Number originally planned for the league"

    n_league_matches = matches.n_league_matches
    assert n_league_matches == 2, "Number actually scheduled for the league"


def test_parse_ranges():
    def check(range_str, expected):
        actual = parse_ranges(range_str)
        assert expected == actual, "Wrong ranges parsed"

    yield check, '1', set([1])
    yield check, '1,4', set([1, 4])
    yield check, '1, 4', set([1, 4])
    yield check, '1-4', set([1, 2, 3, 4])
    yield check, '1-4,2-5', set([1, 2, 3, 4, 5])
    yield check, '1-4,6,0', set([0, 1, 2, 3, 4, 6])


def test_parse_bad_ranges():
    def check(range_str):
        try:
            actual = parse_ranges(range_str)
        except:
            pass
        else:
            msg = "Should have errored, got: {0}".format(repr(actual))
            raise AssertionError(msg)

    yield check, ''
    yield check, '1,a'
    yield check, '1--4'
    yield check, '1-,4'
