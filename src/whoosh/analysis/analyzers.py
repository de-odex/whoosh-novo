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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Protocol

from whoosh.analysis.filters import STOP_WORDS, Filter, LowercaseFilter, StopFilter
from whoosh.analysis.intraword import IntraWordFilter
from whoosh.analysis.morph import StemFilter
from whoosh.analysis.tokenizers import (
    CommaSeparatedTokenizer,
    IDTokenizer,
    RegexTokenizer,
    SpaceSeparatedTokenizer,
    Tokenizer,
    default_pattern,
)
from whoosh.lang.porter import stem

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Generator
    from re import Pattern

    from whoosh.analysis.acore import Token

# Analyzers


class Analyzer(Protocol):
    """Abstract base class for analyzers."""

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def __eq__(self, other: object):
        return (
            other is not None
            and isinstance(other, type(self))
            and self.__dict__ == other.__dict__
        )

    @abstractmethod
    def __call__(self, value: str, **kwargs: Any) -> Generator[Token]:
        raise NotImplementedError

    @abstractmethod
    def clean(self) -> None:
        raise NotImplementedError


class CompositeAnalyzer(Analyzer):
    tokenizer: Tokenizer
    filters: list[Filter]

    def __init__(self, tokenizer: Tokenizer, *filters: Filter):
        self.tokenizer = tokenizer
        self.filters = []

        for filter in filters:
            self.filters.append(filter)

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(repr(item) for item in self.filters),
        )

    def __call__(
        self, value: str, no_morph: bool = False, **kwargs: Any
    ) -> Generator[Token]:
        # Start with tokenizer
        gen = self.tokenizer(value, **kwargs)
        # Run filters
        for item in self.filters:
            if not (no_morph and hasattr(item, "is_morph") and item.is_morph):
                gen = item(gen)
        return gen

    def __getitem__(self, item: int) -> Tokenizer | Filter:
        return [self.tokenizer, *self.filters].__getitem__(item)  # type: ignore

    def __len__(self):
        return len(self.filters)

    def __eq__(self, other: object):
        return (
            other is not None
            and isinstance(other, type(self))
            and self.filters == other.filters
        )

    def __or__(self, other: Filter) -> CompositeAnalyzer:
        if not isinstance(other, Filter):  # type: ignore
            raise TypeError(f"{self!r} is not composable with {other!r}")
        return CompositeAnalyzer(self.tokenizer, *self.filters, other)

    def clean(self):
        for item in self.filters:
            item.clean()

    def has_morph(self):
        return any(item.is_morph for item in self.filters)


# Functions that return composed analyzers


def IDAnalyzer(lowercase: bool = False) -> Analyzer:
    """Deprecated, just use an IDTokenizer directly, with a LowercaseFilter if
    desired.
    """

    tokenizer = IDTokenizer()
    if lowercase:
        tokenizer = tokenizer | LowercaseFilter()
    return tokenizer


def KeywordAnalyzer(lowercase: bool = False, commas: bool = False) -> Analyzer:
    """Parses whitespace- or comma-separated tokens.

    >>> ana = KeywordAnalyzer()
    >>> [token.text for token in ana("Hello there, this is a TEST")]
    ["Hello", "there,", "this", "is", "a", "TEST"]

    :param lowercase: whether to lowercase the tokens.
    :param commas: if True, items are separated by commas rather than
        whitespace.
    """

    if commas:
        tokenizer = CommaSeparatedTokenizer()
    else:
        tokenizer = SpaceSeparatedTokenizer()
    if lowercase:
        tokenizer = tokenizer | LowercaseFilter()
    return tokenizer


def RegexAnalyzer(
    expression: str | Pattern[str] = r"\w+(\.?\w+)*", gaps: bool = False
) -> RegexTokenizer:
    """Deprecated, just use a RegexTokenizer directly."""

    return RegexTokenizer(expression=expression, gaps=gaps)


def SimpleAnalyzer(
    expression: str | Pattern[str] = default_pattern, gaps: bool = False
) -> CompositeAnalyzer:
    """Composes a RegexTokenizer with a LowercaseFilter.

    >>> ana = SimpleAnalyzer()
    >>> [token.text for token in ana("Hello there, this is a TEST")]
    ["hello", "there", "this", "is", "a", "test"]

    :param expression: The regular expression pattern to use to extract tokens.
    :param gaps: If True, the tokenizer *splits* on the expression, rather
        than matching on the expression.
    """

    return RegexTokenizer(expression=expression, gaps=gaps) | LowercaseFilter()


def StandardAnalyzer(
    expression: str | Pattern[str] = default_pattern,
    stoplist: Collection[str] | None = STOP_WORDS,
    minsize: int = 2,
    maxsize: int | None = None,
    gaps: bool = False,
) -> CompositeAnalyzer:
    """Composes a RegexTokenizer with a LowercaseFilter and optional
    StopFilter.

    >>> ana = StandardAnalyzer()
    >>> [token.text for token in ana("Testing is testing and testing")]
    ["testing", "testing", "testing"]

    :param expression: The regular expression pattern to use to extract tokens.
    :param stoplist: A list of stop words. Set this to None to disable
        the stop word filter.
    :param minsize: Words smaller than this are removed from the stream.
    :param maxsize: Words longer that this are removed from the stream.
    :param gaps: If True, the tokenizer *splits* on the expression, rather
        than matching on the expression.
    """

    ret = RegexTokenizer(expression=expression, gaps=gaps)
    chain = ret | LowercaseFilter()
    if stoplist is not None:
        chain = chain | StopFilter(stoplist=stoplist, minsize=minsize, maxsize=maxsize)
    return chain


def StemmingAnalyzer(
    expression: str | Pattern[str] = default_pattern,
    stoplist: Collection[str] | None = STOP_WORDS,
    minsize: int = 2,
    maxsize: int | None = None,
    gaps: bool = False,
    stemfn: Callable[[str], str] = stem,
    ignore: Collection[str] | None = None,
    cachesize: int | None = 50000,
) -> CompositeAnalyzer:
    """Composes a RegexTokenizer with a lower case filter, an optional stop
    filter, and a stemming filter.

    >>> ana = StemmingAnalyzer()
    >>> [token.text for token in ana("Testing is testing and testing")]
    ["test", "test", "test"]

    :param expression: The regular expression pattern to use to extract tokens.
    :param stoplist: A list of stop words. Set this to None to disable
        the stop word filter.
    :param minsize: Words smaller than this are removed from the stream.
    :param maxsize: Words longer that this are removed from the stream.
    :param gaps: If True, the tokenizer *splits* on the expression, rather
        than matching on the expression.
    :param ignore: a set of words to not stem.
    :param cachesize: the maximum number of stemmed words to cache. The larger
        this number, the faster stemming will be but the more memory it will
        use. Use None for no cache, or -1 for an unbounded cache.
    """

    ret = RegexTokenizer(expression=expression, gaps=gaps)
    chain = ret | LowercaseFilter()
    if stoplist is not None:
        chain = chain | StopFilter(stoplist=stoplist, minsize=minsize, maxsize=maxsize)
    return chain | StemFilter(stemfn=stemfn, ignore=ignore, cachesize=cachesize)


def FancyAnalyzer(
    expression: str | Pattern[str] = r"\s+",
    stoplist: Collection[str] = STOP_WORDS,
    minsize: int = 2,
    gaps: bool = True,
    splitwords: bool = True,
    splitnums: bool = True,
    mergewords: bool = False,
    mergenums: bool = False,
) -> CompositeAnalyzer:
    """Composes a RegexTokenizer with an IntraWordFilter, LowercaseFilter, and
    StopFilter.

    >>> ana = FancyAnalyzer()
    >>> [token.text for token in ana("Should I call getInt or get_real?")]
    ["should", "call", "getInt", "get", "int", "get_real", "get", "real"]

    :param expression: The regular expression pattern to use to extract tokens.
    :param stoplist: A list of stop words. Set this to None to disable
        the stop word filter.
    :param minsize: Words smaller than this are removed from the stream.
    :param maxsize: Words longer that this are removed from the stream.
    :param gaps: If True, the tokenizer *splits* on the expression, rather
        than matching on the expression.
    """

    return (
        RegexTokenizer(expression=expression, gaps=gaps)
        | IntraWordFilter(
            splitwords=splitwords,
            splitnums=splitnums,
            mergewords=mergewords,
            mergenums=mergenums,
        )
        | LowercaseFilter()
        | StopFilter(stoplist=stoplist, minsize=minsize)
    )


def LanguageAnalyzer(
    lang: str,
    expression: str | Pattern[str] = default_pattern,
    gaps: bool = False,
    cachesize: int | None = 50000,
) -> CompositeAnalyzer:
    """Configures a simple analyzer for the given language, with a
    LowercaseFilter, StopFilter, and StemFilter.

    >>> ana = LanguageAnalyzer("es")
    >>> [token.text for token in ana("Por el mar corren las liebres")]
    ['mar', 'corr', 'liebr']

    The list of available languages is in `whoosh.lang.languages`.
    You can use :func:`whoosh.lang.has_stemmer` and
    :func:`whoosh.lang.has_stopwords` to check if a given language has a
    stemming function and/or stop word list available.

    :param expression: The regular expression pattern to use to extract tokens.
    :param gaps: If True, the tokenizer *splits* on the expression, rather
        than matching on the expression.
    :param cachesize: the maximum number of stemmed words to cache. The larger
        this number, the faster stemming will be but the more memory it will
        use.
    """

    from whoosh.lang import NoStemmer, NoStopWords

    # Make the start of the chain
    chain = RegexTokenizer(expression=expression, gaps=gaps) | LowercaseFilter()

    # Add a stop word filter
    try:
        chain = chain | StopFilter(lang=lang)
    except NoStopWords:
        pass

    # Add a stemming filter
    try:
        chain = chain | StemFilter(lang=lang, cachesize=cachesize)
    except NoStemmer:
        pass

    return chain
