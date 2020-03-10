
from sr.comp.teams import Team

def test_plain():
    t = Team('ABC', "name", rookie = False, dropped_out_after = 4)

    assert not t.rookie
    assert t.is_still_around(3)
    assert t.is_still_around(4)
    assert not t.is_still_around(5)
