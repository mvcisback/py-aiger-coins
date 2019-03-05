import math


# Python is deprecating fractions.gcd....
# https://stackoverflow.com/questions/147515/least-common-multiple-for-3-or-more-numbers/147539#147539  # noqa: E501
def lcm(a, b):
    """Return lowest common multiple."""
    return a * b // math.gcd(a, b)
