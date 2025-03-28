import random
from collections import defaultdict
from datetime import datetime, timezone
from itertools import permutations

import pytest

from whoosh import __version__, analysis, fields, index, qparser, query
from whoosh.filedb.filestore import RamStorage
from whoosh.util.numeric import byte_to_length, length_to_byte
from whoosh.util.testing import TempIndex, TempStorage
from whoosh.writing import IndexingError


def test_creation():
    s = fields.Schema(
        content=fields.TEXT(phrase=True),
        title=fields.TEXT(stored=True),
        path=fields.ID(stored=True),
        tags=fields.KEYWORD(stored=True),
        quick=fields.NGRAM,
        note=fields.STORED,
    )
    st = RamStorage()

    ix = st.create_index(s)
    w = ix.writer()
    w.add_document(
        title="First",
        content="This is the first document",
        path="/a",
        tags="first second third",
        quick="First document",
        note="This is the first document",
    )
    w.add_document(
        content="Let's try this again",
        title="Second",
        path="/b",
        tags="Uno Dos Tres",
        quick="Second document",
        note="This is the second document",
    )
    w.commit()


def test_empty_commit():
    s = fields.Schema(id=fields.ID(stored=True))
    with TempIndex(s, "emptycommit") as ix:
        w = ix.writer()
        w.add_document(id="1")
        w.add_document(id="2")
        w.add_document(id="3")
        w.commit()

        w = ix.writer()
        w.commit()


def test_version_in():
    with TempStorage("versionin") as st:
        assert not index.exists(st)

        schema = fields.Schema(text=fields.TEXT)
        ix = st.create_index(schema)
        assert index.exists(st)
        assert ix.is_empty()

        v = index.version(st)
        assert v[0] == __version__
        assert v[1] == index._CURRENT_TOC_VERSION

        with ix.writer() as w:
            w.add_document(text="alfa")

        assert not ix.is_empty()


def test_simple_indexing():
    schema = fields.Schema(text=fields.TEXT, id=fields.STORED)
    domain = (
        "alfa",
        "bravo",
        "charlie",
        "delta",
        "echo",
        "foxtrot",
        "golf",
        "hotel",
        "india",
        "juliet",
        "kilo",
        "lima",
        "mike",
        "november",
    )
    docs = defaultdict(list)
    with TempIndex(schema, "simple") as ix:
        with ix.writer() as w:
            for i in range(100):
                smp = random.sample(domain, 5)
                for word in smp:
                    docs[word].append(i)
                w.add_document(text=" ".join(smp), id=i)

        with ix.searcher() as s:
            for word in domain:
                rset = sorted(
                    [
                        hit["id"]
                        for hit in s.search(query.Term("text", word), limit=None)
                    ]
                )
                assert rset == docs[word]


def test_integrity():
    s = fields.Schema(name=fields.TEXT, value=fields.TEXT)
    st = RamStorage()
    ix = st.create_index(s)

    w = ix.writer()
    w.add_document(name="Yellow brown", value="Blue red green purple?")
    w.add_document(name="Alpha beta", value="Gamma delta epsilon omega.")
    w.commit()

    w = ix.writer()
    w.add_document(name="One two", value="Three four five.")
    w.commit()

    tr = ix.reader()
    assert ix.doc_count_all() == 3
    assert " ".join(tr.field_terms("name")) == "alpha beta brown one two yellow"


def test_lengths():
    s = fields.Schema(
        f1=fields.KEYWORD(stored=True, scorable=True),
        f2=fields.KEYWORD(stored=True, scorable=True),
    )
    with TempIndex(s, "testlengths") as ix:
        w = ix.writer()
        items = "ABCDEFG"
        from itertools import cycle, islice

        lengths = [10, 20, 2, 102, 45, 3, 420, 2]
        for length in lengths:
            w.add_document(f2=" ".join(islice(cycle(items), length)))
        w.commit()

        with ix.reader() as dr:
            ls1 = [dr.doc_field_length(i, "f1") for i in range(0, len(lengths))]
            assert ls1 == [0] * len(lengths)
            ls2 = [dr.doc_field_length(i, "f2") for i in range(0, len(lengths))]
            assert ls2 == [byte_to_length(length_to_byte(l)) for l in lengths]


def test_many_lengths():
    domain = "alfa bravo charlie delta echo".split()
    schema = fields.Schema(text=fields.TEXT)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    for i, word in enumerate(domain):
        length = (i + 1) ** 6
        w.add_document(text=" ".join(word for _ in range(length)))
    w.commit()

    s = ix.searcher()
    for i, word in enumerate(domain):
        target = byte_to_length(length_to_byte((i + 1) ** 6))
        ti = s.term_info("text", word)
        assert ti.min_length() == target
        assert ti.max_length() == target


def test_lengths_ram():
    s = fields.Schema(
        f1=fields.KEYWORD(stored=True, scorable=True),
        f2=fields.KEYWORD(stored=True, scorable=True),
    )
    st = RamStorage()
    ix = st.create_index(s)
    w = ix.writer()
    w.add_document(f1="A B C D E", f2="X Y Z")
    w.add_document(f1="B B B B C D D Q", f2="Q R S T")
    w.add_document(f1="D E F", f2="U V A B C D E")
    w.commit()

    dr = ix.reader()
    assert dr.stored_fields(0)["f1"] == "A B C D E"
    assert dr.doc_field_length(0, "f1") == 5
    assert dr.doc_field_length(1, "f1") == 8
    assert dr.doc_field_length(2, "f1") == 3
    assert dr.doc_field_length(0, "f2") == 3
    assert dr.doc_field_length(1, "f2") == 4
    assert dr.doc_field_length(2, "f2") == 7

    assert dr.field_length("f1") == 16
    assert dr.field_length("f2") == 14
    assert dr.max_field_length("f1") == 8
    assert dr.max_field_length("f2") == 7


def test_merged_lengths():
    s = fields.Schema(
        f1=fields.KEYWORD(stored=True, scorable=True),
        f2=fields.KEYWORD(stored=True, scorable=True),
    )
    with TempIndex(s, "mergedlengths") as ix:
        w = ix.writer()
        w.add_document(f1="A B C", f2="X")
        w.add_document(f1="B C D E", f2="Y Z")
        w.commit()

        w = ix.writer()
        w.add_document(f1="A", f2="B C D E X Y")
        w.add_document(f1="B C", f2="X")
        w.commit(merge=False)

        w = ix.writer()
        w.add_document(f1="A B X Y Z", f2="B C")
        w.add_document(f1="Y X", f2="A B")
        w.commit(merge=False)

        with ix.reader() as dr:
            assert dr.stored_fields(0)["f1"] == "A B C"
            assert dr.doc_field_length(0, "f1") == 3
            assert dr.doc_field_length(2, "f2") == 6
            assert dr.doc_field_length(4, "f1") == 5


def test_frequency_keyword():
    s = fields.Schema(content=fields.KEYWORD)
    st = RamStorage()
    ix = st.create_index(s)

    w = ix.writer()
    w.add_document(content="A B C D E")
    w.add_document(content="B B B B C D D")
    w.add_document(content="D E F")
    w.commit()

    with ix.reader() as tr:
        assert tr.doc_frequency("content", "B") == 2
        assert tr.frequency("content", "B") == 5
        assert tr.doc_frequency("content", "E") == 2
        assert tr.frequency("content", "E") == 2
        assert tr.doc_frequency("content", "A") == 1
        assert tr.frequency("content", "A") == 1
        assert tr.doc_frequency("content", "D") == 3
        assert tr.frequency("content", "D") == 4
        assert tr.doc_frequency("content", "F") == 1
        assert tr.frequency("content", "F") == 1
        assert tr.doc_frequency("content", "Z") == 0
        assert tr.frequency("content", "Z") == 0

        stats = [
            (fname, text, ti.doc_frequency(), ti.weight()) for (fname, text), ti in tr
        ]

        assert stats == [
            ("content", b"A", 1, 1),
            ("content", b"B", 2, 5),
            ("content", b"C", 2, 2),
            ("content", b"D", 3, 4),
            ("content", b"E", 2, 2),
            ("content", b"F", 1, 1),
        ]


def test_frequency_text():
    s = fields.Schema(content=fields.KEYWORD)
    st = RamStorage()
    ix = st.create_index(s)

    w = ix.writer()
    w.add_document(content="alfa bravo charlie delta echo")
    w.add_document(content="bravo bravo bravo bravo charlie delta delta")
    w.add_document(content="delta echo foxtrot")
    w.commit()

    with ix.reader() as tr:
        assert tr.doc_frequency("content", "bravo") == 2
        assert tr.frequency("content", "bravo") == 5
        assert tr.doc_frequency("content", "echo") == 2
        assert tr.frequency("content", "echo") == 2
        assert tr.doc_frequency("content", "alfa") == 1
        assert tr.frequency("content", "alfa") == 1
        assert tr.doc_frequency("content", "delta") == 3
        assert tr.frequency("content", "delta") == 4
        assert tr.doc_frequency("content", "foxtrot") == 1
        assert tr.frequency("content", "foxtrot") == 1
        assert tr.doc_frequency("content", "zulu") == 0
        assert tr.frequency("content", "zulu") == 0

        stats = [
            (fname, text, ti.doc_frequency(), ti.weight()) for (fname, text), ti in tr
        ]

        assert stats == [
            ("content", b"alfa", 1, 1),
            ("content", b"bravo", 2, 5),
            ("content", b"charlie", 2, 2),
            ("content", b"delta", 3, 4),
            ("content", b"echo", 2, 2),
            ("content", b"foxtrot", 1, 1),
        ]


def test_deletion():
    s = fields.Schema(key=fields.ID, name=fields.TEXT, value=fields.TEXT)
    with TempIndex(s, "deletion") as ix:
        w = ix.writer()
        w.add_document(key="A", name="Yellow brown", value="Blue red green purple?")
        w.add_document(key="B", name="Alpha beta", value="Gamma delta epsilon omega.")
        w.add_document(key="C", name="One two", value="Three four five.")
        w.commit()

        w = ix.writer()
        assert w.delete_by_term("key", "B") == 1
        w.commit(merge=False)

        assert ix.doc_count_all() == 3
        assert ix.doc_count() == 2

        w = ix.writer()
        w.add_document(key="A", name="Yellow brown", value="Blue red green purple?")
        w.add_document(key="B", name="Alpha beta", value="Gamma delta epsilon omega.")
        w.add_document(key="C", name="One two", value="Three four five.")
        w.commit()

        # This will match both documents with key == B, one of which is already
        # deleted. This should not raise an error.
        w = ix.writer()
        assert w.delete_by_term("key", "B") == 1
        w.commit()

        ix.optimize()
        assert ix.doc_count_all() == 4
        assert ix.doc_count() == 4

        with ix.reader() as tr:
            assert " ".join(tr.field_terms("name")) == "brown one two yellow"


def test_writer_reuse():
    s = fields.Schema(key=fields.ID)
    ix = RamStorage().create_index(s)

    w = ix.writer()
    w.add_document(key="A")
    w.add_document(key="B")
    w.add_document(key="C")
    w.commit()

    # You can't re-use a commited/canceled writer
    pytest.raises(IndexingError, w.add_document, key="D")
    pytest.raises(IndexingError, w.update_document, key="B")
    pytest.raises(IndexingError, w.delete_document, 0)
    pytest.raises(IndexingError, w.add_reader, None)
    pytest.raises(IndexingError, w.add_field, "name", fields.ID)
    pytest.raises(IndexingError, w.remove_field, "key")
    pytest.raises(IndexingError, w.searcher)


def test_update():
    # Test update with multiple unique keys
    SAMPLE_DOCS = [
        {"id": "test1", "path": "/test/1", "text": "Hello"},
        {"id": "test2", "path": "/test/2", "text": "There"},
        {"id": "test3", "path": "/test/3", "text": "Reader"},
    ]

    schema = fields.Schema(
        id=fields.ID(unique=True, stored=True),
        path=fields.ID(unique=True, stored=True),
        text=fields.TEXT,
    )

    with TempIndex(schema, "update") as ix:
        with ix.writer() as w:
            for doc in SAMPLE_DOCS:
                w.add_document(**doc)

        with ix.writer() as w:
            w.update_document(id="test2", path="test/1", text="Replacement")


def test_update2():
    schema = fields.Schema(
        key=fields.ID(unique=True, stored=True), p=fields.ID(stored=True)
    )
    with TempIndex(schema, "update2") as ix:
        nums = list(range(21))
        random.shuffle(nums)
        for i, n in enumerate(nums):
            w = ix.writer()
            w.update_document(key=str(n % 10), p=str(i))
            w.commit()

        with ix.searcher() as s:
            results = [d["key"] for _, d in s.iter_docs()]
            results = " ".join(sorted(results))
            assert results == "0 1 2 3 4 5 6 7 8 9"


def test_update_numeric():
    schema = fields.Schema(
        num=fields.NUMERIC(unique=True, stored=True), text=fields.ID(stored=True)
    )
    with TempIndex(schema, "updatenum") as ix:
        nums = list(range(5)) * 3
        random.shuffle(nums)
        for num in nums:
            with ix.writer() as w:
                w.update_document(num=num, text=str(num))

        with ix.searcher() as s:
            results = [d["text"] for _, d in s.iter_docs()]
            results = " ".join(sorted(results))
            assert results == "0 1 2 3 4"


def test_reindex():
    sample_docs = [
        {"id": "test1", "text": "This is a document. Awesome, is it not?"},
        {"id": "test2", "text": "Another document. Astounding!"},
        {
            "id": "test3",
            "text": ("A fascinating article on the behavior of domestic steak knives."),
        },
    ]

    schema = fields.Schema(
        text=fields.TEXT(stored=True), id=fields.ID(unique=True, stored=True)
    )
    with TempIndex(schema, "reindex") as ix:

        def reindex():
            writer = ix.writer()
            for doc in sample_docs:
                writer.update_document(**doc)
            writer.commit()

        reindex()
        assert ix.doc_count() == 3
        reindex()
        assert ix.doc_count() == 3


def test_noscorables1():
    values = [
        "alfa",
        "bravo",
        "charlie",
        "delta",
        "echo",
        "foxtrot",
        "golf",
        "hotel",
        "india",
        "juliet",
        "kilo",
        "lima",
    ]
    from random import choice, randint, sample

    times = 1000

    schema = fields.Schema(id=fields.ID, tags=fields.KEYWORD)
    with TempIndex(schema, "noscorables1") as ix:
        w = ix.writer()
        for _ in range(times):
            w.add_document(
                id=choice(values), tags=" ".join(sample(values, randint(2, 7)))
            )
        w.commit()

        with ix.searcher() as s:
            s.search(query.Term("id", "bravo"))


def test_noscorables2():
    schema = fields.Schema(field=fields.ID)
    with TempIndex(schema, "noscorables2") as ix:
        writer = ix.writer()
        writer.add_document(field="foo")
        writer.commit()


def test_multi():
    schema = fields.Schema(
        id=fields.ID(stored=True), content=fields.KEYWORD(stored=True)
    )
    with TempIndex(schema, "multi") as ix:
        writer = ix.writer()
        # Deleted 1
        writer.add_document(id="1", content="alfa bravo charlie")
        # Deleted 1
        writer.add_document(id="2", content="bravo charlie delta echo")
        # Deleted 2
        writer.add_document(id="3", content="charlie delta echo foxtrot")
        writer.commit()

        writer = ix.writer()
        writer.delete_by_term("id", "1")
        writer.delete_by_term("id", "2")
        writer.add_document(id="4", content="apple bear cherry donut")
        writer.add_document(id="5", content="bear cherry donut eggs")
        # Deleted 2
        writer.add_document(id="6", content="delta echo foxtrot golf")
        # no d
        writer.add_document(id="7", content="echo foxtrot golf hotel")
        writer.commit(merge=False)

        writer = ix.writer()
        writer.delete_by_term("id", "3")
        writer.delete_by_term("id", "6")
        writer.add_document(id="8", content="cherry donut eggs falafel")
        writer.add_document(id="9", content="donut eggs falafel grape")
        writer.add_document(id="A", content=" foxtrot golf hotel india")
        writer.commit(merge=False)

        assert ix.doc_count() == 6

        with ix.searcher() as s:
            r = s.search(query.Prefix("content", "d"), optimize=False)
            assert sorted([d["id"] for d in r]) == ["4", "5", "8", "9"]

            r = s.search(query.Prefix("content", "d"))
            assert sorted([d["id"] for d in r]) == ["4", "5", "8", "9"]

            r = s.search(query.Prefix("content", "d"), limit=None)
            assert sorted([d["id"] for d in r]) == ["4", "5", "8", "9"]


def test_deleteall():
    schema = fields.Schema(text=fields.TEXT)
    with TempIndex(schema, "deleteall") as ix:
        w = ix.writer()
        domain = "alfa bravo charlie delta echo".split()
        for i, ls in enumerate(permutations(domain)):
            w.add_document(text=" ".join(ls))
            if not i % 10:
                w.commit()
                w = ix.writer()
        w.commit()

        # This is just a test, don't use this method to delete all docs IRL!
        doccount = ix.doc_count_all()
        w = ix.writer()
        for docnum in range(doccount):
            w.delete_document(docnum)
        w.commit()

        with ix.searcher() as s:
            r = s.search(
                query.Or([query.Term("text", "alfa"), query.Term("text", "bravo")])
            )
            assert len(r) == 0

        ix.optimize()
        assert ix.doc_count_all() == 0

        with ix.reader() as r:
            assert list(r) == []


def test_simple_stored():
    schema = fields.Schema(a=fields.ID(stored=True), b=fields.ID(stored=False))
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(a="alfa", b="bravo")
    with ix.searcher() as s:
        sf = s.stored_fields(0)
        assert sf == {"a": "alfa"}


def test_single():
    schema = fields.Schema(id=fields.ID(stored=True), text=fields.TEXT)
    with TempIndex(schema, "single") as ix:
        w = ix.writer()
        w.add_document(id="1", text="alfa")
        w.commit()

        with ix.searcher() as s:
            assert ("text", "alfa") in s.reader()
            assert list(s.documents(id="1")) == [{"id": "1"}]
            assert list(s.documents(text="alfa")) == [{"id": "1"}]
            assert list(s.all_stored_fields()) == [{"id": "1"}]


def test_indentical_fields():
    schema = fields.Schema(
        id=fields.STORED, f1=fields.TEXT, f2=fields.TEXT, f3=fields.TEXT
    )
    with TempIndex(schema, "identifields") as ix:
        w = ix.writer()
        w.add_document(id=1, f1="alfa", f2="alfa", f3="alfa")
        w.commit()

        with ix.searcher() as s:
            assert list(s.lexicon("f1")) == [b"alfa"]
            assert list(s.lexicon("f2")) == [b"alfa"]
            assert list(s.lexicon("f3")) == [b"alfa"]
            assert list(s.documents(f1="alfa")) == [{"id": 1}]
            assert list(s.documents(f2="alfa")) == [{"id": 1}]
            assert list(s.documents(f3="alfa")) == [{"id": 1}]


def test_multivalue():
    ana = analysis.StemmingAnalyzer()
    schema = fields.Schema(
        id=fields.STORED,
        date=fields.DATETIME,
        num=fields.NUMERIC,
        txt=fields.TEXT(analyzer=ana),
    )
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(id=1, date=datetime(2001, 1, 1, tzinfo=timezone.utc), num=5)
        w.add_document(
            id=2,
            date=[
                datetime(2002, 2, 2, tzinfo=timezone.utc),
                datetime(2003, 3, 3, tzinfo=timezone.utc),
            ],
            num=[1, 2, 3, 12],
        )
        w.add_document(txt="a b c".split())

    with ix.reader() as r:
        assert ("num", 3) in r
        assert ("date", datetime(2003, 3, 3, tzinfo=timezone.utc)) in r
        assert " ".join(r.field_terms("txt")) == "a b c"


def test_multi_language():
    # Analyzer for English
    ana_eng = analysis.StemmingAnalyzer()

    # analyzer for Pig Latin
    def stem_piglatin(w):
        if w.endswith("ay"):
            w = w[:-2]
        return w

    ana_pig = analysis.StemmingAnalyzer(stoplist=["nday", "roay"], stemfn=stem_piglatin)

    # Dictionary mapping languages to analyzers
    analyzers = {"eng": ana_eng, "pig": ana_pig}

    # Fake documents
    corpus = [
        ("eng", "Such stuff as dreams are made on"),
        ("pig", "Otay ebay, roay otnay otay ebay"),
    ]

    schema = fields.Schema(
        content=fields.TEXT(stored=True), lang=fields.ID(stored=True)
    )
    ix = RamStorage().create_index(schema)

    with ix.writer() as w:
        for doclang, content in corpus:
            ana = analyzers[doclang]
            # "Pre-analyze" the field into token strings
            words = [token.text for token in ana(content)]
            # Note we store the original value but index the pre-analyzed words
            w.add_document(lang=doclang, content=words, _stored_content=content)

    with ix.searcher() as s:
        schema = s.schema

        # Modify the schema to fake the correct analyzer for the language
        # we're searching in
        schema["content"].analyzer = analyzers["eng"]

        qp = qparser.QueryParser("content", schema)
        q = qp.parse("dreaming")
        r = s.search(q)
        assert len(r) == 1
        assert r[0]["content"] == "Such stuff as dreams are made on"

        schema["content"].analyzer = analyzers["pig"]
        qp = qparser.QueryParser("content", schema)
        q = qp.parse("otnay")
        r = s.search(q)
        assert len(r) == 1
        assert r[0]["content"] == "Otay ebay, roay otnay otay ebay"


def test_doc_boost():
    schema = fields.Schema(id=fields.STORED, a=fields.TEXT, b=fields.TEXT)
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(id=0, a="alfa alfa alfa", b="bravo")
    w.add_document(id=1, a="alfa", b="bear", _a_boost=5.0)
    w.add_document(id=2, a="alfa alfa alfa alfa", _boost=0.5)
    w.commit()

    with ix.searcher() as s:
        r = s.search(query.Term("a", "alfa"))
        assert [hit["id"] for hit in r] == [1, 0, 2]

    w = ix.writer()
    w.add_document(id=3, a="alfa", b="bottle")
    w.add_document(id=4, b="bravo", _b_boost=2.0)
    w.commit(merge=False)

    with ix.searcher() as s:
        r = s.search(query.Term("a", "alfa"))
        assert [hit["id"] for hit in r] == [1, 0, 3, 2]


def test_globfield_length_merge():
    # Issue 343

    schema = fields.Schema(title=fields.TEXT(stored=True), path=fields.ID(stored=True))
    schema.add("*_text", fields.TEXT, glob=True)

    with TempIndex(schema, "globlenmerge") as ix:
        with ix.writer() as w:
            w.add_document(
                title="First document",
                path="/a",
                content_text="This is the first document we've added!",
            )

        with ix.writer() as w:
            w.add_document(
                title="Second document",
                path="/b",
                content_text="The second document is even more interesting!",
            )

        with ix.searcher() as s:
            docnum = s.document_number(path="/a")
            assert s.doc_field_length(docnum, "content_text") is not None

            qp = qparser.QueryParser("content", schema)
            q = qp.parse("content_text:document")
            r = s.search(q)
            paths = sorted(hit["path"] for hit in r)
            assert paths == ["/a", "/b"]


def test_glob_optimize():
    # Issue 472: Stored dynamic field deleted after commit with optimize

    schema = fields.Schema()
    schema.add("f*", fields.STORED, glob=True)

    with TempIndex(schema, "globoptimize") as ix:
        writer = ix.writer()

        # Create document with dynamic fields
        writer.add_document(f1=1, f2=2)
        writer.commit()

        # Read back fields
        assert list(ix.reader().all_stored_fields()) == [{"f1": 1, "f2": 2}]

        # Optimize
        writer = ix.writer()
        writer.commit(optimize=True)

        # Read fields again
        assert list(ix.reader().all_stored_fields()) == [{"f1": 1, "f2": 2}]


def test_index_decimals():
    from decimal import Decimal

    schema = fields.Schema(name=fields.KEYWORD(stored=True), num=fields.NUMERIC(int))
    ix = RamStorage().create_index(schema)

    with ix.writer() as w:
        with pytest.raises(TypeError):
            w.add_document(name="hello", num=Decimal("3.2"))

    schema = fields.Schema(
        name=fields.KEYWORD(stored=True), num=fields.NUMERIC(Decimal, decimal_places=5)
    )
    ix = RamStorage().create_index(schema)
    with ix.writer() as w:
        w.add_document(name="hello", num=Decimal("3.2"))


def test_stored_tuple():
    schema = fields.Schema(a=fields.STORED, b=fields.ID)

    with TempIndex(schema) as ix:
        with ix.writer() as w:
            w.add_document(a=("foo", 20))

        with ix.searcher() as s:
            assert s.stored_fields(0) == {"a": ("foo", 20)}

    with TempIndex(schema) as ix:
        with ix.writer() as w:
            w.add_document(a=("alfa", 1), b="a")
            w.add_document(a=("bravo", 2), b="b")
            w.add_document(a=("charlie", 3), b="c")
            w.add_document(a=("delta", 4), b="d")

        with ix.writer() as w:
            w.add_document(a=("echo", 5), b="e")
            w.add_document(a=("foxtrot", 6), b="f")
            w.add_document(a=("golf", 7), b="g")
            w.add_document(a=("hotel", 8), b="h")
            w.merge = False

        with ix.searcher() as s:
            doc = s.document(b="f")
            assert doc["a"] == ("foxtrot", 6)
