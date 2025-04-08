from random import randint, shuffle

from whoosh.filedb.filetables import HashReader, HashWriter
from whoosh.util.testing import TempStorage


def test_bigtable():
    with TempStorage("bigtable") as st:

        def randstring(min, max):
            return bytes(randint(1, 255) for _ in range(randint(min, max)))

        count = 100000
        samp = {randstring(1, 50): randstring(1, 50) for _ in range(count)}

        fhw = HashWriter(st.create_file("big.hsh"))
        fhw.add_all(samp.items())
        fhw.close()

        fhr = HashReader(st.open_file("big.hsh"))
        keys = list(samp.keys())
        shuffle(keys)
        for key in keys:
            assert samp[key] == fhr[key]

        set1 = set(samp.items())
        set2 = set(fhr.items())
        assert set1 == set2

        fhr.close()
