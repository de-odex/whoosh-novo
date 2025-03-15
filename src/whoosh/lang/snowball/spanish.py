from .bases import _StandardStemmer


class SpanishStemmer(_StandardStemmer):
    """
    The Spanish Snowball stemmer.

    :cvar __vowels: The Spanish vowels.
    :type __vowels: unicode
    :cvar __step0_suffixes: Suffixes to be deleted in step 0 of the algorithm.
    :type __step0_suffixes: tuple
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2a_suffixes: Suffixes to be deleted in step 2a of the algorithm.
    :type __step2a_suffixes: tuple
    :cvar __step2b_suffixes: Suffixes to be deleted in step 2b of the algorithm.
    :type __step2b_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :note: A detailed description of the Spanish
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/spanish/stemmer.html

    """

    __vowels = "aeiou\xe1\xe9\xed\xf3\xfa\xfc"
    __step0_suffixes = (
        "selas",
        "selos",
        "sela",
        "selo",
        "las",
        "les",
        "los",
        "nos",
        "me",
        "se",
        "la",
        "le",
        "lo",
    )
    __step1_suffixes = (
        "amientos",
        "imientos",
        "amiento",
        "imiento",
        "aciones",
        "uciones",
        "adoras",
        "adores",
        "ancias",
        "log\xedas",
        "encias",
        "amente",
        "idades",
        "anzas",
        "ismos",
        "ables",
        "ibles",
        "istas",
        "adora",
        "aci\xf3n",
        "antes",
        "ancia",
        "log\xeda",
        "uci\xf3n",
        "encia",
        "mente",
        "anza",
        "icos",
        "icas",
        "ismo",
        "able",
        "ible",
        "ista",
        "osos",
        "osas",
        "ador",
        "ante",
        "idad",
        "ivas",
        "ivos",
        "ico",
        "ica",
        "oso",
        "osa",
        "iva",
        "ivo",
    )
    __step2a_suffixes = (
        "yeron",
        "yendo",
        "yamos",
        "yais",
        "yan",
        "yen",
        "yas",
        "yes",
        "ya",
        "ye",
        "yo",
        "y\xf3",
    )
    __step2b_suffixes = (
        "ar\xedamos",
        "er\xedamos",
        "ir\xedamos",
        "i\xe9ramos",
        "i\xe9semos",
        "ar\xedais",
        "aremos",
        "er\xedais",
        "eremos",
        "ir\xedais",
        "iremos",
        "ierais",
        "ieseis",
        "asteis",
        "isteis",
        "\xe1bamos",
        "\xe1ramos",
        "\xe1semos",
        "ar\xedan",
        "ar\xedas",
        "ar\xe9is",
        "er\xedan",
        "er\xedas",
        "er\xe9is",
        "ir\xedan",
        "ir\xedas",
        "ir\xe9is",
        "ieran",
        "iesen",
        "ieron",
        "iendo",
        "ieras",
        "ieses",
        "abais",
        "arais",
        "aseis",
        "\xe9amos",
        "ar\xe1n",
        "ar\xe1s",
        "ar\xeda",
        "er\xe1n",
        "er\xe1s",
        "er\xeda",
        "ir\xe1n",
        "ir\xe1s",
        "ir\xeda",
        "iera",
        "iese",
        "aste",
        "iste",
        "aban",
        "aran",
        "asen",
        "aron",
        "ando",
        "abas",
        "adas",
        "idas",
        "aras",
        "ases",
        "\xedais",
        "ados",
        "idos",
        "amos",
        "imos",
        "emos",
        "ar\xe1",
        "ar\xe9",
        "er\xe1",
        "er\xe9",
        "ir\xe1",
        "ir\xe9",
        "aba",
        "ada",
        "ida",
        "ara",
        "ase",
        "\xedan",
        "ado",
        "ido",
        "\xedas",
        "\xe1is",
        "\xe9is",
        "\xeda",
        "ad",
        "ed",
        "id",
        "an",
        "i\xf3",
        "ar",
        "er",
        "ir",
        "as",
        "\xeds",
        "en",
        "es",
    )
    __step3_suffixes = ("os", "a", "e", "o", "\xe1", "\xe9", "\xed", "\xf3")

    def stem(self, word):
        """
        Stem a Spanish word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        step1_success = False

        r1, r2 = self._r1r2_standard(word, self.__vowels)
        rv = self._rv_standard(word, self.__vowels)

        # STEP 0: Attached pronoun
        for suffix in self.__step0_suffixes:
            if word.endswith(suffix):
                if rv.endswith(suffix):
                    if rv[: -len(suffix)].endswith(
                        (
                            "i\xe9ndo",
                            "\xe1ndo",
                            "\xe1r",
                            "\xe9r",
                            "\xedr",
                        )
                    ):
                        word = (
                            word[: -len(suffix)]
                            .replace("\xe1", "a")
                            .replace("\xe9", "e")
                            .replace("\xed", "i")
                        )
                        r1 = (
                            r1[: -len(suffix)]
                            .replace("\xe1", "a")
                            .replace("\xe9", "e")
                            .replace("\xed", "i")
                        )
                        r2 = (
                            r2[: -len(suffix)]
                            .replace("\xe1", "a")
                            .replace("\xe9", "e")
                            .replace("\xed", "i")
                        )
                        rv = (
                            rv[: -len(suffix)]
                            .replace("\xe1", "a")
                            .replace("\xe9", "e")
                            .replace("\xed", "i")
                        )

                    elif rv[: -len(suffix)].endswith(
                        ("ando", "iendo", "ar", "er", "ir")
                    ):
                        word = word[: -len(suffix)]
                        r1 = r1[: -len(suffix)]
                        r2 = r2[: -len(suffix)]
                        rv = rv[: -len(suffix)]

                    elif rv[: -len(suffix)].endswith("yendo") and word[
                        : -len(suffix)
                    ].endswith("uyendo"):
                        word = word[: -len(suffix)]
                        r1 = r1[: -len(suffix)]
                        r2 = r2[: -len(suffix)]
                        rv = rv[: -len(suffix)]
                break

        # STEP 1: Standard suffix removal
        for suffix in self.__step1_suffixes:
            if word.endswith(suffix):
                if suffix == "amente" and r1.endswith(suffix):
                    step1_success = True
                    word = word[:-6]
                    r2 = r2[:-6]
                    rv = rv[:-6]

                    if r2.endswith("iv"):
                        word = word[:-2]
                        r2 = r2[:-2]
                        rv = rv[:-2]

                        if r2.endswith("at"):
                            word = word[:-2]
                            rv = rv[:-2]

                    elif r2.endswith(("os", "ic", "ad")):
                        word = word[:-2]
                        rv = rv[:-2]

                elif r2.endswith(suffix):
                    step1_success = True
                    if suffix in (
                        "adora",
                        "ador",
                        "aci\xf3n",
                        "adoras",
                        "adores",
                        "aciones",
                        "ante",
                        "antes",
                        "ancia",
                        "ancias",
                    ):
                        word = word[: -len(suffix)]
                        r2 = r2[: -len(suffix)]
                        rv = rv[: -len(suffix)]

                        if r2.endswith("ic"):
                            word = word[:-2]
                            rv = rv[:-2]

                    elif suffix in ("log\xeda", "log\xedas"):
                        word = word.replace(suffix, "log")
                        rv = rv.replace(suffix, "log")

                    elif suffix in ("uci\xf3n", "uciones"):
                        word = word.replace(suffix, "u")
                        rv = rv.replace(suffix, "u")

                    elif suffix in ("encia", "encias"):
                        word = word.replace(suffix, "ente")
                        rv = rv.replace(suffix, "ente")

                    elif suffix == "mente":
                        word = word[:-5]
                        r2 = r2[:-5]
                        rv = rv[:-5]

                        if r2.endswith(("ante", "able", "ible")):
                            word = word[:-4]
                            rv = rv[:-4]

                    elif suffix in ("idad", "idades"):
                        word = word[: -len(suffix)]
                        r2 = r2[: -len(suffix)]
                        rv = rv[: -len(suffix)]

                        for pre_suff in ("abil", "ic", "iv"):
                            if r2.endswith(pre_suff):
                                word = word[: -len(pre_suff)]
                                rv = rv[: -len(pre_suff)]

                    elif suffix in ("ivo", "iva", "ivos", "ivas"):
                        word = word[: -len(suffix)]
                        r2 = r2[: -len(suffix)]
                        rv = rv[: -len(suffix)]
                        if r2.endswith("at"):
                            word = word[:-2]
                            rv = rv[:-2]
                    else:
                        word = word[: -len(suffix)]
                        rv = rv[: -len(suffix)]
                break

        # STEP 2a: Verb suffixes beginning 'y'
        if not step1_success:
            for suffix in self.__step2a_suffixes:
                if rv.endswith(suffix) and word[-len(suffix) - 1 : -len(suffix)] == "u":
                    word = word[: -len(suffix)]
                    rv = rv[: -len(suffix)]
                    break

            # STEP 2b: Other verb suffixes
            for suffix in self.__step2b_suffixes:
                if rv.endswith(suffix):
                    if suffix in ("en", "es", "\xe9is", "emos"):
                        word = word[: -len(suffix)]
                        rv = rv[: -len(suffix)]

                        if word.endswith("gu"):
                            word = word[:-1]

                        if rv.endswith("gu"):
                            rv = rv[:-1]
                    else:
                        word = word[: -len(suffix)]
                        rv = rv[: -len(suffix)]
                    break

        # STEP 3: Residual suffix
        for suffix in self.__step3_suffixes:
            if rv.endswith(suffix):
                if suffix in ("e", "\xe9"):
                    word = word[: -len(suffix)]
                    rv = rv[: -len(suffix)]

                    if (
                        len(word) >= 2
                        and word[-2:] == "gu"
                        and len(rv) > 0
                        and rv[-1] == "u"
                    ):
                        word = word[:-1]
                else:
                    word = word[: -len(suffix)]
                break

        word = (
            word.replace("\xe1", "a")
            .replace("\xe9", "e")
            .replace("\xed", "i")
            .replace("\xf3", "o")
            .replace("\xfa", "u")
        )
        return word
