
import os
import datetime

from nose.plugins.skip import SkipTest

from sr.comp.comp import SRComp

DUMMY_PATH = os.path.dirname(os.path.abspath(__file__)) + '/dummy'

# Only instantiate SRComp once: it is a slow process!
instance = None

def test_load():
    "Test that loading the dummy state works"
    global instance
    instance = SRComp(DUMMY_PATH)
    assert instance.root
    assert instance.state
    assert instance.teams
    assert instance.schedule
    assert instance.scores
    assert instance.arenas
    assert instance.corners
    assert isinstance(instance.awards, dict)

def test_timezone():
    # Test that one can get the timezone from the dummy state
    global instance
    if instance is None:
        raise SkipTest("Timezone test skipped due to srcomp load failure.")
    assert (
        instance.timezone.utcoffset(datetime.datetime(2014, 4, 26)) ==
        datetime.timedelta(seconds=3600)
    )
