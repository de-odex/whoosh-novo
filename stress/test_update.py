import random

from whoosh import fields, query
from whoosh.util.testing import TempIndex


def test_many_updates():
    schema = fields.Schema(key=fields.ID(unique=True, stored=True))
    with TempIndex(schema, "manyupdates") as ix:
        for _ in range(10000):
            num = random.randint(0, 5000)
            w = ix.writer()
            w.update_document(key=str(num))
            w.commit()

        with ix.searcher() as s:
            result = [d["key"] for d in s.search(query.Every())]
            assert len(result) == len(set(result))
