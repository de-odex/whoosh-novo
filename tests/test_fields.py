from datetime import datetime, timedelta, timezone

import pytest

from whoosh import fields, qparser, query
from whoosh.filedb.filestore import RamStorage
from whoosh.util import times
from whoosh.util.testing import TempIndex


def test_schema_eq():
    a = fields.Schema()
    b = fields.Schema()
    assert a == b

    a = fields.Schema(id=fields.ID)
    b = a.copy()
    assert a["id"] == b["id"]
    assert a == b

    c = fields.Schema(id=fields.TEXT)
    assert a != c


def test_creation1():
    s = fields.Schema()
    s.add("content", fields.TEXT(phrase=True))
    s.add("title", fields.TEXT(stored=True))
    s.add("path", fields.ID(stored=True))
    s.add("tags", fields.KEYWORD(stored=True))
    s.add("quick", fields.NGRAM)
    s.add("note", fields.STORED)

    assert s.names() == ["content", "note", "path", "quick", "tags", "title"]
    assert "content" in s
    assert "buzz" not in s
    assert isinstance(s["tags"], fields.KEYWORD)


def test_creation2():
    s = fields.Schema(
        a=fields.ID(stored=True), b=fields.ID, c=fields.KEYWORD(scorable=True)
    )

    assert s.names() == ["a", "b", "c"]
    assert "a" in s
    assert "b" in s
    assert "c" in s


def test_declarative():
    class MySchema(fields.SchemaClass):
        content = fields.TEXT
        title = fields.TEXT
        path = fields.ID
        date = fields.DATETIME

    ix = RamStorage().create_index(MySchema)
    assert ix.schema.names() == ["content", "date", "path", "title"]

    ix = RamStorage().create_index(MySchema())
    assert ix.schema.names() == ["content", "date", "path", "title"]

    with pytest.raises(fields.FieldConfigurationError):
        RamStorage().create_index(object())


def test_declarative_inherit():
    class Parent(fields.SchemaClass):
        path = fields.ID
        date = fields.DATETIME

    class Child(Parent):
        content = fields.TEXT

    class Grandchild(Child):
        title = fields.TEXT

    s = Grandchild()
    assert s.names() == ["content", "date", "path", "title"]


def test_badnames():
    s = fields.Schema()
    with pytest.raises(fields.FieldConfigurationError):
        s.add("_test", fields.ID)
    with pytest.raises(fields.FieldConfigurationError):
        s.add("a f", fields.ID)


# def test_numeric_support():
#    intf = fields.NUMERIC(int, shift_step=0)
#    longf = fields.NUMERIC(int, bits=64, shift_step=0)
#    floatf = fields.NUMERIC(float, shift_step=0)
#
#    def roundtrip(obj, num):
#        assert obj.from_bytes(obj.to_bytes(num)), num)
#
#    roundtrip(intf, 0)
#    roundtrip(intf, 12345)
#    roundtrip(intf, -12345)
#    roundtrip(longf, 0)
#    roundtrip(longf, 85020450482)
#    roundtrip(longf, -85020450482)
#    roundtrip(floatf, 0)
#    roundtrip(floatf, 582.592)
#    roundtrip(floatf, -582.592)
#    roundtrip(floatf, -99.42)
#
#    from random import shuffle
#
#    def roundtrip_sort(obj, start, end, step):
#        count = start
#        rng = []
#        while count < end:
#            rng.append(count)
#            count += step
#
#        scrabled = list(rng)
#        shuffle(scrabled)
#        round = [obj.from_text(t) for t
#                 in sorted([obj.to_text(n) for n in scrabled])]
#        assert round, rng)
#
#    roundtrip_sort(intf, -100, 100, 1)
#    roundtrip_sort(longf, -58902, 58249, 43)
#    roundtrip_sort(floatf, -99.42, 99.83, 2.38)


def test_index_numeric():
    schema = fields.Schema(
        a=fields.NUMERIC(int, 32, signed=False), b=fields.NUMERIC(int, 32, signed=True)
    )
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(a=1, b=1)
    with ix.searcher() as s:
        assert list(s.lexicon("a")) == [
            b"\x00\x00\x00\x00\x01",
            b"\x04\x00\x00\x00\x00",
            b"\x08\x00\x00\x00\x00",
            b"\x0c\x00\x00\x00\x00",
            b"\x10\x00\x00\x00\x00",
            b"\x14\x00\x00\x00\x00",
            b"\x18\x00\x00\x00\x00",
            b"\x1c\x00\x00\x00\x00",
        ]
        assert list(s.lexicon("b")) == [
            b"\x00\x80\x00\x00\x01",
            b"\x04\x08\x00\x00\x00",
            b"\x08\x00\x80\x00\x00",
            b"\x0c\x00\x08\x00\x00",
            b"\x10\x00\x00\x80\x00",
            b"\x14\x00\x00\x08\x00",
            b"\x18\x00\x00\x00\x80",
            b"\x1c\x00\x00\x00\x08",
        ]


def test_numeric():
    schema = fields.Schema(
        id=fields.ID(stored=True),
        integer=fields.NUMERIC(int),
        floating=fields.NUMERIC(float),
    )
    ix = RamStorage().create_index(schema)

    w = ix.writer()
    w.add_document(id="a", integer=5820, floating=1.2)
    w.add_document(id="b", integer=22, floating=2.3)
    w.add_document(id="c", integer=78, floating=3.4)
    w.add_document(id="d", integer=13, floating=4.5)
    w.add_document(id="e", integer=9, floating=5.6)
    w.commit()

    with ix.searcher() as s:
        qp = qparser.QueryParser("integer", schema)

        q = qp.parse("5820")
        r = s.search(q)
        assert len(r) == 1
        assert r[0]["id"] == "a"

    with ix.searcher() as s:
        r = s.search(qp.parse("floating:4.5"))
        assert len(r) == 1
        assert r[0]["id"] == "d"

    q = qp.parse("integer:*")
    assert q.__class__ == query.Every
    assert q.field() == "integer"

    q = qp.parse("integer:5?6")
    assert q == query.NullQuery


def test_decimal_numeric():
    from decimal import Decimal

    f = fields.NUMERIC(int, decimal_places=4)
    schema = fields.Schema(id=fields.ID(stored=True), deci=f)
    ix = RamStorage().create_index(schema)

    # assert f.from_text(f.to_text(Decimal("123.56"))), Decimal("123.56"))

    w = ix.writer()
    w.add_document(id="a", deci=Decimal("123.56"))
    w.add_document(id="b", deci=Decimal("0.536255"))
    w.add_document(id="c", deci=Decimal("2.5255"))
    w.add_document(id="d", deci=Decimal("58"))
    w.commit()

    with ix.searcher() as s:
        qp = qparser.QueryParser("deci", schema)
        q = qp.parse("123.56")
        r = s.search(q)
        assert len(r) == 1
        assert r[0]["id"] == "a"

        r = s.search(qp.parse("0.536255"))
        assert len(r) == 1
        assert r[0]["id"] == "b"


def test_numeric_parsing():
    schema = fields.Schema(id=fields.ID(stored=True), number=fields.NUMERIC)

    qp = qparser.QueryParser("number", schema)
    q = qp.parse("[10 to *]")
    assert q == query.NullQuery

    q = qp.parse("[to 400]")
    assert q.__class__ is query.NumericRange
    assert q.start is None
    assert q.end == 400

    q = qp.parse("[10 to]")
    assert q.__class__ is query.NumericRange
    assert q.start == 10
    assert q.end is None

    q = qp.parse("[10 to 400]")
    assert q.__class__ is query.NumericRange
    assert q.start == 10
    assert q.end == 400


def test_numeric_ranges():
    schema = fields.Schema(id=fields.STORED, num=fields.NUMERIC)
    ix = RamStorage().create_index(schema)
    w = ix.writer()

    for i in range(400):
        w.add_document(id=i, num=i)
    w.commit()

    with ix.searcher() as s:
        qp = qparser.QueryParser("num", schema)

        def check(qs, target):
            q = qp.parse(qs)
            result = [s.stored_fields(d)["id"] for d in q.docs(s)]
            assert result == target

        # Note that range() is always inclusive-exclusive
        check("[10 to 390]", list(range(10, 390 + 1)))
        check("[100 to]", list(range(100, 400)))
        check("[to 350]", list(range(0, 350 + 1)))
        check("[16 to 255]", list(range(16, 255 + 1)))
        check("{10 to 390]", list(range(11, 390 + 1)))
        check("[10 to 390}", list(range(10, 390)))
        check("{10 to 390}", list(range(11, 390)))
        check("{16 to 255}", list(range(17, 255)))


def test_numeric_ranges_unsigned():
    values = [1, 10, 100, 1000, 2, 20, 200, 2000, 9, 90, 900, 9000]
    schema = fields.Schema(num2=fields.NUMERIC(stored=True, signed=False))

    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        for v in values:
            w.add_document(num2=v)

    with ix.searcher() as s:
        q = query.NumericRange("num2", 55, None, True, False)
        r = s.search(q, limit=None)
        for hit in r:
            assert int(hit["num2"]) >= 55


def test_decimal_ranges():
    from decimal import Decimal

    schema = fields.Schema(id=fields.STORED, num=fields.NUMERIC(int, decimal_places=2))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    count = Decimal("0.0")
    inc = Decimal("0.2")
    for _ in range(500):
        w.add_document(id=str(count), num=count)
        count += inc
    w.commit()

    with ix.searcher() as s:
        qp = qparser.QueryParser("num", schema)

        def check(qs, start, end):
            q = qp.parse(qs)
            result = [s.stored_fields(d)["id"] for d in q.docs(s)]

            target = []
            count = Decimal(start)
            limit = Decimal(end)
            while count <= limit:
                target.append(str(count))
                count += inc

            assert result == target

        check("[10.2 to 80.8]", "10.2", "80.8")
        check("{10.2 to 80.8]", "10.4", "80.8")
        check("[10.2 to 80.8}", "10.2", "80.6")
        check("{10.2 to 80.8}", "10.4", "80.6")


def test_numeric_errors():
    f = fields.NUMERIC(int, bits=16, signed=True)
    schema = fields.Schema(f=f)

    with pytest.raises(ValueError):
        list(f.index(-32769))
    with pytest.raises(ValueError):
        list(f.index(32768))


def test_nontext_document():
    schema = fields.Schema(
        id=fields.STORED, num=fields.NUMERIC, date=fields.DATETIME, even=fields.BOOLEAN
    )
    ix = RamStorage().create_index(schema)

    dt = datetime.now(tz=timezone.utc)
    w = ix.writer()
    for i in range(50):
        w.add_document(id=i, num=i, date=dt + timedelta(days=i), even=not (i % 2))
    w.commit()

    with ix.searcher() as s:

        def check(kwargs, target):
            result = [d["id"] for d in s.documents(**kwargs)]
            assert result == target

        check({"num": 49}, [49])
        check({"date": dt + timedelta(days=30)}, [30])
        check({"even": True}, list(range(0, 50, 2)))


def test_nontext_update():
    schema = fields.Schema(
        id=fields.STORED,
        num=fields.NUMERIC(unique=True),
        date=fields.DATETIME(unique=True),
    )
    ix = RamStorage().create_index(schema)

    dt = datetime.now(tz=timezone.utc)
    w = ix.writer()
    for i in range(10):
        w.add_document(id=i, num=i, date=dt + timedelta(days=i))
    w.commit()

    w = ix.writer()
    w.update_document(num=8, id="a")
    w.update_document(num=2, id="b")
    w.update_document(num=4, id="c")
    w.update_document(date=dt + timedelta(days=5), id="d")
    w.update_document(date=dt + timedelta(days=1), id="e")
    w.update_document(date=dt + timedelta(days=7), id="f")
    w.commit()


def test_datetime():
    dtf = fields.DATETIME(stored=True)
    schema = fields.Schema(id=fields.ID(stored=True), date=dtf)
    st = RamStorage()
    ix = st.create_index(schema)

    w = ix.writer()
    for month in range(1, 12):
        for day in range(1, 28):
            w.add_document(
                id=f"{month}-{day}",
                date=datetime(2010, month, day, 14, 0, 0, tzinfo=timezone.utc),
            )
    w.commit()

    with ix.searcher() as s:
        qp = qparser.QueryParser("id", schema)

        r = s.search(qp.parse("date:20100523"))
        assert len(r) == 1
        assert r[0]["id"] == "5-23"
        assert r[0]["date"].__class__ is datetime
        assert r[0]["date"].month == 5
        assert r[0]["date"].day == 23

        r = s.search(qp.parse("date:'2010 02'"))
        assert len(r) == 27

        q = qp.parse("date:[2010-05 to 2010-08]")
        startdt = datetime(2010, 5, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
        enddt = datetime(2010, 8, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
        assert q.__class__ is query.NumericRange
        assert q.start == times.datetime_to_long(startdt)
        assert q.end == times.datetime_to_long(enddt)


def test_boolean():
    schema = fields.Schema(id=fields.ID(stored=True), done=fields.BOOLEAN(stored=True))
    ix = RamStorage().create_index(schema)

    w = ix.writer()
    w.add_document(id="a", done=True)
    w.add_document(id="b", done=False)
    w.add_document(id="c", done=True)
    w.add_document(id="d", done=False)
    w.add_document(id="e", done=True)
    w.commit()

    with ix.searcher() as s:
        qp = qparser.QueryParser("id", schema)

        r = s.search(qp.parse("done:true"))
        assert sorted([d["id"] for d in r]) == ["a", "c", "e"]
        assert all(d["done"] for d in r)

        r = s.search(qp.parse("done:yes"))
        assert sorted([d["id"] for d in r]) == ["a", "c", "e"]
        assert all(d["done"] for d in r)

        q = qp.parse("done:false")
        assert q.__class__ == query.Term
        assert q.text is False
        assert schema["done"].to_bytes(False) == b"f"
        r = s.search(q)
        assert sorted([d["id"] for d in r]) == ["b", "d"]
        assert not any(d["done"] for d in r)

        r = s.search(qp.parse("done:no"))
        assert sorted([d["id"] for d in r]) == ["b", "d"]
        assert not any(d["done"] for d in r)


def test_boolean2():
    schema = fields.Schema(t=fields.TEXT(stored=True), b=fields.BOOLEAN(stored=True))
    ix = RamStorage().create_index(schema)
    writer = ix.writer()
    writer.add_document(t="some kind of text", b=False)
    writer.add_document(t="some other kind of text", b=False)
    writer.add_document(t="some more text", b=False)
    writer.add_document(t="some again", b=True)
    writer.commit()

    with ix.searcher() as s:
        qf = qparser.QueryParser("b", None).parse("f")
        qt = qparser.QueryParser("b", None).parse("t")
        r = s.search(qf)
        assert len(r) == 3

        assert [d["b"] for d in s.search(qt)] == [True]
        assert [d["b"] for d in s.search(qf)] == [False] * 3


def test_boolean3():
    schema = fields.Schema(
        t=fields.TEXT(stored=True, field_boost=5),
        b=fields.BOOLEAN(stored=True),
        c=fields.TEXT,
    )
    ix = RamStorage().create_index(schema)

    with ix.writer() as w:
        w.add_document(t="with hardcopy", b=True, c="alfa")
        w.add_document(t="no hardcopy", b=False, c="bravo")

    with ix.searcher() as s:
        q = query.Term("b", schema["b"].to_bytes(True))
        ts = [hit["t"] for hit in s.search(q)]
        assert ts == ["with hardcopy"]


def test_boolean_strings():
    schema = fields.Schema(i=fields.STORED, b=fields.BOOLEAN(stored=True))
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(i=0, b="true")
        w.add_document(i=1, b="True")
        w.add_document(i=2, b="false")
        w.add_document(i=3, b="False")
        w.add_document(i=4, b="true")
        w.add_document(i=5, b="True")
        w.add_document(i=6, b="false")
        w.add_document(i=7, b="False")

    with ix.searcher() as s:
        qp = qparser.QueryParser("b", ix.schema)

        def check(qs, nums):
            q = qp.parse(qs)
            r = s.search(q, limit=None)
            assert [hit["i"] for hit in r] == nums

        trues = [0, 1, 4, 5]
        falses = [2, 3, 6, 7]
        check("true", trues)
        check("True", trues)
        check("false", falses)
        check("False", falses)
        check("t", trues)
        check("f", falses)


def test_boolean_find_deleted():
    # "Random" string of ones and zeros representing deleted and undeleted
    domain = "1110001010001110010101000101001011101010001011111101000101010101"

    schema = fields.Schema(i=fields.STORED, b=fields.BOOLEAN(stored=True))
    ix = RamStorage().create_index(schema)
    count = 0
    # Create multiple segments just in case
    for _ in range(5):
        w = ix.writer()
        for c in domain:
            w.add_document(i=count, b=(c == "1"))
        w.commit(merge=False)

    # Delete documents where "b" is True
    with ix.writer() as w:
        w.delete_by_term("b", "t")

    with ix.searcher() as s:
        # Double check that documents with b=True are all deleted
        reader = s.reader()
        for docnum in range(s.doc_count_all()):
            b = s.stored_fields(docnum)["b"]
            assert b == reader.is_deleted(docnum)

        # Try doing a search for documents where b=True
        qp = qparser.QueryParser("b", ix.schema)
        q = qp.parse("b:t")
        r = s.search(q, limit=None)
        assert len(r) == 0

        # Make sure Every query doesn't match deleted docs
        r = s.search(qp.parse("*"), limit=None)
        assert not any(hit["b"] for hit in r)
        assert not any(reader.is_deleted(hit.docnum) for hit in r)

        r = s.search(qp.parse("*:*"), limit=None)
        assert not any(hit["b"] for hit in r)
        assert not any(reader.is_deleted(hit.docnum) for hit in r)

        # Make sure Not query doesn't match deleted docs
        q = qp.parse("NOT b:t")
        r = s.search(q, limit=None)
        assert not any(hit["b"] for hit in r)
        assert not any(reader.is_deleted(hit.docnum) for hit in r)

        r = s.search(q, limit=5)
        assert not any(hit["b"] for hit in r)
        assert not any(reader.is_deleted(hit.docnum) for hit in r)


def test_boolean_multifield():
    schema = fields.Schema(
        name=fields.TEXT(stored=True), bit=fields.BOOLEAN(stored=True)
    )
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(name="audi", bit=True)
        w.add_document(name="vw", bit=False)
        w.add_document(name="porsche", bit=False)
        w.add_document(name="ferrari", bit=True)
        w.add_document(name="citroen", bit=False)

    with ix.searcher() as s:
        qp = qparser.MultifieldParser(["name", "bit"], schema)
        q = qp.parse("boop")

        r = s.search(q)
        assert sorted(hit["name"] for hit in r) == ["audi", "ferrari"]
        assert len(r) == 2


def test_idlist():
    schema = fields.Schema(paths=fields.IDLIST(stored=True))
    ix = RamStorage().create_index(schema)

    with ix.writer() as w:
        w.add_document(paths="here there everywhere")
        w.add_document(paths="here")
        w.add_document(paths="there")

    with ix.searcher() as s:
        qp = qparser.QueryParser("paths", schema)
        q = qp.parse("here")

        r = s.search(q)
        assert sorted(hit["paths"] for hit in r) == ["here", "here there everywhere"]


def test_missing_field():
    schema = fields.Schema()
    ix = RamStorage().create_index(schema)

    with ix.searcher() as s:
        with pytest.raises(KeyError):
            s.document_numbers(id="test")


def test_token_boost():
    from whoosh.analysis import DoubleMetaphoneFilter, RegexTokenizer

    ana = RegexTokenizer() | DoubleMetaphoneFilter()
    field = fields.TEXT(analyzer=ana, phrase=False)
    results = sorted(field.index("spruce view"))
    assert results == [
        (b"F", 1, 1.0, b"\x00\x00\x00\x01"),
        (b"FF", 1, 0.5, b"\x00\x00\x00\x01"),
        (b"SPRS", 1, 1.0, b"\x00\x00\x00\x01"),
    ]


def test_pickle_idlist():
    schema = fields.Schema(
        pk=fields.ID(stored=True, unique=True),
        text=fields.TEXT(),
        tags=fields.IDLIST(stored=True),
    )
    with TempIndex(schema) as ix:
        assert ix


def test_pickle_schema():
    from pickle import dumps

    from whoosh import analysis
    from whoosh.support.charset import accent_map

    freetext_analyzer = analysis.StemmingAnalyzer() | analysis.CharsetFilter(accent_map)

    schema = fields.Schema(
        path=fields.ID(stored=True, unique=True),
        file_mtime=fields.DATETIME(stored=True),
        name=fields.TEXT(stored=False, field_boost=2.0),
        description=fields.TEXT(
            stored=False, field_boost=1.5, analyzer=freetext_analyzer
        ),
        content=fields.TEXT(analyzer=freetext_analyzer),
    )

    # Try to make some sentences that will require stemming
    docs = [
        "The rain in spain falls mainly in the plain",
        "Plainly sitting on the plain",
        "Imagine a greatly improved sentence here",
    ]

    with TempIndex(schema) as ix:
        with ix.writer() as w:
            for doc in docs:
                w.add_document(description=doc, content=doc)

        assert dumps(schema, 2)

        with ix.reader() as r:
            assert dumps(r.schema, 2)


def test_valid_date_string():
    """Can parse a valid date string and return a NumericRange query with the parsed date as the value"""
    import datetime

    from whoosh.fields import DATETIME, datetime_to_long
    from whoosh.query import NumericRange

    # Initialize the DATETIME field
    field = DATETIME()

    # Define a valid date string
    date_string = "2022-01-01"

    # Invoke the parse_query method with the valid date string
    query = field.parse_query("date", date_string)

    # Define the expected start and end dates
    expected_start = datetime_to_long(
        datetime.datetime(2022, 1, 1, tzinfo=timezone.utc)
    )
    expected_end = datetime_to_long(
        datetime.datetime(2022, 1, 1, tzinfo=timezone.utc)
        + datetime.timedelta(days=1)
        - datetime.timedelta(microseconds=1)
    )

    # Check that the query is a NumericRange query with the parsed date as the value
    assert isinstance(query, NumericRange), "Query is not a NumericRange"
    assert query.fieldname == "date", "Fieldname is not correct"
    assert query.start == expected_start, "Start date is not correct"
    assert query.end == expected_end, "End date is not correct"
    assert query.boost == 1.0, "Boost value is not correct"
