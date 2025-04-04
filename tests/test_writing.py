import random
import threading
import time

import pytest

from whoosh import analysis, fields, query, writing
from whoosh.filedb.filestore import RamStorage
from whoosh.util.testing import TempIndex


def u(s):
    return s.decode("ascii") if isinstance(s, bytes) else s


def test_no_stored():
    schema = fields.Schema(id=fields.ID, text=fields.TEXT)
    with TempIndex(schema, "nostored") as ix:
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
        )

        w = ix.writer()
        for i in range(20):
            w.add_document(id=str(i), text=" ".join(random.sample(domain, 5)))
        w.commit()

        with ix.reader() as r:
            assert sorted([int(id) for id in r.lexicon("id")]) == list(range(20))


def test_asyncwriter():
    schema = fields.Schema(id=fields.ID(stored=True), text=fields.TEXT)
    with TempIndex(schema, "asyncwriter") as ix:
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
        )

        writers = []
        # Simulate doing 20 (near-)simultaneous commits. If we weren't using
        # AsyncWriter, at least some of these would fail because the first
        # writer wouldn't be finished yet.
        for i in range(20):
            w = writing.AsyncWriter(ix)
            writers.append(w)
            w.add_document(id=str(i), text=" ".join(random.sample(domain, 5)))
            w.commit()

        # Wait for all writers to finish before checking the results
        for w in writers:
            if w.running:
                w.join()

        # Check whether all documents made it into the index.
        with ix.reader() as r:
            assert sorted([int(id) for id in r.lexicon("id")]) == list(range(20))


def test_asyncwriter_no_stored():
    schema = fields.Schema(id=fields.ID, text=fields.TEXT)
    with TempIndex(schema, "asyncnostored") as ix:
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
        )

        writers = []
        # Simulate doing 20 (near-)simultaneous commits. If we weren't using
        # AsyncWriter, at least some of these would fail because the first
        # writer wouldn't be finished yet.
        for i in range(20):
            w = writing.AsyncWriter(ix)
            writers.append(w)
            w.add_document(id=str(i), text=" ".join(random.sample(domain, 5)))
            w.commit()

        # Wait for all writers to finish before checking the results
        for w in writers:
            if w.running:
                w.join()

        # Check whether all documents made it into the index.
        with ix.reader() as r:
            assert sorted([int(id) for id in r.lexicon("id")]) == list(range(20))


def test_updates():
    schema = fields.Schema(id=fields.ID(unique=True, stored=True))
    ix = RamStorage().create_index(schema)
    for _ in range(10):
        with ix.writer() as w:
            w.update_document(id="a")
    assert ix.doc_count() == 1


def test_buffered():
    schema = fields.Schema(id=fields.ID, text=fields.TEXT)
    with TempIndex(schema, "buffered") as ix:
        domain = "alfa bravo charlie delta echo foxtrot golf hotel india"
        domain = domain.split()

        w = writing.BufferedWriter(
            ix, period=None, limit=10, commitargs={"merge": False}
        )
        for i in range(20):
            w.add_document(id=str(i), text=" ".join(random.sample(domain, 5)))
        time.sleep(0.1)
        w.close()

        assert len(ix._segments()) == 2


def test_buffered_search():
    schema = fields.Schema(id=fields.STORED, text=fields.TEXT)
    with TempIndex(schema, "bufferedsearch") as ix:
        w = writing.BufferedWriter(ix, period=None, limit=5)
        w.add_document(id=1, text="alfa bravo charlie")
        w.add_document(id=2, text="bravo tango delta")
        w.add_document(id=3, text="tango delta echo")
        w.add_document(id=4, text="charlie delta echo")

        with w.searcher() as s:
            r = s.search(query.Term("text", "tango"))
            assert sorted([d["id"] for d in r]) == [2, 3]

        w.add_document(id=5, text="foxtrot golf hotel")
        w.add_document(id=6, text="india tango juliet")
        w.add_document(id=7, text="tango kilo lima")
        w.add_document(id=8, text="mike november echo")

        with w.searcher() as s:
            r = s.search(query.Term("text", "tango"))
            assert sorted([d["id"] for d in r]) == [2, 3, 6, 7]

        w.close()


def test_buffered_update():
    schema = fields.Schema(
        id=fields.ID(stored=True, unique=True), payload=fields.STORED
    )
    with TempIndex(schema, "bufferedupdate") as ix:
        w = writing.BufferedWriter(ix, period=None, limit=5)
        for i in range(10):
            for char in "abc":
                fs = {"id": char, "payload": str(i) + char}
                w.update_document(**fs)

        with w.reader() as r:
            sfs = [sf for _, sf in r.iter_docs()]
            sfs = sorted(sfs, key=lambda x: x["id"])
            assert sfs == [
                {"id": u("a"), "payload": u("9a")},
                {"id": u("b"), "payload": u("9b")},
                {"id": u("c"), "payload": u("9c")},
            ]
            assert r.doc_count() == 3

        w.close()


def test_buffered_threads():
    domain = "alfa bravo charlie delta".split()
    schema = fields.Schema(name=fields.ID(unique=True, stored=True))
    with TempIndex(schema, "buffthreads") as ix:
        w = writing.BufferedWriter(ix, limit=10)

        class SimWriter(threading.Thread):
            def run(self):
                for _ in range(5):
                    w.update_document(name=random.choice(domain))
                    time.sleep(random.uniform(0.01, 0.1))

        threads = [SimWriter() for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        w.close()

        with ix.reader() as r:
            assert r.doc_count() == 4
            names = sorted([d["name"] for d in r.all_stored_fields()])
            assert names == domain


def test_fractional_weights():
    ana = analysis.RegexTokenizer(r"\S+") | analysis.DelimitedAttributeFilter()

    # With Positions format
    schema = fields.Schema(f=fields.TEXT(analyzer=ana))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(f="alfa^0.5 bravo^1.5 charlie^2.0 delta^1.5")
    w.commit()

    with ix.searcher() as s:
        wts = []
        for word in s.lexicon("f"):
            p = s.postings("f", word)
            wts.append(p.weight())
        assert wts == [0.5, 1.5, 2.0, 1.5]

    # Try again with Frequency format
    schema = fields.Schema(f=fields.TEXT(analyzer=ana, phrase=False))
    ix = RamStorage().create_index(schema)
    w = ix.writer()
    w.add_document(f="alfa^0.5 bravo^1.5 charlie^2.0 delta^1.5")
    w.commit()

    with ix.searcher() as s:
        wts = []
        for word in s.lexicon("f"):
            p = s.postings("f", word)
            wts.append(p.weight())
        assert wts == [0.5, 1.5, 2.0, 1.5]


def test_cancel_delete():
    schema = fields.Schema(id=fields.ID(stored=True))
    # Single segment
    with TempIndex(schema, "canceldelete1") as ix:
        w = ix.writer()
        for char in "ABCD":
            w.add_document(id=char)
        w.commit()

        with ix.reader() as r:
            assert not r.has_deletions()

        w = ix.writer()
        w.delete_document(2)
        w.delete_document(3)
        w.cancel()

        with ix.reader() as r:
            assert not r.has_deletions()
            assert not r.is_deleted(2)
            assert not r.is_deleted(3)

    # Multiple segments
    with TempIndex(schema, "canceldelete2") as ix:
        for char in "ABCD":
            w = ix.writer()
            w.add_document(id=char)
            w.commit(merge=False)

        with ix.reader() as r:
            assert not r.has_deletions()

        w = ix.writer()
        w.delete_document(2)
        w.delete_document(3)
        w.cancel()

        with ix.reader() as r:
            assert not r.has_deletions()
            assert not r.is_deleted(2)
            assert not r.is_deleted(3)


def test_delete_nonexistant():
    from whoosh.writing import IndexingError

    schema = fields.Schema(id=fields.ID(stored=True))
    # Single segment
    with TempIndex(schema, "deletenon1") as ix:
        w = ix.writer()
        for char in "ABC":
            w.add_document(id=char)
        w.commit()

        try:
            w = ix.writer()
            with pytest.raises(IndexingError):
                w.delete_document(5)
        finally:
            w.cancel()

    # Multiple segments
    with TempIndex(schema, "deletenon1") as ix:
        for char in "ABC":
            w = ix.writer()
            w.add_document(id=char)
            w.commit(merge=False)

        try:
            w = ix.writer()
            with pytest.raises(IndexingError):
                w.delete_document(5)
        finally:
            w.cancel()


def test_add_field():
    schema = fields.Schema(a=fields.TEXT)
    with TempIndex(schema, "addfield") as ix:
        with ix.writer() as w:
            w.add_document(a="alfa bravo charlie")
        with ix.writer() as w:
            w.add_field("b", fields.ID(stored=True))
            w.add_field("c*", fields.ID(stored=True), glob=True)
            w.add_document(a="delta echo foxtrot", b="india", cat="juliet")

        with ix.searcher() as s:
            fs = s.document(b="india")
            assert fs == {"b": "india", "cat": "juliet"}


def test_add_reader():
    schema = fields.Schema(
        i=fields.ID(stored=True, unique=True),
        a=fields.TEXT(stored=True, spelling=True),
        b=fields.TEXT(vector=True),
    )
    with TempIndex(schema, "addreader") as ix:
        with ix.writer() as w:
            w.add_document(
                i="0", a="alfa bravo charlie delta", b="able baker coxwell dog"
            )
            w.add_document(
                i="1", a="bravo charlie delta echo", b="elf fabio gong hiker"
            )
            w.add_document(
                i="2", a="charlie delta echo foxtrot", b="india joker king loopy"
            )
            w.add_document(
                i="3", a="delta echo foxtrot golf", b="mister noogie oompah pancake"
            )

        with ix.writer() as w:
            w.delete_by_term("i", "1")
            w.delete_by_term("i", "3")

        with ix.writer() as w:
            w.add_document(
                i="4", a="hotel india juliet kilo", b="quick rhubarb soggy trap"
            )
            w.add_document(
                i="5", a="india juliet kilo lima", b="umber violet weird xray"
            )
            w.optimize = True

        with ix.reader() as r:
            assert r.doc_count() == 4

            sfs = sorted(r.all_stored_fields(), key=lambda d: d["i"])
            assert sfs == [
                {"i": "0", "a": "alfa bravo charlie delta"},
                {"i": "2", "a": "charlie delta echo foxtrot"},
                {"i": "4", "a": "hotel india juliet kilo"},
                {"i": "5", "a": "india juliet kilo lima"},
            ]

            assert (
                " ".join(r.field_terms("a"))
                == "alfa bravo charlie delta echo foxtrot hotel india juliet kilo lima"
            )

            vs = []
            for docnum in r.all_doc_ids():
                v = r.vector(docnum, "b")
                vs.append(list(v.all_ids()))
            assert vs == [
                ["quick", "rhubarb", "soggy", "trap"],
                ["umber", "violet", "weird", "xray"],
                ["able", "baker", "coxwell", "dog"],
                ["india", "joker", "king", "loopy"],
            ]


def test_add_reader_spelling():
    # Test whether add_spell_word() items get copied over in a merge

    # Because b is stemming and spelled, it will use add_spell_word()
    ana = analysis.StemmingAnalyzer()
    schema = fields.Schema(
        a=fields.TEXT(analyzer=ana), b=fields.TEXT(analyzer=ana, spelling=True)
    )

    with TempIndex(schema, "addreadersp") as ix:
        with ix.writer() as w:
            w.add_document(a="rendering modeling", b="rendering modeling")
            w.add_document(a="flying rolling", b="flying rolling")

        with ix.writer() as w:
            w.add_document(a="writing eyeing", b="writing eyeing")
            w.add_document(a="undoing indicating", b="undoing indicating")
            w.optimize = True

        with ix.reader() as r:
            sws = list(r.lexicon("spell_b"))
            assert sws == [
                b"eyeing",
                b"flying",
                b"indicating",
                b"modeling",
                b"rendering",
                b"rolling",
                b"undoing",
                b"writing",
            ]

            assert list(r.terms_within("a", "undoink", 1)) == []
            assert list(r.terms_within("b", "undoink", 1)) == ["undoing"]


def test_clear():
    schema = fields.Schema(a=fields.KEYWORD)
    ix = RamStorage().create_index(schema)

    # Add some segments
    with ix.writer() as w:
        w.add_document(a="one two three")
        w.merge = False
    with ix.writer() as w:
        w.add_document(a="two three four")
        w.merge = False
    with ix.writer() as w:
        w.add_document(a="three four five")
        w.merge = False

    # Clear
    with ix.writer() as w:
        w.add_document(a="foo bar baz")
        w.mergetype = writing.CLEAR

    with ix.searcher() as s:
        assert s.doc_count_all() == 1
        assert list(s.reader().lexicon("a")) == [b"bar", b"baz", b"foo"]


def test_spellable_list():
    # Make sure a spellable field works with a list of pre-analyzed tokens

    ana = analysis.StemmingAnalyzer()
    schema = fields.Schema(
        Location=fields.STORED,
        Lang=fields.STORED,
        Title=fields.TEXT(spelling=True, analyzer=ana),
    )
    ix = RamStorage().create_index(schema)

    doc = {
        "Location": "1000/123",
        "Lang": "E",
        "Title": ["Introduction", "Numerical", "Analysis"],
    }

    with ix.writer() as w:
        w.add_document(**doc)


def test_zero_procs():
    schema = fields.Schema(text=fields.TEXT)
    ix = RamStorage().create_index(schema)
    with ix.writer(procs=0) as w:
        assert isinstance(w, writing.IndexWriter)

    with ix.writer(procs=1) as w:
        assert isinstance(w, writing.IndexWriter)


def test_delete_by_term_has_del():
    schema = fields.Schema(key=fields.KEYWORD)
    with TempIndex(schema) as ix:
        with ix.writer() as w:
            w.add_document(key="alfa")
            w.add_document(key="bravo")
            w.add_document(key="charlie")

        with ix.writer() as w:
            w.add_document(key="delta")
            w.add_document(key="echo")
            w.add_document(key="foxtrot")
            w.merge = False

        with ix.reader() as r:
            assert not r.has_deletions()

        with ix.writer() as w:
            w.delete_by_term("key", "bravo")
            w.optimize = True

        with ix.reader() as r:
            assert not r.has_deletions()


def test_add_fail_with_absorbed_exception():
    """
    Issue #375 https://github.com/whoosh-community/whoosh/issues/375
    Test that a failed document add with absorbed exceptions does not leave
    an unfinished document state for the next document to be added.

    Test Case:
    1. Add a bad document (in this case using integer ID)
    2. Absorb exceptions when doing so

    Client code is now unaware of previous error and OK with it

    3. Attempt to add a new document, also invalid but without absorbing exceptions

    Expected behavior: Appropriate exception for second document failure
    Behavior prior to fix: Cryptic "Called start_doc when already in a doc"

    This is because the first document had left the perDocWriter in an unfinished state.
    The fix cleaned up the writer when aborting from a bad addition, allowing the
    exception for the actual problem with the second document to bubble up.
    In this case: "2 is not unicode or sequence"
    """
    schema = fields.Schema(id=fields.ID())
    st = RamStorage()
    ix = st.create_index(schema)

    with ix.writer() as w:
        try:
            # Integer value is invalid, but absorbed exception causes silent failure
            w.add_document(id=1)
        except:
            pass
        with pytest.raises(Exception) as ex:
            w.add_document(id=2)

        # Assert that correct exception is raised, not the cryptic one
        assert "already" not in ex.value.args[0]
        assert "unicode" in ex.value.args[0]
