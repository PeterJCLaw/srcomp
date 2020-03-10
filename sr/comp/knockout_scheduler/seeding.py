import math


def bit_mask(n):
    """Return an n-bit mask of 1's."""

    return 2 ** n - 1


def reverse_bits(n, width):
    """Reverse the bits of ``n``."""

    b = '{:0{width}b}'.format(n, width=width)
    return int(b[::-1], 2)


def first_round_seeding(n_teams):
    """
    Return the seed arrangement for the first round of a knockout with
    ``n_teams`` at 4 teams per match.

    :param int n_teams: The number of teams.
    :return: A list of matches.
    """

    # Round the number of teams up to a power of two
    rounded_teams = int(2 ** math.ceil(math.log(n_teams, 2)))

    n_per_match = 4
    n_matches = int(math.ceil(float(rounded_teams) / n_per_match))
    matches_bits = int(math.ceil(math.log(n_matches, 2)))

    # Find the order in which we repeatedly insert teams into the
    # match list.
    # The pattern in the insertion offsets is:
    #  - Even offset: Bitwise reversal of the offset in the offset table
    #  -  Odd offset: Complement of the previous number
    # Derived using a similar approach to this website:
    # http://blogs.popart.com/2012/02/things-only-mathematicians-can-get-excited-about/
    # but for matches with 4 teams in.
    ins_order = []
    for n in range(n_matches):
        if n % 2 == 0:
            # Even
            v = reverse_bits(n, matches_bits)
        else:
            # Odd
            v ^= bit_mask(matches_bits)
        ins_order.append(v)

    matches = []
    for n in range(n_matches):
        matches += [[]]

    for n in range(n_teams):
        matches[ins_order[n % n_matches]].append(n)

    return matches
