# Copyright (C) 2014 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import heapq
import itertools

__all__ = ["RangeSet"]


class RangeSet(object):
    """A RangeSet represents a set of nonoverlapping ranges on the
  integers (ie, a set of integers, but efficient when the set contains
  lots of runs."""

    def __init__(self, data=None):
        self.monotonic = False
        if isinstance(data, str):
            self._parse_internal(data)
        elif data:
            assert len(data) % 2 == 0
            self.data = tuple(self._remove_pairs(data))
            self.monotonic = all(x < y for x, y in zip(self.data, self.data[1:]))
        else:
            self.data = ()

    def __iter__(self):
        for i in range(0, len(self.data), 2):
            yield self.data[i:i + 2]

    def __eq__(self, other):
        return self.data == other.data

    def __ne__(self, other):
        return self.data != other.data

    def __nonzero__(self):
        return bool(self.data)

    def __str__(self):
        if not self.data:
            return "empty"
        else:
            return self.to_string()

    def __repr__(self):
        return '<RangeSet("' + self.to_string() + '")>'

    @classmethod
    def parse(cls, text):
        """Parse a text string consisting of a space-separated list of
    blocks and ranges, eg "10-20 30 35-40".  Ranges are interpreted to
    include both their ends (so the above example represents 18
    individual blocks.  Returns a RangeSet object.

    If the input has all its blocks in increasing order, then returned
    RangeSet will have an extra attribute 'monotonic' that is set to
    True.  For example the input "10-20 30" is monotonic, but the input
    "15-20 30 10-14" is not, even though they represent the same set
    of blocks (and the two RangeSets will compare equal with ==).
    """
        return cls(text)

    def _parse_internal(self, text):
        data = []
        last = -1
        monotonic = True
        for p in text.split():
            if "-" in p:
                s, e = (int(x) for x in p.split("-"))
                data.append(s)
                data.append(e + 1)
                if last <= s <= e:
                    last = e
                else:
                    monotonic = False
            else:
                s = int(p)
                data.append(s)
                data.append(s + 1)
                if last <= s:
                    last = s + 1
                else:
                    monotonic = False
        data.sort()
        self.data = tuple(self._remove_pairs(data))
        self.monotonic = monotonic

    @staticmethod
    def _remove_pairs(source):
        """Remove consecutive duplicate items to simplify the result.

    [1, 2, 2, 5, 5, 10] will become [1, 10]."""
        last = None
        for i in source:
            if i == last:
                last = None
            else:
                if last is not None:
                    yield last
                last = i
        if last is not None:
            yield last

    def to_string(self):
        out = []
        for i in range(0, len(self.data), 2):
            s, e = self.data[i:i + 2]
            if e == s + 1:
                out.append(str(s))
            else:
                out.append(str(s) + "-" + str(e - 1))
        return " ".join(out)

    def to_string_raw(self):
        assert self.data
        return str(len(self.data)) + "," + ",".join(str(i) for i in self.data)

    def union(self, other):
        """Return a new RangeSet representing the union of this RangeSet
    with the argument.

    >>> RangeSet("10-19 30-34").union(RangeSet("18-29"))
    <RangeSet("10-34")>
    >>> RangeSet("10-19 30-34").union(RangeSet("22 32"))
    <RangeSet("10-19 22 30-34")>
    """
        out = []
        z = 0
        for p, d in heapq.merge(zip(self.data, itertools.cycle((+1, -1))),
                                zip(other.data, itertools.cycle((+1, -1)))):
            if (z == 0 and d == 1) or (z == 1 and d == -1):
                out.append(p)
            z += d
        return RangeSet(data=out)

    def intersect(self, other):
        """Return a new RangeSet representing the intersection of this
    RangeSet with the argument.

    >>> RangeSet("10-19 30-34").intersect(RangeSet("18-32"))
    <RangeSet("18-19 30-32")>
    >>> RangeSet("10-19 30-34").intersect(RangeSet("22-28"))
    <RangeSet("")>
    """
        out = []
        z = 0
        for p, d in heapq.merge(zip(self.data, itertools.cycle((+1, -1))),
                                zip(other.data, itertools.cycle((+1, -1)))):
            if (z == 1 and d == 1) or (z == 2 and d == -1):
                out.append(p)
            z += d
        return RangeSet(data=out)

    def subtract(self, other):
        """Return a new RangeSet representing subtracting the argument
    from this RangeSet.

    >>> RangeSet("10-19 30-34").subtract(RangeSet("18-32"))
    <RangeSet("10-17 33-34")>
    >>> RangeSet("10-19 30-34").subtract(RangeSet("22-28"))
    <RangeSet("10-19 30-34")>
    """

        out = []
        z = 0
        for p, d in heapq.merge(zip(self.data, itertools.cycle((+1, -1))),
                                zip(other.data, itertools.cycle((-1, +1)))):
            if (z == 0 and d == 1) or (z == 1 and d == -1):
                out.append(p)
            z += d
        return RangeSet(data=out)

    def overlaps(self, other):
        """Returns true if the argument has a nonempty overlap with this
    RangeSet.

    >>> RangeSet("10-19 30-34").overlaps(RangeSet("18-32"))
    True
    >>> RangeSet("10-19 30-34").overlaps(RangeSet("22-28"))
    False
    """

        # This is like intersect, but we can stop as soon as we discover the
        # output is going to be nonempty.
        z = 0
        for _, d in heapq.merge(zip(self.data, itertools.cycle((+1, -1))),
                                zip(other.data, itertools.cycle((+1, -1)))):
            if (z == 1 and d == 1) or (z == 2 and d == -1):
                return True
            z += d
        return False

    def size(self):
        """Returns the total size of the RangeSet (ie, how many integers
    are in the set).

    >>> RangeSet("10-19 30-34").size()
    15
    """

        total = 0
        for i, p in enumerate(self.data):
            if i % 2:
                total += p
            else:
                total -= p
        return total

    def map_within(self, other):
        """'other' should be a subset of 'self'.  Returns a RangeSet
    representing what 'other' would get translated to if the integers
    of 'self' were translated down to be contiguous starting at zero.

    >>> RangeSet("0-9").map_within(RangeSet("3-4"))
    <RangeSet("3-4")>
    >>> RangeSet("10-19").map_within(RangeSet("13-14"))
    <RangeSet("3-4")>
    >>> RangeSet("10-19 30-39").map_within(RangeSet("17-19 30-32"))
    <RangeSet("7-12")>
    >>> RangeSet("10-19 30-39").map_within(RangeSet("12-13 17-19 30-32"))
    <RangeSet("2-3 7-12")>
    """

        out = []
        offset = 0
        start = None
        for p, d in heapq.merge(zip(self.data, itertools.cycle((-5, +5))),
                                zip(other.data, itertools.cycle((-1, +1)))):
            if d == -5:
                start = p
            elif d == +5:
                offset += p - start
                start = None
            else:
                out.append(offset + p - start)
        return RangeSet(data=out)

    def extend(self, n):
        """Extend the RangeSet by 'n' blocks.

    The lower bound is guaranteed to be non-negative.

    >>> RangeSet("0-9").extend(1)
    <RangeSet("0-10")>
    >>> RangeSet("10-19").extend(15)
    <RangeSet("0-34")>
    >>> RangeSet("10-19 30-39").extend(4)
    <RangeSet("6-23 26-43")>
    >>> RangeSet("10-19 30-39").extend(10)
    <RangeSet("0-49")>
    """
        out = self
        for i in range(0, len(self.data), 2):
            s, e = self.data[i:i + 2]
            s1 = max(0, s - n)
            e1 = e + n
            out = out.union(RangeSet(str(s1) + "-" + str(e1 - 1)))
        return out

    def first(self, n):
        """Return the RangeSet that contains at most the first 'n' integers.

    >>> RangeSet("0-9").first(1)
    <RangeSet("0")>
    >>> RangeSet("10-19").first(5)
    <RangeSet("10-14")>
    >>> RangeSet("10-19").first(15)
    <RangeSet("10-19")>
    >>> RangeSet("10-19 30-39").first(3)
    <RangeSet("10-12")>
    >>> RangeSet("10-19 30-39").first(15)
    <RangeSet("10-19 30-34")>
    >>> RangeSet("10-19 30-39").first(30)
    <RangeSet("10-19 30-39")>
    >>> RangeSet("0-9").first(0)
    <RangeSet("")>
    """

        if self.size() <= n:
            return self

        out = []
        for s, e in self:
            if e - s >= n:
                out += (s, s + n)
                break
            else:
                out += (s, e)
                n -= e - s
        return RangeSet(data=out)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
