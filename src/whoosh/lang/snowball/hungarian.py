class HungarianStemmer:
    """
    The Hungarian Snowball stemmer.

    :cvar __vowels: The Hungarian vowels.
    :type __vowels: unicode
    :cvar __digraphs: The Hungarian digraphs.
    :type __digraphs: tuple
    :cvar __double_consonants: The Hungarian double consonants.
    :type __double_consonants: tuple
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :cvar __step4_suffixes: Suffixes to be deleted in step 4 of the algorithm.
    :type __step4_suffixes: tuple
    :cvar __step5_suffixes: Suffixes to be deleted in step 5 of the algorithm.
    :type __step5_suffixes: tuple
    :cvar __step6_suffixes: Suffixes to be deleted in step 6 of the algorithm.
    :type __step6_suffixes: tuple
    :cvar __step7_suffixes: Suffixes to be deleted in step 7 of the algorithm.
    :type __step7_suffixes: tuple
    :cvar __step8_suffixes: Suffixes to be deleted in step 8 of the algorithm.
    :type __step8_suffixes: tuple
    :cvar __step9_suffixes: Suffixes to be deleted in step 9 of the algorithm.
    :type __step9_suffixes: tuple
    :note: A detailed description of the Hungarian
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/hungarian/stemmer.html

    """

    __vowels = "aeiou\xf6\xfc\xe1\xe9\xed\xf3\xf5\xfa\xfb"
    __digraphs = ("cs", "dz", "dzs", "gy", "ly", "ny", "ty", "zs")
    __double_consonants = (
        "bb",
        "cc",
        "ccs",
        "dd",
        "ff",
        "gg",
        "ggy",
        "jj",
        "kk",
        "ll",
        "lly",
        "mm",
        "nn",
        "nny",
        "pp",
        "rr",
        "ss",
        "ssz",
        "tt",
        "tty",
        "vv",
        "zz",
        "zzs",
    )

    __step1_suffixes = ("al", "el")
    __step2_suffixes = (
        "k\xe9ppen",
        "onk\xe9nt",
        "enk\xe9nt",
        "ank\xe9nt",
        "k\xe9pp",
        "k\xe9nt",
        "ban",
        "ben",
        "nak",
        "nek",
        "val",
        "vel",
        "t\xf3l",
        "t\xf5l",
        "r\xf3l",
        "r\xf5l",
        "b\xf3l",
        "b\xf5l",
        "hoz",
        "hez",
        "h\xf6z",
        "n\xe1l",
        "n\xe9l",
        "\xe9rt",
        "kor",
        "ba",
        "be",
        "ra",
        "re",
        "ig",
        "at",
        "et",
        "ot",
        "\xf6t",
        "ul",
        "\xfcl",
        "v\xe1",
        "v\xe9",
        "en",
        "on",
        "an",
        "\xf6n",
        "n",
        "t",
    )
    __step3_suffixes = ("\xe1nk\xe9nt", "\xe1n", "\xe9n")
    __step4_suffixes = (
        "astul",
        "est\xfcl",
        "\xe1stul",
        "\xe9st\xfcl",
        "stul",
        "st\xfcl",
    )
    __step5_suffixes = ("\xe1", "\xe9")
    __step6_suffixes = (
        "ok\xe9",
        "\xf6k\xe9",
        "ak\xe9",
        "ek\xe9",
        "\xe1k\xe9",
        "\xe1\xe9i",
        "\xe9k\xe9",
        "\xe9\xe9i",
        "k\xe9",
        "\xe9i",
        "\xe9\xe9",
        "\xe9",
    )
    __step7_suffixes = (
        "\xe1juk",
        "\xe9j\xfck",
        "\xfcnk",
        "unk",
        "juk",
        "j\xfck",
        "\xe1nk",
        "\xe9nk",
        "nk",
        "uk",
        "\xfck",
        "em",
        "om",
        "am",
        "od",
        "ed",
        "ad",
        "\xf6d",
        "ja",
        "je",
        "\xe1m",
        "\xe1d",
        "\xe9m",
        "\xe9d",
        "m",
        "d",
        "a",
        "e",
        "o",
        "\xe1",
        "\xe9",
    )
    __step8_suffixes = (
        "jaitok",
        "jeitek",
        "jaink",
        "jeink",
        "aitok",
        "eitek",
        "\xe1itok",
        "\xe9itek",
        "jaim",
        "jeim",
        "jaid",
        "jeid",
        "eink",
        "aink",
        "itek",
        "jeik",
        "jaik",
        "\xe1ink",
        "\xe9ink",
        "aim",
        "eim",
        "aid",
        "eid",
        "jai",
        "jei",
        "ink",
        "aik",
        "eik",
        "\xe1im",
        "\xe1id",
        "\xe1ik",
        "\xe9im",
        "\xe9id",
        "\xe9ik",
        "im",
        "id",
        "ai",
        "ei",
        "ik",
        "\xe1i",
        "\xe9i",
        "i",
    )
    __step9_suffixes = ("\xe1k", "\xe9k", "\xf6k", "ok", "ek", "ak", "k")

    def stem(self, word):
        """
        Stem an Hungarian word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        r1 = self.__r1_hungarian(word, self.__vowels, self.__digraphs)

        # STEP 1: Remove instrumental case
        if r1.endswith(self.__step1_suffixes):
            for double_cons in self.__double_consonants:
                if word[-2 - len(double_cons) : -2] == double_cons:
                    word = "".join((word[:-4], word[-3]))

                    if r1[-2 - len(double_cons) : -2] == double_cons:
                        r1 = "".join((r1[:-4], r1[-3]))
                    break

        # STEP 2: Remove frequent cases
        for suffix in self.__step2_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    word = word[: -len(suffix)]
                    r1 = r1[: -len(suffix)]

                    if r1.endswith("\xe1"):
                        word = "".join((word[:-1], "a"))
                        r1 = "".join((r1[:-1], "a"))

                    elif r1.endswith("\xe9"):
                        word = "".join((word[:-1], "e"))
                        r1 = "".join((r1[:-1], "e"))
                break

        # STEP 3: Remove special cases
        for suffix in self.__step3_suffixes:
            if r1.endswith(suffix):
                if suffix == "\xe9n":
                    word = "".join((word[:-2], "e"))
                    r1 = "".join((r1[:-2], "e"))
                else:
                    word = "".join((word[: -len(suffix)], "a"))
                    r1 = "".join((r1[: -len(suffix)], "a"))
                break

        # STEP 4: Remove other cases
        for suffix in self.__step4_suffixes:
            if r1.endswith(suffix):
                if suffix == "\xe1stul":
                    word = "".join((word[:-5], "a"))
                    r1 = "".join((r1[:-5], "a"))

                elif suffix == "\xe9st\xfcl":
                    word = "".join((word[:-5], "e"))
                    r1 = "".join((r1[:-5], "e"))
                else:
                    word = word[: -len(suffix)]
                    r1 = r1[: -len(suffix)]
                break

        # STEP 5: Remove factive case
        for suffix in self.__step5_suffixes:
            if r1.endswith(suffix):
                for double_cons in self.__double_consonants:
                    if word[-1 - len(double_cons) : -1] == double_cons:
                        word = "".join((word[:-3], word[-2]))

                        if r1[-1 - len(double_cons) : -1] == double_cons:
                            r1 = "".join((r1[:-3], r1[-2]))
                        break

        # STEP 6: Remove owned
        for suffix in self.__step6_suffixes:
            if r1.endswith(suffix):
                if suffix in ("\xe1k\xe9", "\xe1\xe9i"):
                    word = "".join((word[:-3], "a"))
                    r1 = "".join((r1[:-3], "a"))

                elif suffix in ("\xe9k\xe9", "\xe9\xe9i", "\xe9\xe9"):
                    word = "".join((word[: -len(suffix)], "e"))
                    r1 = "".join((r1[: -len(suffix)], "e"))
                else:
                    word = word[: -len(suffix)]
                    r1 = r1[: -len(suffix)]
                break

        # STEP 7: Remove singular owner suffixes
        for suffix in self.__step7_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    if suffix in (
                        "\xe1nk",
                        "\xe1juk",
                        "\xe1m",
                        "\xe1d",
                        "\xe1",
                    ):
                        word = "".join((word[: -len(suffix)], "a"))
                        r1 = "".join((r1[: -len(suffix)], "a"))

                    elif suffix in (
                        "\xe9nk",
                        "\xe9j\xfck",
                        "\xe9m",
                        "\xe9d",
                        "\xe9",
                    ):
                        word = "".join((word[: -len(suffix)], "e"))
                        r1 = "".join((r1[: -len(suffix)], "e"))
                    else:
                        word = word[: -len(suffix)]
                        r1 = r1[: -len(suffix)]
                break

        # STEP 8: Remove plural owner suffixes
        for suffix in self.__step8_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    if suffix in (
                        "\xe1im",
                        "\xe1id",
                        "\xe1i",
                        "\xe1ink",
                        "\xe1itok",
                        "\xe1ik",
                    ):
                        word = "".join((word[: -len(suffix)], "a"))
                        r1 = "".join((r1[: -len(suffix)], "a"))

                    elif suffix in (
                        "\xe9im",
                        "\xe9id",
                        "\xe9i",
                        "\xe9ink",
                        "\xe9itek",
                        "\xe9ik",
                    ):
                        word = "".join((word[: -len(suffix)], "e"))
                        r1 = "".join((r1[: -len(suffix)], "e"))
                    else:
                        word = word[: -len(suffix)]
                        r1 = r1[: -len(suffix)]
                break

        # STEP 9: Remove plural suffixes
        for suffix in self.__step9_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    if suffix == "\xe1k":
                        word = "".join((word[:-2], "a"))
                    elif suffix == "\xe9k":
                        word = "".join((word[:-2], "e"))
                    else:
                        word = word[: -len(suffix)]
                break

        return word

    def __r1_hungarian(self, word, vowels, digraphs):
        """
        Return the region R1 that is used by the Hungarian stemmer.

        If the word begins with a vowel, R1 is defined as the region
        after the first consonant or digraph (= two letters stand for
        one phoneme) in the word. If the word begins with a consonant,
        it is defined as the region after the first vowel in the word.
        If the word does not contain both a vowel and consonant, R1
        is the null region at the end of the word.

        :param word: The Hungarian word whose region R1 is determined.
        :type word: str or unicode
        :param vowels: The Hungarian vowels that are used to determine
                       the region R1.
        :type vowels: unicode
        :param digraphs: The digraphs that are used to determine the
                         region R1.
        :type digraphs: tuple
        :return: the region R1 for the respective word.
        :rtype: unicode
        :note: This helper method is invoked by the stem method of the subclass
               HungarianStemmer. It is not to be invoked directly!

        """
        r1 = ""
        if word[0] in vowels:
            for digraph in digraphs:
                if digraph in word[1:]:
                    r1 = word[word.index(digraph[-1]) + 1 :]
                    return r1

            for i in range(1, len(word)):
                if word[i] not in vowels:
                    r1 = word[i + 1 :]
                    break
        else:
            for i in range(1, len(word)):
                if word[i] in vowels:
                    r1 = word[i + 1 :]
                    break

        return r1
