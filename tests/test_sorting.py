import random
from datetime import datetime, timedelta, timezone
from itertools import permutations

from whoosh import columns, fields, query, sorting
from whoosh.filedb.filestore import RamStorage
from whoosh.util.testing import TempIndex

try:
    import multiprocessing
except ImportError:
    pass
else:

    class MPFCTask(multiprocessing.Process):
        def __init__(self, storage, indexname):
            multiprocessing.Process.__init__(self)
            self.storage = storage
            self.indexname = indexname

        def run(self):
            ix = self.storage.open_index(self.indexname)
            with ix.searcher() as s:
                r = s.search(query.Every(), sortedby="key", limit=None)
                result = "".join([h["key"] for h in r])
                assert result == "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def u(s):
    return s.decode("ascii") if isinstance(s, bytes) else s


docs = (
    {"id": "zulu", "num": 100, "tag": "one", "frac": 0.75},
    {"id": "xray", "num": -5, "tag": "three", "frac": 2.0},
    {"id": "yankee", "num": 3, "tag": "two", "frac": 5.5},
    {"id": "alfa", "num": 7, "tag": "three", "frac": 2.25},
    {"id": "tango", "num": 2, "tag": "two", "frac": 1.75},
    {"id": "foxtrot", "num": -800, "tag": "two", "frac": 3.25},
    {"id": "sierra", "num": 1, "tag": "one", "frac": 4.75},
    {"id": "whiskey", "num": 0, "tag": "three", "frac": 5.25},
    {"id": "bravo", "num": 582045, "tag": "three", "frac": 1.25},
)


def get_schema():
    return fields.Schema(
        id=fields.ID(stored=True),
        num=fields.NUMERIC(stored=True),
        frac=fields.NUMERIC(float, stored=True),
        tag=fields.ID(stored=True),
        ev=fields.ID,
    )


def make_single_index(ix):
    w = ix.writer()
    for doc in docs:
        w.add_document(ev="a", **doc)
    w.commit()


def make_multi_index(ix):
    for i in range(0, len(docs), 3):
        w = ix.writer()
        for doc in docs[i : i + 3]:
            w.add_document(ev="a", **doc)
        w.commit(merge=False)


def try_sort(sortedby, key, q=None, limit=None, reverse=False):
    if q is None:
        q = query.Term("ev", "a")

    correct = [d["id"] for d in sorted(docs, key=key, reverse=reverse)][:limit]
    schema = get_schema()

    for fn in (make_single_index, make_multi_index):
        ix = RamStorage().create_index(schema)
        fn(ix)
        with ix.searcher() as s:
            r = s.search(q, sortedby=sortedby, limit=limit, reverse=reverse)
            rids = [d["id"] for d in r]
            assert rids == correct


def test_sortedby():
    try_sort("id", lambda d: d["id"])
    try_sort("id", lambda d: d["id"], limit=5)
    try_sort("id", lambda d: d["id"], reverse=True)
    try_sort("id", lambda d: d["id"], limit=5, reverse=True)


def test_multisort():
    mf = sorting.MultiFacet(["tag", "id"])
    try_sort(mf, lambda d: (d["tag"], d["id"]))
    try_sort(mf, lambda d: (d["tag"], d["id"]), reverse=True)
    try_sort(mf, lambda d: (d["tag"], d["id"]), limit=5)
    try_sort(mf, lambda d: (d["tag"], d["id"]), reverse=True, limit=5)


def test_numeric():
    try_sort("num", lambda d: d["num"])
    try_sort("num", lambda d: d["num"], reverse=True)
    try_sort("num", lambda d: d["num"], limit=5)
    try_sort("frac", lambda d: d["frac"])


def test_empty_field():
    schema = fields.Schema(id=fields.STORED, key=fields.KEYWORD)
    with TempIndex(schema, "emptysort") as ix:
        w = ix.writer()
        w.add_document(id=1)
        w.add_document(id=2)
        w.add_document(id=3)
        w.commit()

        with ix.searcher() as s:
            r = s.search(query.Every(), sortedby="key")
            assert [h["id"] for h in r] == [1, 2, 3]


def test_page_sorted():
    schema = fields.Schema(key=fields.ID(stored=True))
    with TempIndex(schema, "pagesorted") as ix:
        domain = list("abcdefghijklmnopqrstuvwxyz")
        random.shuffle(domain)

        w = ix.writer()
        for char in domain:
            w.add_document(key=char)
        w.commit()

        with ix.searcher() as s:
            r = s.search(query.Every(), sortedby="key", limit=5)
            assert r.scored_length() == 5
            assert len(r) == s.doc_count_all()

            rp = s.search_page(query.Every(), 1, pagelen=5, sortedby="key")
            assert "".join([h["key"] for h in rp]) == "abcde"
            assert rp[10:] == []

            rp = s.search_page(query.Term("key", "glonk"), 1, pagelen=5, sortedby="key")
            assert len(rp) == 0
            assert rp.is_last_page()


def test_score_facet():
    schema = fields.Schema(id=fields.STORED, a=fields.TEXT, b=fields.TEXT, c=fields.ID)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id=1, a="alfa alfa bravo", b="bottle", c="c")
    w.add_document(id=2, a="alfa alfa alfa", b="bottle", c="c")
    w.commit()
    w = ix.writer()
    w.add_document(id=3, a="alfa bravo bravo", b="bottle", c="c")
    w.add_document(id=4, a="alfa bravo alfa", b="apple", c="c")
    w.commit(merge=False)
    w = ix.writer()
    w.add_document(id=5, a="alfa bravo bravo", b="apple", c="c")
    w.add_document(id=6, a="alfa alfa alfa", b="apple", c="c")
    w.commit(merge=False)

    with ix.searcher() as s:
        facet = sorting.MultiFacet(["b", sorting.ScoreFacet()])
        r = s.search(q=query.Term("a", "alfa"), sortedby=facet)
        assert [h["id"] for h in r] == [6, 4, 5, 2, 1, 3]


def test_function_facet():
    schema = fields.Schema(id=fields.STORED, text=fields.TEXT(stored=True, vector=True))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    domain = ("alfa", "bravo", "charlie")
    count = 1
    for w1 in domain:
        for w2 in domain:
            for w3 in domain:
                for w4 in domain:
                    w.add_document(id=count, text=f"{w1} {w2} {w3} {w4}")
                    count += 1
    w.commit()

    def fn(searcher, docnum):
        v = dict(searcher.vector_as("frequency", docnum, "text"))
        # Give high score to documents that have equal number of "alfa"
        # and "bravo". Negate value so higher values sort first
        return 0 - (1.0 / (abs(v.get("alfa", 0) - v.get("bravo", 0)) + 1.0))

    with ix.searcher() as s:
        q = query.And([query.Term("text", "alfa"), query.Term("text", "bravo")])

        fnfacet = sorting.FunctionFacet(fn)
        r = s.search(q, sortedby=fnfacet)
        texts = [hit["text"] for hit in r]
        for t in texts[:10]:
            tks = t.split()
            assert tks.count("alfa") == tks.count("bravo")


def test_numeric_field_facet():
    schema = fields.Schema(id=fields.STORED, v1=fields.NUMERIC, v2=fields.NUMERIC)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id=1, v1=2, v2=100)
    w.add_document(id=2, v1=1, v2=50)
    w.commit()
    w = ix.writer()
    w.add_document(id=3, v1=2, v2=200)
    w.add_document(id=4, v1=1, v2=100)
    w.commit()
    w = ix.writer(merge=False)
    w.add_document(id=5, v1=2, v2=50)
    w.add_document(id=6, v1=1, v2=200)
    w.commit()

    with ix.searcher() as s:
        mf = sorting.MultiFacet().add_field("v1").add_field("v2", reverse=True)
        r = s.search(query.Every(), sortedby=mf)
        assert [hit["id"] for hit in r] == [6, 4, 2, 3, 1, 5]


def test_query_facet():
    schema = fields.Schema(id=fields.STORED, v=fields.ID)
    ix = RamStorage().create_index(schema)
    for i, ltr in enumerate("iacgbehdf"):
        w = ix.writer()
        w.add_document(id=i, v=ltr)
        w.commit(merge=False)

    with ix.searcher() as s:
        q1 = query.TermRange("v", "a", "c")
        q2 = query.TermRange("v", "d", "f")
        q3 = query.TermRange("v", "g", "i")

        assert [hit["id"] for hit in s.search(q1)] == [1, 2, 4]
        assert [hit["id"] for hit in s.search(q2)] == [5, 7, 8]
        assert [hit["id"] for hit in s.search(q3)] == [0, 3, 6]

        facet = sorting.QueryFacet({"a-c": q1, "d-f": q2, "g-i": q3})
        r = s.search(query.Every(), groupedby=facet)
        # If you specify a facet without a name, it's automatically called
        # "facet"
        assert r.groups("facet") == {
            "a-c": [1, 2, 4],
            "d-f": [5, 7, 8],
            "g-i": [0, 3, 6],
        }


def test_query_facet_overlap():
    domain = "abcdefghi"
    schema = fields.Schema(
        v=fields.KEYWORD(stored=True), num=fields.NUMERIC(stored=True)
    )
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        for i, ltr in enumerate(domain):
            v = f"{ltr} {domain[8 - i]}"
            w.add_document(num=i, v=v)

    with ix.searcher() as s:
        q1 = query.TermRange("v", "a", "c")
        q2 = query.TermRange("v", "d", "f")
        q3 = query.TermRange("v", "g", "i")

        facets = sorting.Facets()
        facets.add_query(
            "myfacet", {"a-c": q1, "d-f": q2, "g-i": q3}, allow_overlap=True
        )
        r = s.search(query.Every(), groupedby=facets)
        gr = r.groups("myfacet")
        assert r.groups("myfacet") == {
            "a-c": [0, 1, 2, 6, 7, 8],
            "d-f": [3, 4, 5],
            "g-i": [0, 1, 2, 6, 7, 8],
        }


def test_missing_field_facet():
    schema = fields.Schema(id=fields.STORED, tag=fields.ID)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id=0, tag="alfa")
    w.add_document(id=1, tag="alfa")
    w.add_document(id=2)
    w.add_document(id=3, tag="bravo")
    w.add_document(id=4)
    w.commit()

    with ix.searcher() as s:
        r = s.search(query.Every(), groupedby="tag")
        assert r.groups("tag") == {None: [2, 4], "bravo": [3], "alfa": [0, 1]}


def test_missing_numeric_facet():
    schema = fields.Schema(id=fields.STORED, tag=fields.NUMERIC)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id=0, tag=1)
    w.add_document(id=1, tag=1)
    w.add_document(id=2)
    w.add_document(id=3, tag=0)
    w.add_document(id=4)
    w.commit()

    with ix.searcher() as s:
        r = s.search(query.Every(), groupedby="tag")
        assert r.groups("tag") == {None: [2, 4], 0: [3], 1: [0, 1]}


def test_missing_overlap():
    schema = fields.Schema(a=fields.NUMERIC(stored=True), b=fields.KEYWORD(stored=True))
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(a=0, b="one two")
        w.add_document(a=1)
        w.add_document(a=2, b="two three")
        w.add_document(a=3)
        w.add_document(a=4, b="three four")

    with ix.searcher() as s:
        facet = sorting.FieldFacet("b", allow_overlap=True)
        r = s.search(query.Every(), groupedby=facet)
        target = {"one": [0], "two": [0, 2], "three": [2, 4], "four": [4], None: [1, 3]}
        assert r.groups() == target


def test_date_facet():
    schema = fields.Schema(id=fields.STORED, date=fields.DATETIME)
    dc = schema["date"].default_column()
    assert isinstance(dc, columns.NumericColumn)

    ix = RamStorage().create_index(schema)
    w = ix.writer()
    d1 = datetime(2011, 7, 13)  # noqa: DTZ001
    d2 = datetime(1984, 3, 29)  # noqa: DTZ001
    w.add_document(id=0, date=d1)
    w.add_document(id=1, date=d1)
    w.add_document(id=2)
    w.add_document(id=3, date=d2)
    w.add_document(id=4)
    w.commit()

    with ix.searcher() as s:
        r = s.search(query.Every(), groupedby="date")
        assert r.groups()
        assert r.groups() == {d1: [0, 1], d2: [3], None: [2, 4]}


def test_range_facet():
    schema = fields.Schema(id=fields.STORED, price=fields.NUMERIC)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id=0, price=200)
    w.add_document(id=1, price=100)
    w.add_document(id=2)
    w.add_document(id=3, price=50)
    w.add_document(id=4, price=500)
    w.add_document(id=5, price=125)
    w.commit()

    with ix.searcher() as s:
        rf = sorting.RangeFacet("price", 0, 1000, 100)
        r = s.search(query.Every(), groupedby={"price": rf})
        assert r.groups("price") == {
            (0, 100): [3],
            (100, 200): [1, 5],
            (200, 300): [0],
            (500, 600): [4],
            None: [2],
        }


def test_range_gaps():
    schema = fields.Schema(id=fields.STORED, num=fields.NUMERIC)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    for i in range(10):
        w.add_document(id=i, num=i)
    w.commit()

    with ix.searcher() as s:
        rf = sorting.RangeFacet("num", 0, 1000, [1, 2, 3])
        r = s.search(query.Every(), groupedby={"num": rf})
        assert r.groups("num") == {
            (0, 1): [0],
            (1, 3): [1, 2],
            (3, 6): [3, 4, 5],
            (6, 9): [6, 7, 8],
            (9, 12): [9],
        }


def test_daterange_facet():
    schema = fields.Schema(id=fields.STORED, date=fields.DATETIME)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id=0, date=datetime(2001, 1, 15, tzinfo=timezone.utc))
    w.add_document(id=1, date=datetime(2001, 1, 10, tzinfo=timezone.utc))
    w.add_document(id=2)
    w.add_document(id=3, date=datetime(2001, 1, 3, tzinfo=timezone.utc))
    w.add_document(id=4, date=datetime(2001, 1, 8, tzinfo=timezone.utc))
    w.add_document(id=5, date=datetime(2001, 1, 6, tzinfo=timezone.utc))
    w.commit()

    with ix.searcher() as s:
        rf = sorting.DateRangeFacet(
            "date",
            datetime(2001, 1, 1, tzinfo=timezone.utc),
            datetime(2001, 1, 20, tzinfo=timezone.utc),
            timedelta(days=5),
        )
        r = s.search(query.Every(), groupedby={"date": rf})
        dt = datetime
        assert r.groups("date") == {
            (
                dt(2001, 1, 1, 0, 0, tzinfo=timezone.utc),
                dt(2001, 1, 6, 0, 0, tzinfo=timezone.utc),
            ): [3],
            (
                dt(2001, 1, 6, 0, 0, tzinfo=timezone.utc),
                dt(2001, 1, 11, 0, 0, tzinfo=timezone.utc),
            ): [1, 4, 5],
            (
                dt(2001, 1, 11, 0, 0, tzinfo=timezone.utc),
                dt(2001, 1, 16, 0, 0, tzinfo=timezone.utc),
            ): [0],
            None: [2],
        }


def test_relative_daterange():
    from whoosh.support.relativedelta import relativedelta

    dt = datetime

    schema = fields.Schema(id=fields.STORED, date=fields.DATETIME)
    ix = RamStorage().create_index(schema)
    basedate = datetime(2001, 1, 1, tzinfo=timezone.utc)
    count = 0
    with ix.writer() as w:
        while basedate < datetime(2001, 12, 1, tzinfo=timezone.utc):
            w.add_document(id=count, date=basedate)
            basedate += timedelta(days=14, hours=16)
            count += 1

    with ix.searcher() as s:
        gap = relativedelta(months=1)
        rf = sorting.DateRangeFacet(
            "date",
            dt(2001, 1, 1, tzinfo=timezone.utc),
            dt(2001, 12, 31, tzinfo=timezone.utc),
            gap,
        )
        r = s.search(query.Every(), groupedby={"date": rf})
        assert r.groups("date") == {
            (
                dt(2001, 1, 1, tzinfo=timezone.utc),
                dt(2001, 2, 1, tzinfo=timezone.utc),
            ): [0, 1, 2],
            (
                dt(2001, 2, 1, tzinfo=timezone.utc),
                dt(2001, 3, 1, tzinfo=timezone.utc),
            ): [3, 4],
            (
                dt(2001, 3, 1, tzinfo=timezone.utc),
                dt(2001, 4, 1, tzinfo=timezone.utc),
            ): [5, 6],
            (
                dt(2001, 4, 1, tzinfo=timezone.utc),
                dt(2001, 5, 1, tzinfo=timezone.utc),
            ): [7, 8],
            (
                dt(2001, 5, 1, tzinfo=timezone.utc),
                dt(2001, 6, 1, tzinfo=timezone.utc),
            ): [9, 10],
            (
                dt(2001, 6, 1, tzinfo=timezone.utc),
                dt(2001, 7, 1, tzinfo=timezone.utc),
            ): [11, 12],
            (
                dt(2001, 7, 1, tzinfo=timezone.utc),
                dt(2001, 8, 1, tzinfo=timezone.utc),
            ): [13, 14],
            (
                dt(2001, 8, 1, tzinfo=timezone.utc),
                dt(2001, 9, 1, tzinfo=timezone.utc),
            ): [15, 16],
            (
                dt(2001, 9, 1, tzinfo=timezone.utc),
                dt(2001, 10, 1, tzinfo=timezone.utc),
            ): [17, 18],
            (
                dt(2001, 10, 1, tzinfo=timezone.utc),
                dt(2001, 11, 1, tzinfo=timezone.utc),
            ): [19, 20],
            (
                dt(2001, 11, 1, tzinfo=timezone.utc),
                dt(2001, 12, 1, tzinfo=timezone.utc),
            ): [21, 22],
        }


def test_overlapping_vector():
    schema = fields.Schema(id=fields.STORED, tags=fields.KEYWORD(vector=True))
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(id=0, tags="alfa bravo charlie")
        w.add_document(id=1, tags="bravo charlie delta")
        w.add_document(id=2, tags="charlie delta echo")
        w.add_document(id=3, tags="delta echo alfa")
        w.add_document(id=4, tags="echo alfa bravo")

    with ix.searcher() as s:
        of = sorting.FieldFacet("tags", allow_overlap=True)
        cat = of.categorizer(s)
        assert cat._use_vectors

        r = s.search(query.Every(), groupedby={"tags": of})
        assert r.groups("tags") == {
            "alfa": [0, 3, 4],
            "bravo": [0, 1, 4],
            "charlie": [0, 1, 2],
            "delta": [1, 2, 3],
            "echo": [2, 3, 4],
        }

        fcts = sorting.Facets()
        fcts.add_field("tags", allow_overlap=True)
        r = s.search(query.Every(), groupedby=fcts)
        assert r.groups("tags") == {
            "alfa": [0, 3, 4],
            "bravo": [0, 1, 4],
            "charlie": [0, 1, 2],
            "delta": [1, 2, 3],
            "echo": [2, 3, 4],
        }


def test_overlapping_lists():
    schema = fields.Schema(id=fields.STORED, tags=fields.KEYWORD)
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(id=0, tags="alfa bravo charlie")
        w.add_document(id=1, tags="bravo charlie delta")
        w.add_document(id=2, tags="charlie delta echo")
        w.add_document(id=3, tags="delta echo alfa")
        w.add_document(id=4, tags="echo alfa bravo")

    with ix.searcher() as s:
        of = sorting.FieldFacet("tags", allow_overlap=True)
        cat = of.categorizer(s)
        assert not cat._use_vectors

        r = s.search(query.Every(), groupedby={"tags": of})
        assert r.groups("tags") == {
            "alfa": [0, 3, 4],
            "bravo": [0, 1, 4],
            "charlie": [0, 1, 2],
            "delta": [1, 2, 3],
            "echo": [2, 3, 4],
        }

        fcts = sorting.Facets()
        fcts.add_field("tags", allow_overlap=True)
        r = s.search(query.Every(), groupedby=fcts)
        assert r.groups("tags") == {
            "alfa": [0, 3, 4],
            "bravo": [0, 1, 4],
            "charlie": [0, 1, 2],
            "delta": [1, 2, 3],
            "echo": [2, 3, 4],
        }


def test_field_facets():
    def check(method):
        with TempIndex(get_schema()) as ix:
            method(ix)
            with ix.searcher() as s:
                results = s.search(query.Every(), groupedby="tag")
                groups = results.groups()
                assert sorted(groups.items()) == [
                    ("one", [0, 6]),
                    ("three", [1, 3, 7, 8]),
                    ("two", [2, 4, 5]),
                ]

    check(make_single_index)
    check(make_multi_index)


def test_multifacet():
    schema = fields.Schema(tag=fields.ID(stored=True), size=fields.ID(stored=True))
    with TempIndex(schema, "multifacet") as ix:
        w = ix.writer()
        w.add_document(tag="alfa", size="small")
        w.add_document(tag="bravo", size="medium")
        w.add_document(tag="alfa", size="large")
        w.add_document(tag="bravo", size="small")
        w.add_document(tag="alfa", size="medium")
        w.add_document(tag="bravo", size="medium")
        w.commit()

        correct = {
            ("bravo", "medium"): [1, 5],
            ("alfa", "large"): [2],
            ("alfa", "medium"): [4],
            ("alfa", "small"): [0],
            ("bravo", "small"): [3],
        }

        with ix.searcher() as s:
            facet = sorting.MultiFacet(["tag", "size"])
            r = s.search(query.Every(), groupedby={"tag/size": facet})
            cats = r.groups("tag/size")
            assert cats == correct


def test_sort_filter():
    schema = fields.Schema(group=fields.ID(stored=True), key=fields.ID(stored=True))
    groups = "alfa bravo charlie".split()
    keys = "abcdefghijklmnopqrstuvwxyz"
    source = []
    for i in range(100):
        key = keys[i % len(keys)]
        group = groups[i % len(groups)]
        source.append({"key": key, "group": group})
    source.sort(key=lambda x: (x["key"], x["group"]))

    sample = list(source)
    random.shuffle(sample)

    with TempIndex(schema, "sortfilter") as ix:
        w = ix.writer()
        for i, fs in enumerate(sample):
            w.add_document(**fs)
            i += 1
            if not i % 26:
                w.commit(merge=False)
                w = ix.writer()
        w.commit()

        fq = query.Term("group", "bravo")

        with ix.searcher() as s:
            r = s.search(query.Every(), sortedby=("key", "group"), filter=fq, limit=20)
            assert [h.fields() for h in r] == [
                d for d in source if d["group"] == "bravo"
            ][:20]

            fq = query.Term("group", "bravo")
            r = s.search(
                query.Every(), sortedby=("key", "group"), filter=fq, limit=None
            )
            assert [h.fields() for h in r] == [
                d for d in source if d["group"] == "bravo"
            ]

        ix.optimize()

        with ix.searcher() as s:
            r = s.search(query.Every(), sortedby=("key", "group"), filter=fq, limit=20)
            assert [h.fields() for h in r] == [
                d for d in source if d["group"] == "bravo"
            ][:20]

            fq = query.Term("group", "bravo")
            r = s.search(
                query.Every(), sortedby=("key", "group"), filter=fq, limit=None
            )
            assert [h.fields() for h in r] == [
                d for d in source if d["group"] == "bravo"
            ]


def test_sorting_function():
    schema = fields.Schema(id=fields.STORED, text=fields.TEXT(stored=True, vector=True))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    domain = ("alfa", "bravo", "charlie")
    count = 1
    for w1 in domain:
        for w2 in domain:
            for w3 in domain:
                for w4 in domain:
                    w.add_document(id=count, text=f"{w1} {w2} {w3} {w4}")
                    count += 1
    w.commit()

    def fn(searcher, docnum):
        v = dict(searcher.vector_as("frequency", docnum, "text"))
        # Sort documents that have equal number of "alfa"
        # and "bravo" first
        return 0 - 1.0 / (abs(v.get("alfa", 0) - v.get("bravo", 0)) + 1.0)

    fnfacet = sorting.FunctionFacet(fn)

    with ix.searcher() as s:
        q = query.And([query.Term("text", "alfa"), query.Term("text", "bravo")])
        results = s.search(q, sortedby=fnfacet)
        r = [hit["text"] for hit in results]
        for t in r[:10]:
            tks = t.split()
            assert tks.count("alfa") == tks.count("bravo")


class test_translate:
    domain = [
        ("alfa", 100, 50),
        ("bravo", 20, 80),
        ("charlie", 10, 10),
        ("delta", 82, 39),
        ("echo", 20, 73),
        ("foxtrot", 81, 59),
        ("golf", 39, 93),
        ("hotel", 57, 48),
        ("india", 84, 75),
    ]

    schema = fields.Schema(
        name=fields.TEXT(sortable=True),
        a=fields.NUMERIC(sortable=True),
        b=fields.NUMERIC(sortable=True),
    )
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        for name, a, b in domain:
            w.add_document(name=u(name), a=a, b=b)

    with ix.searcher() as s:
        q = query.Every()

        # Baseline: just sort by a field
        r = s.search(q, sortedby="a")
        assert (
            " ".join([hit["name"] for hit in r])
            == "charlie bravo echo golf hotel foxtrot delta india alfa"
        )

        # Sort by reversed name
        target = [x[0] for x in sorted(domain, key=lambda x: x[0][::-1])]
        tf = sorting.TranslateFacet(lambda name: name[::-1], sorting.FieldFacet("name"))
        r = s.search(q, sortedby=tf)
        assert [hit["name"] for hit in r] == target

        # Sort by average of a and b
        def avg(a, b):
            return (a + b) / 2

        target = [x[0] for x in sorted(domain, key=lambda x: (x[1] + x[2]) / 2)]
        af = sorting.FieldFacet("a")
        bf = sorting.FieldFacet("b")
        tf = sorting.TranslateFacet(avg, af, bf)
        r = s.search(q, sortedby=tf)
        assert [hit["name"] for hit in r] == target


def test_sorted_groups():
    schema = fields.Schema(a=fields.STORED, b=fields.TEXT, c=fields.ID)
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(a=0, b="blah", c="apple")
        w.add_document(a=1, b="blah blah", c="bear")
        w.add_document(a=2, b="blah blah blah", c="apple")
        w.add_document(a=3, b="blah blah blah blah", c="bear")
        w.add_document(a=4, b="blah blah blah blah blah", c="apple")
        w.add_document(a=5, b="blah blah blah blah blah blah", c="bear")

    with ix.searcher() as s:
        q = query.Term("b", "blah")
        r = s.search(q, groupedby="c")
        gs = r.groups("c")
        assert gs["apple"] == [4, 2, 0]
        assert gs["bear"] == [5, 3, 1]


def test_group_types():
    schema = fields.Schema(a=fields.STORED, b=fields.TEXT, c=fields.ID)
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(a=0, b="blah", c="apple")
        w.add_document(a=1, b="blah blah", c="bear")
        w.add_document(a=2, b="blah blah blah", c="apple")
        w.add_document(a=3, b="blah blah blah blah", c="bear")
        w.add_document(a=4, b="blah blah blah blah blah", c="apple")
        w.add_document(a=5, b="blah blah blah blah blah blah", c="bear")
        w.add_document(a=6, b="blah blah blah blah blah blah blah", c="apple")

    with ix.searcher() as s:
        q = query.Term("b", "blah")

        f = sorting.FieldFacet("c", maptype=sorting.UnorderedList)
        r = s.search(q, groupedby=f)
        gs = r.groups()
        assert gs["apple"] == [0, 2, 4, 6]
        assert gs["bear"] == [1, 3, 5]

        f = sorting.FieldFacet("c", maptype=sorting.Count)
        r = s.search(q, groupedby=f)
        gs = r.groups()
        assert gs["apple"] == 4
        assert gs["bear"] == 3

        r = s.search(q, groupedby="c", maptype=sorting.Count)
        gs = r.groups()
        assert gs["apple"] == 4
        assert gs["bear"] == 3

        f = sorting.FieldFacet("c", maptype=sorting.Best)
        r = s.search(q, groupedby=f)
        gs = r.groups()
        assert gs["apple"] == 6
        assert gs["bear"] == 5


def test_nocachefield_segments():
    schema = fields.Schema(a=fields.ID(stored=True))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(a="bravo")
    w.add_document(a="echo")
    w.add_document(a="juliet")
    w.commit()
    w = ix.writer()
    w.add_document(a="kilo")
    w.add_document(a="foxtrot")
    w.add_document(a="charlie")
    w.commit(merge=False)
    w = ix.writer()
    w.delete_by_term("a", "echo")
    w.add_document(a="alfa")
    w.add_document(a="india")
    w.add_document(a="delta")
    w.commit(merge=False)

    with ix.searcher() as s:
        q = query.TermRange("a", "bravo", "k")
        facet = sorting.FieldFacet("a", reverse=True)

        r = s.search(q, sortedby=facet)
        assert [hit["a"] for hit in r] == [
            "juliet",
            "india",
            "foxtrot",
            "delta",
            "charlie",
            "bravo",
        ]

        mq = query.Or([query.Term("a", "bravo"), query.Term("a", "delta")])
        anq = query.AndNot(q, mq)
        r = s.search(anq, sortedby=facet)
        assert [hit["a"] for hit in r] == ["juliet", "india", "foxtrot", "charlie"]

        mq = query.Or([query.Term("a", "bravo"), query.Term("a", "delta")])
        r = s.search(q, mask=mq, sortedby=facet)
        assert [hit["a"] for hit in r] == ["juliet", "india", "foxtrot", "charlie"]

        fq = query.Or(
            [
                query.Term("a", "alfa"),
                query.Term("a", "charlie"),
                query.Term("a", "echo"),
                query.Term("a", "india"),
            ]
        )
        r = s.search(query.Every(), filter=fq, sortedby=facet)
        assert [hit["a"] for hit in r] == ["india", "charlie", "alfa"]

        nq = query.Not(query.Or([query.Term("a", "alfa"), query.Term("a", "india")]))
        r = s.search(query.Every(), filter=nq, sortedby=facet)
        assert [hit["a"] for hit in r] == [
            "kilo",
            "juliet",
            "foxtrot",
            "delta",
            "charlie",
            "bravo",
        ]


def test_groupby_phrase():
    domain = {
        "Alan Ball": "Tel Aviv",
        "Alan Charles": "San Francisco",
        "Alan Darwin": "London",
        "Alan Eames": "Paris",
    }

    schema = fields.Schema(
        name=fields.TEXT(stored=True),
        city=fields.TEXT(stored=True),
        city_g=fields.ID(stored=True),
    )
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        for name, city in domain.items():
            w.add_document(name=u(name), city=u(city), city_g=u(city))

    with ix.searcher() as s:
        q = query.Term("name", "alan")
        r = s.search(q, groupedby="city_g")
        keys = sorted(r.groups().keys())
        assert keys == ["London", "Paris", "San Francisco", "Tel Aviv"]

        sff = sorting.StoredFieldFacet("city")
        r = s.search(q, groupedby=sff)
        keys = sorted(r.groups().keys())
        assert keys == ["London", "Paris", "San Francisco", "Tel Aviv"]


def test_sort_text_field():
    domain = (
        ("Visual Display of Quantitative Information, The", 10),
        ("Envisioning Information", 10),
        ("Visual Explanations", 10),
        ("Beautiful Evidence", -10),
        ("Visual and Statistical Thinking", -10),
        ("Cognitive Style of Powerpoint", -10),
    )
    sorted_titles = sorted(d[0] for d in domain)

    schema = fields.Schema(
        title=fields.TEXT(stored=True, sortable=True), num=fields.NUMERIC(sortable=True)
    )

    def test(ix):
        with ix.searcher() as s:
            # Sort by title
            r = s.search(query.Every(), sortedby="title")
            titles = [hit["title"] for hit in r]
            assert titles == sorted_titles

            # Sort by reverse title
            facet = sorting.FieldFacet("title", reverse=True)
            r = s.search(query.Every(), sortedby=facet)
            assert [hit["title"] for hit in r] == list(reversed(sorted_titles))

            # Sort by num (-10 to 10) first, and within that, by reverse title
            facet = sorting.MultiFacet()
            facet.add_field("num")
            facet.add_field("title", reverse=True)

            r = s.search(query.Every(), sortedby=facet)
            target = [
                "Visual and Statistical Thinking",
                "Cognitive Style of Powerpoint",
                "Beautiful Evidence",
                "Visual Explanations",
                "Visual Display of Quantitative Information, The",
                "Envisioning Information",
            ]
            assert [hit["title"] for hit in r] == target

    # Single segment
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            for title, num in domain:
                w.add_document(title=u(title), num=num)
        test(ix)

    # Multisegment
    with TempIndex(schema) as ix:
        # Segment 1
        with ix.writer() as w:
            for title, num in domain[:3]:
                w.add_document(title=u(title), num=num)
        # Segment 2
        with ix.writer() as w:
            for title, num in domain[3:]:
                w.add_document(title=u(title), num=num)
            w.merge = False
        test(ix)


def test_filtered_grouped():
    schema = fields.Schema(tag=fields.ID, text=fields.TEXT(stored=True))
    ix = RamStorage().create_index(schema)
    domain = "alfa bravo charlie delta echo foxtrot".split()

    with ix.writer() as w:
        for i, ls in enumerate(permutations(domain, 3)):
            tag = str(i % 3)
            w.add_document(tag=tag, text=" ".join(ls))

    with ix.searcher() as s:
        f = query.And([query.Term("text", "charlie"), query.Term("text", "delta")])
        r = s.search(query.Every(), filter=f, groupedby="tag", limit=None)
        assert len(r) == 24


def test_add_sortable():
    st = RamStorage()
    schema = fields.Schema(chapter=fields.ID(stored=True), price=fields.NUMERIC)
    ix = st.create_index(schema)
    with ix.writer() as w:
        w.add_document(chapter="alfa", price=100)
        w.add_document(chapter="bravo", price=200)
        w.add_document(chapter="charlie", price=300)
        w.add_document(chapter="delta", price=400)
    with ix.writer() as w:
        w.add_document(chapter="bravo", price=500)
        w.add_document(chapter="alfa", price=600)
        w.add_document(chapter="delta", price=100)
        w.add_document(chapter="charlie", price=200)
        w.merge = False

    with ix.reader() as r:
        assert not r.has_column("chapter")
        assert not r.has_column("price")

    with ix.writer() as w:
        sorting.add_sortable(w, "chapter", sorting.StoredFieldFacet("chapter"))
        sorting.add_sortable(w, "price", sorting.FieldFacet("price"))
        w.merge = False

    with ix.reader() as r:
        assert r.has_column("chapter")
        assert r.has_column("price")

        chapr = r.column_reader("chapter")
        pricer = r.column_reader("price")

        assert chapr[0] == "alfa"
        assert pricer[0] == 100

    ix.optimize()

    with ix.reader() as r:
        assert r.has_column("chapter")
        assert r.has_column("price")

        chapr = r.column_reader("chapter")
        pricer = r.column_reader("price")

        assert chapr[0] == "alfa"
        assert pricer[0] == 100


def test_missing_column():
    from whoosh import collectors

    schema = fields.Schema(id=fields.STORED, tags=fields.KEYWORD)
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(id=0, tags="alfa bravo charlie")
        w.add_document(id=1, tags="bravo charlie delta")
        w.add_document(id=2, tags="charlie delta echo")
        w.merge = False

    with ix.writer() as w:
        w.add_field("age", fields.NUMERIC(sortable=True))

        w.add_document(id=3, tags="delta echo foxtrot", age=10)
        w.add_document(id=4, tags="echo foxtrot golf", age=5)
        w.add_document(id=5, tags="foxtrot golf alfa", age=20)
        w.merge = False

    with ix.writer() as w:
        w.add_document(id=6, tags="golf alfa bravo", age=2)
        w.add_document(id=7, tags="alfa hotel india", age=50)
        w.add_document(id=8, tags="hotel india bravo", age=15)
        w.merge = False

    with ix.searcher() as s:
        assert not s.is_atomic()

        q = query.Term("tags", "alfa")

        # Have to use yucky low-level collector API to make sure we used a
        # ColumnCategorizer to do the sorting
        c = s.collector(sortedby="age")
        assert isinstance(c, collectors.SortingCollector)
        s.search_with_collector(q, c)
        assert isinstance(c.categorizer, sorting.ColumnCategorizer)

        r = c.results()
        assert [hit["id"] for hit in r] == [6, 5, 7, 0]

        r = s.search(q, sortedby="age", reverse=True)
        assert [hit["id"] for hit in r] == [0, 7, 5, 6]


def test_compound_sort():
    fspec = fields.KEYWORD(stored=True, sortable=True)
    schema = fields.Schema(a=fspec, b=fspec, c=fspec)
    ix = RamStorage().create_index(schema)

    alist = "alfa bravo alfa bravo alfa bravo alfa bravo alfa bravo".split()
    blist = "alfa bravo charlie alfa bravo charlie alfa bravo charlie alfa".split()
    clist = "alfa bravo charlie delta echo foxtrot golf hotel india juliet".split()
    assert all(len(ls) == 10 for ls in (alist, blist, clist))

    with ix.writer() as w:
        for i in range(10):
            w.add_document(a=alist[i], b=blist[i], c=clist[i])

    with ix.searcher() as s:
        q = query.Every()
        sortedby = [
            sorting.FieldFacet("a"),
            sorting.FieldFacet("b", reverse=True),
            sorting.FieldFacet("c"),
        ]

        r = s.search(q, sortedby=sortedby)
        output = [" ".join((hit["a"], hit["b"], hit["c"])) for hit in r]
        assert output == [
            "alfa charlie charlie",
            "alfa charlie india",
            "alfa bravo echo",
            "alfa alfa alfa",
            "alfa alfa golf",
            "bravo charlie foxtrot",
            "bravo bravo bravo",
            "bravo bravo hotel",
            "bravo alfa delta",
            "bravo alfa juliet",
        ]


def test_column_scoring():
    from whoosh import scoring

    # "sortable=True" on the "id" field tells it to build a column store
    # of field values. If you didn't ever need to actually search on this field,
    # you could get JUST the column using count=fields.COLUMN
    schema = fields.Schema(id=fields.ID(sortable=True), tag=fields.KEYWORD)

    class MyWeighting(scoring.WeightingModel):
        def scorer(self, searcher, fieldname, text, qf=1):
            # Pass the searcher to the scorer so it can look up values in the
            # "count" field
            return MyScorer(searcher)

    class MyScorer(scoring.BaseScorer):
        def __init__(self, searcher):
            self.searcher = searcher
            # Get a column value reader for the "id" field
            self.col = searcher.reader().column_reader("id")

        def score(self, matcher):
            # Get the document number of the current match
            docnum = matcher.id()
            # Use the value from the column as the score
            # Note: the return value must be a number, so for this contrived
            # example we'll call ord() on the ID letter
            id_value = self.col[docnum]
            return ord(id_value)

    with TempIndex(schema) as ix:
        with ix.writer() as w:
            w.add_document(id="a", tag="foo")
            w.add_document(id="b", tag="foo")
            w.add_document(id="c", tag="foo")
            w.add_document(id="d", tag="foo")

        with ix.searcher(weighting=MyWeighting()) as s:
            r = s.search(query.Term("tag", "foo"))
            # Note that higher scores are better, so higher letters come first
            assert [hit["id"] for hit in r] == ["d", "c", "b", "a"]
