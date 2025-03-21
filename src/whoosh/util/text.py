# Copyright 2007 Matt Chaput. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY MATT CHAPUT ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL MATT CHAPUT OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of Matt Chaput.

from __future__ import annotations

import codecs
import re
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

# Note: these functions return a tuple of (text, length), so when you call
# them, you have to add [0] on the end, e.g. str = utf8encode(unicode)[0]

utf8encode = codecs.getencoder("utf-8")
utf8decode = codecs.getdecoder("utf-8")


# Prefix encoding functions


def byte(num: int) -> bytes:
    return bytes((num,))


_T = TypeVar("_T")


def first_diff(a: Sequence[_T], b: Sequence[_T]) -> int:
    """
    Returns the position of the first differing character in the sequences a
    and b. For example, first_diff('render', 'rending') == 4. This function
    limits the return value to 255 so the difference can be encoded in a single
    byte.
    """

    i = 0
    while i <= 255 and i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return i


def prefix_encode(a: bytes, b: bytes) -> bytes:
    """
    Compresses bytestring b as a byte representing the prefix it shares with a,
    followed by the suffix bytes.
    """

    i = first_diff(a, b)
    return byte(i) + b[i:]


def prefix_encode_all(ls: Sequence[str]) -> Generator[str]:
    """Compresses the given list of (unicode) strings by storing each string
    (except the first one) as an integer (encoded in a byte) representing
    the prefix it shares with its predecessor, followed by the suffix encoded
    as UTF-8.
    """

    last = ""
    for w in ls:
        i = first_diff(last, w)
        yield chr(i) + w[i:]
        last = w


def prefix_decode_all(ls: Sequence[str]):
    """Decompresses a list of strings compressed by prefix_encode()."""

    last = ""
    for w in ls:
        i = ord(w[0])
        decoded = last[:i] + w[1:]
        yield decoded
        last = decoded


# Natural key sorting function

_nkre = re.compile(r"\D+|\d+", re.UNICODE)


def _nkconv(i: str) -> str | int:
    try:
        return int(i)
    except ValueError:
        return i.lower()


def natural_key(s: str) -> tuple[str | int, ...]:
    """Converts string ``s`` into a tuple that will sort "naturally" (i.e.,
    ``name5`` will come before ``name10`` and ``1`` will come before ``A``).
    This function is designed to be used as the ``key`` argument to sorting
    functions.

    :param s: the str/unicode string to convert.
    :rtype: tuple
    """

    # Use _nkre to split the input string into a sequence of
    # digit runs and non-digit runs. Then use _nkconv() to convert
    # the digit runs into ints and the non-digit runs to lowercase.
    return tuple(_nkconv(m) for m in _nkre.findall(s))


# Regular expression functions


def rcompile(
    pattern: str | re.Pattern[str], flags: int = 0, verbose: bool = False
) -> re.Pattern[str]:
    """A wrapper for re.compile that checks whether "pattern" is a regex object
    or a string to be compiled, and automatically adds the re.UNICODE flag.
    """

    if isinstance(pattern, re.Pattern):
        # If it's not a string, assume it's already a compiled pattern
        return pattern
    if verbose:
        flags |= re.VERBOSE
    return re.compile(pattern, re.UNICODE | flags)
