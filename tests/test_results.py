from itertools import permutations

import pytest

from whoosh import analysis, fields, formats, highlight, qparser, query
from whoosh.codec.whoosh3 import W3Codec
from whoosh.filedb.filestore import RamStorage
from whoosh.util.testing import TempIndex, TempStorage


def test_score_retrieval():
    schema = fields.Schema(
        title=fields.TEXT(stored=True), content=fields.TEXT(stored=True)
    )
    storage = RamStorage()
    ix = storage.create_index(schema)
    writer = ix.writer()
    writer.add_document(
        title="Miss Mary",
        content="Mary had a little white lamb its fleece was white as snow",
    )
    writer.add_document(
        title="Snow White",
        content="Snow white lived in the forest with seven dwarfs",
    )
    writer.commit()

    with ix.searcher() as s:
        results = s.search(query.Term("content", "white"))
        assert len(results) == 2
        assert results[0]["title"] == "Miss Mary"
        assert results[1]["title"] == "Snow White"
        assert results.score(0) is not None
        assert results.score(0) != 0
        assert results.score(0) != 1


def test_resultcopy():
    schema = fields.Schema(a=fields.TEXT(stored=True))
    st = RamStorage()
    ix = st.create_index(schema)

    w = ix.writer()
    w.add_document(a="alfa bravo charlie")
    w.add_document(a="bravo charlie delta")
    w.add_document(a="charlie delta echo")
    w.add_document(a="delta echo foxtrot")
    w.commit()

    with ix.searcher() as s:
        r = s.search(qparser.QueryParser("a", None).parse("charlie"))
        assert len(r) == 3
        rcopy = r.copy()
        assert r.top_n == rcopy.top_n


def test_resultslength():
    schema = fields.Schema(id=fields.ID(stored=True), value=fields.TEXT)
    ix = RamStorage().create_index(schema)

    w = ix.writer()
    w.add_document(id="1", value="alfa alfa alfa alfa alfa")
    w.add_document(id="2", value="alfa alfa alfa alfa")
    w.add_document(id="3", value="alfa alfa alfa")
    w.add_document(id="4", value="alfa alfa")
    w.add_document(id="5", value="alfa")
    w.add_document(id="6", value="bravo")
    w.commit()

    with ix.searcher() as s:
        r = s.search(query.Term("value", "alfa"), limit=3)
        assert len(r) == 5
        assert r.scored_length() == 3
        assert r[10:] == []


def test_combine():
    schema = fields.Schema(id=fields.ID(stored=True), value=fields.TEXT)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id="1", value="alfa bravo charlie all")
    w.add_document(id="2", value="bravo charlie echo all")
    w.add_document(id="3", value="charlie echo foxtrot all")
    w.add_document(id="4", value="echo foxtrot india all")
    w.add_document(id="5", value="foxtrot india juliet all")
    w.add_document(id="6", value="india juliet alfa all")
    w.add_document(id="7", value="juliet alfa bravo all")
    w.add_document(id="8", value="charlie charlie charlie all")
    w.commit()

    with ix.searcher() as s:

        def idsof(r):
            return "".join(hit["id"] for hit in r)

        def check(r1, methodname, r2, ids):
            getattr(r1, methodname)(r2)
            assert idsof(r1) == ids

        def rfor(t):
            return s.search(query.Term("value", t))

        assert idsof(rfor("foxtrot")) == "345"
        check(rfor("foxtrot"), "extend", rfor("charlie"), "345812")
        check(rfor("foxtrot"), "filter", rfor("juliet"), "5")
        check(rfor("charlie"), "filter", rfor("foxtrot"), "3")
        check(rfor("all"), "filter", rfor("foxtrot"), "345")
        check(rfor("all"), "upgrade", rfor("india"), "45612378")
        check(rfor("charlie"), "upgrade_and_extend", rfor("echo"), "23814")


def test_results_filter():
    schema = fields.Schema(id=fields.STORED, words=fields.KEYWORD(stored=True))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id="1", words="bravo top")
    w.add_document(id="2", words="alfa top")
    w.add_document(id="3", words="alfa top")
    w.add_document(id="4", words="alfa bottom")
    w.add_document(id="5", words="bravo bottom")
    w.add_document(id="6", words="charlie bottom")
    w.add_document(id="7", words="charlie bottom")
    w.commit()

    with ix.searcher() as s:

        def check(r, target):
            result = "".join(s.stored_fields(d)["id"] for d in r.docs())
            assert result == target

        r = s.search(query.Term("words", "alfa"))
        r.filter(s.search(query.Term("words", "bottom")))
        check(r, "4")


def test_sorted_extend():
    from whoosh import sorting

    schema = fields.Schema(
        title=fields.TEXT(stored=True),
        keywords=fields.TEXT,
        num=fields.NUMERIC(stored=True, sortable=True),
    )
    domain = "alfa bravo charlie delta echo foxtrot golf hotel india".split()
    keys = "juliet kilo lima november oskar papa quebec romeo".split()

    combined = 0
    tcount = 0
    kcount = 0
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            for i, words in enumerate(permutations(domain, 3)):
                key = keys[i % (len(domain) - 1)]
                if "bravo" in words:
                    tcount += 1
                if key == "kilo":
                    kcount += 1
                if "bravo" in words or key == "kilo":
                    combined += 1

                w.add_document(title=" ".join(words), keywords=key, num=i)

        with ix.searcher() as s:
            facet = sorting.MultiFacet(
                [sorting.FieldFacet("num", reverse=True), sorting.ScoreFacet()]
            )

            r1 = s.search(query.Term("title", "bravo"), limit=None, sortedby=facet)
            r2 = s.search(query.Term("keywords", "kilo"), limit=None, sortedby=facet)

            assert len(r1) == tcount
            assert len(r2) == kcount
            r1.extend(r2)
            assert len(r1) == combined


def test_extend_empty():
    schema = fields.Schema(id=fields.STORED, words=fields.KEYWORD)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id=1, words="alfa bravo charlie")
    w.add_document(id=2, words="bravo charlie delta")
    w.add_document(id=3, words="charlie delta echo")
    w.add_document(id=4, words="delta echo foxtrot")
    w.add_document(id=5, words="echo foxtrot golf")
    w.commit()

    with ix.searcher() as s:
        # Get an empty results object
        r1 = s.search(query.Term("words", "hotel"))
        # Copy it
        r1c = r1.copy()
        # Get a non-empty results object
        r2 = s.search(query.Term("words", "delta"))
        # Copy it
        r2c = r2.copy()
        # Extend r1 with r2
        r1c.extend(r2c)
        assert [hit["id"] for hit in r1c] == [2, 3, 4]
        assert r1c.scored_length() == 3


def test_extend_filtered():
    schema = fields.Schema(id=fields.STORED, text=fields.TEXT(stored=True))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id=1, text="alfa bravo charlie")
    w.add_document(id=2, text="bravo charlie delta")
    w.add_document(id=3, text="juliet delta echo")
    w.add_document(id=4, text="delta bravo alfa")
    w.add_document(id=5, text="foxtrot sierra tango")
    w.commit()

    hits = lambda result: [hit["id"] for hit in result]

    with ix.searcher() as s:
        r1 = s.search(query.Term("text", "alfa"), filter={1, 4})
        assert r1.allowed == {1, 4}
        assert len(r1.top_n) == 0

        r2 = s.search(query.Term("text", "bravo"))
        assert len(r2.top_n) == 3
        assert hits(r2) == [1, 2, 4]

        r3 = r1.copy()
        assert r3.allowed == {1, 4}
        assert len(r3.top_n) == 0
        r3.extend(r2)
        assert len(r3.top_n) == 3
        assert hits(r3) == [1, 2, 4]


def test_pages():
    from whoosh.scoring import Frequency

    schema = fields.Schema(id=fields.ID(stored=True), c=fields.TEXT)
    ix = RamStorage().create_index(schema)

    w = ix.writer()
    w.add_document(id="1", c="alfa alfa alfa alfa alfa alfa")
    w.add_document(id="2", c="alfa alfa alfa alfa alfa")
    w.add_document(id="3", c="alfa alfa alfa alfa")
    w.add_document(id="4", c="alfa alfa alfa")
    w.add_document(id="5", c="alfa alfa")
    w.add_document(id="6", c="alfa")
    w.commit()

    with ix.searcher(weighting=Frequency) as s:
        q = query.Term("c", "alfa")
        r = s.search(q)
        assert [d["id"] for d in r] == ["1", "2", "3", "4", "5", "6"]
        r = s.search_page(q, 2, pagelen=2)
        assert [d["id"] for d in r] == ["3", "4"]

        r = s.search_page(q, 2, pagelen=4)
        assert r.total == 6
        assert r.pagenum == 2
        assert r.pagelen == 2


def test_pages_with_filter():
    from whoosh.scoring import Frequency

    schema = fields.Schema(id=fields.ID(stored=True), type=fields.TEXT(), c=fields.TEXT)
    ix = RamStorage().create_index(schema)

    w = ix.writer()
    w.add_document(id="1", type="odd", c="alfa alfa alfa alfa alfa alfa")
    w.add_document(id="2", type="even", c="alfa alfa alfa alfa alfa")
    w.add_document(id="3", type="odd", c="alfa alfa alfa alfa")
    w.add_document(id="4", type="even", c="alfa alfa alfa")
    w.add_document(id="5", type="odd", c="alfa alfa")
    w.add_document(id="6", type="even", c="alfa")
    w.commit()

    with ix.searcher(weighting=Frequency) as s:
        q = query.Term("c", "alfa")
        filterq = query.Term("type", "even")
        r = s.search(q, filter=filterq)
        assert [d["id"] for d in r] == ["2", "4", "6"]
        r = s.search_page(q, 2, pagelen=2, filter=filterq)
        assert [d["id"] for d in r] == ["6"]


def test_extra_slice():
    schema = fields.Schema(key=fields.ID(stored=True))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    for char in "abcdefghijklmnopqrstuvwxyz":
        w.add_document(key=char)
    w.commit()

    with ix.searcher() as s:
        r = s.search(query.Every(), limit=5)
        assert r[6:7] == []


def test_page_counts():
    from whoosh.scoring import Frequency

    schema = fields.Schema(id=fields.ID(stored=True))
    st = RamStorage()
    ix = st.create_index(schema)

    w = ix.writer()
    for i in range(10):
        w.add_document(id=str(i))
    w.commit()

    with ix.searcher(weighting=Frequency) as s:
        q = query.Every("id")

        r = s.search(q)
        assert len(r) == 10

        with pytest.raises(ValueError):
            s.search_page(q, 0)

        r = s.search_page(q, 1, 5)
        assert len(r) == 10
        assert r.pagecount == 2

        r = s.search_page(q, 1, 5)
        assert len(r) == 10
        assert r.pagecount == 2

        r = s.search_page(q, 2, 5)
        assert len(r) == 10
        assert r.pagecount == 2
        assert r.pagenum == 2

        r = s.search_page(q, 1, 10)
        assert len(r) == 10
        assert r.pagecount == 1
        assert r.pagenum == 1


def test_resultspage():
    schema = fields.Schema(id=fields.STORED, content=fields.TEXT(stored=True))
    ix = RamStorage().create_index(schema)

    domain = ("alfa", "bravo", "bravo", "charlie", "delta")
    w = ix.writer()
    for i, lst in enumerate(permutations(domain, 3)):
        w.add_document(id=str(i), content=" ".join(lst))
    w.commit()

    with ix.searcher() as s:
        q = query.Term("content", "bravo")
        r = s.search(q, limit=10)
        tops = list(r)

        rp = s.search_page(q, 1, pagelen=5)
        assert rp.scored_length() == 5
        assert list(rp) == tops[0:5]
        assert rp[10:] == []

        rp = s.search_page(q, 2, pagelen=5)
        assert list(rp) == tops[5:10]

        rp = s.search_page(q, 1, pagelen=10)
        assert len(rp) == 54
        assert rp.pagecount == 6
        rp = s.search_page(q, 6, pagelen=10)
        assert len(list(rp)) == 4
        assert rp.is_last_page()

        with pytest.raises(ValueError):
            s.search_page(q, 0)
        assert s.search_page(q, 10).pagenum == 6

        rp = s.search_page(query.Term("content", "glonk"), 1)
        assert len(rp) == 0
        assert rp.is_last_page()


def test_highlight_setters():
    schema = fields.Schema(text=fields.TEXT)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(text="Hello")
    w.commit()

    r = ix.searcher().search(query.Term("text", "hello"))
    hl = highlight.Highlighter()
    ucf = highlight.UppercaseFormatter()
    r.highlighter = hl
    r.formatter = ucf
    assert hl.formatter is ucf


def test_snippets():
    ana = analysis.StemmingAnalyzer()
    schema = fields.Schema(text=fields.TEXT(stored=True, analyzer=ana))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(
        text=(
            "Lay out the rough animation by creating the important poses where they occur on the timeline."
        )
    )
    w.add_document(
        text=(
            "Set key frames on everything that's key-able. This is for control and predictability: you don't want to accidentally leave something un-keyed. This is also much faster than selecting the parameters to key."
        )
    )
    w.add_document(
        text=(
            "Use constant (straight) or sometimes linear transitions between keyframes in the channel editor. This makes the character jump between poses."
        )
    )
    w.add_document(
        text=(
            "Keying everything gives quick, immediate results. But it can become difficult to tweak the animation later, especially for complex characters."
        )
    )
    w.add_document(
        text=(
            "Copy the current pose to create the next one: pose the character, key everything, then copy the keyframe in the playbar to another frame, and key everything at that frame."
        )
    )
    w.commit()

    target = [
        "Set KEY frames on everything that's KEY-able",
        "Copy the current pose to create the next one: pose the character, KEY everything, then copy the keyframe in the playbar to another frame, and KEY everything at that frame",
        "KEYING everything gives quick, immediate results",
    ]

    with ix.searcher() as s:
        qp = qparser.QueryParser("text", ix.schema)
        q = qp.parse("key")
        r = s.search(q, terms=True)
        r.fragmenter = highlight.SentenceFragmenter()
        r.formatter = highlight.UppercaseFormatter()

        assert sorted([hit.highlights("text", top=1) for hit in r]) == sorted(target)


def test_keyterms():
    ana = analysis.StandardAnalyzer()
    vectorformat = formats.Frequency()
    schema = fields.Schema(
        path=fields.ID, content=fields.TEXT(analyzer=ana, vector=vectorformat)
    )
    st = RamStorage()
    ix = st.create_index(schema)
    w = ix.writer()
    w.add_document(path="a", content="This is some generic content")
    w.add_document(path="b", content="This is some distinctive content")
    w.commit()

    with ix.searcher() as s:
        docnum = s.document_number(path="b")
        keyterms = list(s.key_terms([docnum], "content"))
        assert len(keyterms) > 0
        assert keyterms[0][0] == "distinctive"

        r = s.search(query.Term("path", "b"))
        keyterms2 = list(r.key_terms("content"))
        assert len(keyterms2) > 0
        assert keyterms2[0][0] == "distinctive"


def test_lengths():
    schema = fields.Schema(id=fields.STORED, text=fields.TEXT)
    ix = RamStorage().create_index(schema)

    w = ix.writer()
    w.add_document(id=1, text="alfa bravo charlie delta echo")
    w.add_document(id=2, text="bravo charlie delta echo foxtrot")
    w.add_document(id=3, text="charlie needle echo foxtrot golf")
    w.add_document(id=4, text="delta echo foxtrot golf hotel")
    w.add_document(id=5, text="echo needle needle hotel india")
    w.add_document(id=6, text="foxtrot golf hotel india juliet")
    w.add_document(id=7, text="golf needle india juliet kilo")
    w.add_document(id=8, text="hotel india juliet needle lima")
    w.commit()

    with ix.searcher() as s:
        q = query.Or([query.Term("text", "needle"), query.Term("text", "charlie")])
        r = s.search(q, limit=2)
        assert not r.has_exact_length()
        assert r.estimated_length() == 7
        assert r.estimated_min_length() == 3
        assert r.scored_length() == 2
        assert len(r) == 6


def test_lengths2():
    schema = fields.Schema(text=fields.TEXT(stored=True))
    ix = RamStorage().create_index(schema)
    count = 0
    for _ in range(3):
        w = ix.writer()
        for ls in permutations("alfa bravo charlie".split()):
            if "bravo" in ls and "charlie" in ls:
                count += 1
            w.add_document(text=" ".join(ls))
        w.commit(merge=False)

    with ix.searcher() as s:
        q = query.Or([query.Term("text", "bravo"), query.Term("text", "charlie")])
        r = s.search(q, limit=None)
        assert len(r) == count

        r = s.search(q, limit=3)
        assert len(r) == count


def test_stability():
    schema = fields.Schema(text=fields.TEXT)
    ix = RamStorage().create_index(schema)
    domain = "alfa bravo charlie delta".split()
    w = ix.writer()
    for ls in permutations(domain, 3):
        w.add_document(text=" ".join(ls))
    w.commit()

    with ix.searcher() as s:
        q = query.Term("text", "bravo")
        last = []
        for i in range(s.doc_frequency("text", "bravo")):
            # Only un-optimized results are stable
            r = s.search(q, limit=i + 1, optimize=False)
            docnums = [hit.docnum for hit in r]
            assert docnums[:-1] == last
            last = docnums


def test_terms():
    schema = fields.Schema(text=fields.TEXT(stored=True))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(text="alfa sierra tango")
    w.add_document(text="bravo charlie delta")
    w.add_document(text="charlie delta echo")
    w.add_document(text="delta echo foxtrot")
    w.commit()

    qp = qparser.QueryParser("text", ix.schema)
    q = qp.parse("(bravo AND charlie) OR foxtrot OR missing")
    r = ix.searcher().search(q, terms=True)

    fieldobj = schema["text"]

    def txts(tset):
        return sorted(fieldobj.from_bytes(t[1]) for t in tset)

    assert txts(r.matched_terms()) == ["bravo", "charlie", "foxtrot"]
    for hit in r:
        value = hit["text"]
        for txt in txts(hit.matched_terms()):
            assert txt in value


def test_hit_column():
    # Not stored
    schema = fields.Schema(text=fields.TEXT())
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(text="alfa bravo charlie")

    with ix.searcher() as s:
        r = s.search(query.Term("text", "alfa"))
        assert len(r) == 1
        hit = r[0]
        with pytest.raises(KeyError):
            _ = hit["text"]

    # With column
    schema = fields.Schema(text=fields.TEXT(sortable=True))
    ix = RamStorage().create_index(schema)
    with ix.writer(codec=W3Codec()) as w:
        w.add_document(text="alfa bravo charlie")

    with ix.searcher() as s:
        r = s.search(query.Term("text", "alfa"))
        assert len(r) == 1
        hit = r[0]
        assert hit["text"] == "alfa bravo charlie"


def test_closed_searcher():
    from whoosh.reading import ReaderClosed

    schema = fields.Schema(key=fields.KEYWORD(stored=True, sortable=True))

    with TempStorage() as st:
        ix = st.create_index(schema)
        with ix.writer() as w:
            w.add_document(key="alfa")
            w.add_document(key="bravo")
            w.add_document(key="charlie")
            w.add_document(key="delta")
            w.add_document(key="echo")

        s = ix.searcher()
        r = s.search(query.TermRange("key", "b", "d"))
        s.close()
        assert s.is_closed
        with pytest.raises(ReaderClosed):
            assert r[0]["key"] == "bravo"
        with pytest.raises(ReaderClosed):
            s.reader().column_reader("key")
        with pytest.raises(ReaderClosed):
            s.suggest("key", "brovo")

        s = ix.searcher()
        r = s.search(query.TermRange("key", "b", "d"))
        assert r[0]
        assert r[0]["key"] == "bravo"
        c = s.reader().column_reader("key")
        assert c[1] == "bravo"
        assert s.suggest("key", "brovo") == ["bravo"]


def test_paged_highlights():
    schema = fields.Schema(text=fields.TEXT(stored=True))
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(text="alfa bravo charlie delta echo foxtrot")
        w.add_document(text="bravo charlie delta echo foxtrot golf")
        w.add_document(text="charlie delta echo foxtrot golf hotel")
        w.add_document(text="delta echo foxtrot golf hotel india")
        w.add_document(text="echo foxtrot golf hotel india juliet")
        w.add_document(text="foxtrot golf hotel india juliet kilo")

    with ix.searcher() as s:
        q = query.Term("text", "alfa")
        page = s.search_page(q, 1, pagelen=3)

        page.results.fragmenter = highlight.WholeFragmenter()
        page.results.formatter = highlight.UppercaseFormatter()
        hi = page[0].highlights("text")
        assert hi == "ALFA bravo charlie delta echo foxtrot"


def test_phrase_keywords():
    schema = fields.Schema(text=fields.TEXT(stored=True))
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(text="alfa bravo charlie delta")
        w.add_document(text="bravo charlie delta echo")
        w.add_document(text="charlie delta echo foxtrot")
        w.add_document(text="delta echo foxtrot alfa")
        w.add_document(text="echo foxtrot alfa bravo")

    with ix.searcher() as s:
        q = query.Phrase("text", "alfa bravo".split())
        r = s.search(q)
        assert len(r) == 2
        kts = " ".join(t for t, score in r.key_terms("text"))
        assert kts == "alfa bravo charlie foxtrot delta"


def test_every_keywords():
    schema = fields.Schema(title=fields.TEXT, content=fields.TEXT(stored=True))
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(title="alfa", content="bravo")
        w.add_document(title="charlie", content="delta")

    with ix.searcher() as s:
        q = qparser.QueryParser("content", ix.schema).parse("*")
        assert isinstance(q, query.Every)

        r = s.search(q, terms=True)
        assert len(r) == 2
        hit = r[0]
        assert hit["content"] == "bravo"
        assert hit.highlights("content") == ""


def test_filter_by_result():
    schema = fields.Schema(
        title=fields.TEXT(stored=True), content=fields.TEXT(stored=True)
    )

    with TempIndex(schema, "filter") as ix:
        words = "foo bar baz qux barney".split()
        with ix.writer() as w:
            for x in range(100):
                t = "even" if x % 2 == 0 else "odd"
                c = words[x % len(words)]
                w.add_document(title=t, content=c)

        with ix.searcher() as searcher:
            fq = query.Term("title", "even")
            filter_result = searcher.search(fq)
            assert filter_result.docset is None

            q = query.Term("content", "foo")

            # filter_result.docs()
            result = searcher.search(q, filter=filter_result)
            assert all(x["title"] == "even" and x["content"] == "foo" for x in result)
