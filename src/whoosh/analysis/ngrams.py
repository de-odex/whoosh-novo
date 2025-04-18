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

from typing import TYPE_CHECKING, Any, Literal

from whoosh.analysis.acore import Token
from whoosh.analysis.filters import Filter, LowercaseFilter
from whoosh.analysis.tokenizers import RegexTokenizer, Tokenizer

if TYPE_CHECKING:
    from collections.abc import Generator

# Tokenizer


class NgramTokenizer(Tokenizer):
    """Splits input text into N-grams instead of words.

    >>> ngt = NgramTokenizer(4)
    >>> [token.text for token in ngt("hi there")]
    ["hi t", "i th", " the", "ther", "here"]

    Note that this tokenizer does NOT use a regular expression to extract
    words, so the grams emitted by it will contain whitespace, punctuation,
    etc. You may want to massage the input or add a custom filter to this
    tokenizer's output.

    Alternatively, if you only want sub-word grams without whitespace, you
    could combine a RegexTokenizer with NgramFilter instead.
    """

    __inittypes__ = {"minsize": int, "maxsize": int}

    def __init__(self, minsize: int, maxsize: int | None = None):
        """
        :param minsize: The minimum size of the N-grams.
        :param maxsize: The maximum size of the N-grams. If you omit
            this parameter, maxsize == minsize.
        """

        self.min = minsize
        self.max = maxsize or minsize

    def __eq__(self, other: object):
        if isinstance(other, type(self)):
            if self.min == other.min and self.max == other.max:
                return True
        return False

    def __call__(
        self,
        value: str,
        positions: bool = False,
        chars: bool = False,
        keeporiginal: bool = False,
        removestops: bool = True,
        start_pos: int = 0,
        start_char: int = 0,
        mode: str = "",
        **kwargs: Any,
    ) -> Generator[Token]:
        assert isinstance(value, str), f"{value!r} is not unicode"

        inlen = len(value)
        t = Token(positions, chars, removestops=removestops, mode=mode)
        pos = start_pos

        if mode == "query":
            size = min(self.max, inlen)
            for start in range(0, inlen - size + 1):
                end = start + size
                if end > inlen:
                    continue
                t.text = value[start:end]
                if keeporiginal:
                    t.original = t.text
                t.stopped = False
                if positions:
                    t.pos = pos
                if chars:
                    t.startchar = start_char + start
                    t.endchar = start_char + end
                yield t
                pos += 1
        else:
            for start in range(0, inlen - self.min + 1):
                for size in range(self.min, self.max + 1):
                    end = start + size
                    if end > inlen:
                        continue
                    t.text = value[start:end]
                    if keeporiginal:
                        t.original = t.text
                    t.stopped = False
                    if positions:
                        t.pos = pos
                    if chars:
                        t.startchar = start_char + start
                        t.endchar = start_char + end

                    yield t
                pos += 1


# Filter


class NgramFilter(Filter):
    """Splits token text into N-grams.

    >>> rext = RegexTokenizer()
    >>> stream = rext("hello there")
    >>> ngf = NgramFilter(4)
    >>> [token.text for token in ngf(stream)]
    ["hell", "ello", "ther", "here"]
    """

    __inittypes__ = {"minsize": int, "maxsize": int}

    def __init__(
        self,
        minsize: int,
        maxsize: int | None = None,
        at: Literal["start", "end"] | None = None,
    ):
        """
        :param minsize: The minimum size of the N-grams.
        :param maxsize: The maximum size of the N-grams. If you omit this
            parameter, maxsize == minsize.
        :param at: If 'start', only take N-grams from the start of each word.
            if 'end', only take N-grams from the end of each word. Otherwise,
            take all N-grams from the word (the default).
        """

        self.min = minsize
        self.max = maxsize or minsize
        self.at = 0
        if at == "start":
            self.at = -1
        elif at == "end":
            self.at = 1

    def __eq__(self, other: object):
        return (
            other is not None
            and isinstance(other, type(self))
            and self.min == other.min
            and self.max == other.max
        )

    def __call__(self, tokens: Generator[Token]) -> Generator[Token]:
        assert hasattr(tokens, "__iter__")
        at = self.at
        for t in tokens:
            text = t.text
            if len(text) < self.min:
                continue

            chars = t.chars
            if chars:
                startchar = t.startchar
            # Token positions don't mean much for N-grams,
            # so we'll leave the token's original position
            # untouched.

            if t.mode == "query":
                size = min(self.max, len(t.text))
                if at == -1:
                    t.text = text[:size]
                    if chars:
                        t.endchar = startchar + size
                    yield t
                elif at == 1:
                    t.text = text[0 - size :]
                    if chars:
                        t.startchar = t.endchar - size
                    yield t
                else:
                    for start in range(0, len(text) - size + 1):
                        t.text = text[start : start + size]
                        if chars:
                            t.startchar = startchar + start
                            t.endchar = startchar + start + size
                        yield t
            else:
                if at == -1:
                    limit = min(self.max, len(text))
                    for size in range(self.min, limit + 1):
                        t.text = text[:size]
                        if chars:
                            t.endchar = startchar + size
                        yield t

                elif at == 1:
                    if chars:
                        original_startchar = t.startchar
                    start = max(0, len(text) - self.max)
                    for i in range(start, len(text) - self.min + 1):
                        t.text = text[i:]
                        if chars:
                            t.startchar = original_startchar + i
                        yield t
                else:
                    for start in range(0, len(text) - self.min + 1):
                        for size in range(self.min, self.max + 1):
                            end = start + size
                            if end > len(text):
                                continue

                            t.text = text[start:end]

                            if chars:
                                t.startchar = startchar + start
                                t.endchar = startchar + end

                            yield t


# Analyzers


def NgramAnalyzer(minsize: int, maxsize: int | None = None):
    """Composes an NgramTokenizer and a LowercaseFilter.

    >>> ana = NgramAnalyzer(4)
    >>> [token.text for token in ana("hi there")]
    ["hi t", "i th", " the", "ther", "here"]
    """

    return NgramTokenizer(minsize, maxsize=maxsize) | LowercaseFilter()


def NgramWordAnalyzer(
    minsize: int,
    maxsize: int | None = None,
    tokenizer: Tokenizer | None = None,
    at: Literal["start", "end"] | None = None,
):
    if not tokenizer:
        tokenizer = RegexTokenizer()
    return tokenizer | LowercaseFilter() | NgramFilter(minsize, maxsize, at=at)
