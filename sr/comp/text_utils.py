from collections.abc import Iterable


def join_and(items: Iterable[object]) -> str:
    """
    Produce a mostly comma-separated list, with the last conjunction being "and"
    rather than a comma.

    >>> join_and(["spam", "eggs", "ham"])
    "spam, eggs and ham"
    """
    strings = [str(x) for x in items]
    if not strings:
        return ""

    if len(strings) == 1:
        return strings[0]

    *rest, last = strings

    return " and ".join((", ".join(rest), last))
