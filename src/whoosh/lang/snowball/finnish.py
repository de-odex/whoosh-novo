from .bases import _StandardStemmer


class FinnishStemmer(_StandardStemmer):
    """
    The Finnish Snowball stemmer.

    :cvar __vowels: The Finnish vowels.
    :type __vowels: unicode
    :cvar __restricted_vowels: A subset of the Finnish vowels.
    :type __restricted_vowels: unicode
    :cvar __long_vowels: The Finnish vowels in their long forms.
    :type __long_vowels: tuple
    :cvar __consonants: The Finnish consonants.
    :type __consonants: unicode
    :cvar __double_consonants: The Finnish double consonants.
    :type __double_consonants: tuple
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :cvar __step4_suffixes: Suffixes to be deleted in step 4 of the algorithm.
    :type __step4_suffixes: tuple
    :note: A detailed description of the Finnish
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/finnish/stemmer.html
    """

    __vowels = "aeiouy\xe4\xf6"
    __restricted_vowels = "aeiou\xe4\xf6"
    __long_vowels = ("aa", "ee", "ii", "oo", "uu", "\xe4\xe4", "\xf6\xf6")
    __consonants = "bcdfghjklmnpqrstvwxz"
    __double_consonants = (
        "bb",
        "cc",
        "dd",
        "ff",
        "gg",
        "hh",
        "jj",
        "kk",
        "ll",
        "mm",
        "nn",
        "pp",
        "qq",
        "rr",
        "ss",
        "tt",
        "vv",
        "ww",
        "xx",
        "zz",
    )
    __step1_suffixes = (
        "kaan",
        "k\xe4\xe4n",
        "sti",
        "kin",
        "han",
        "h\xe4n",
        "ko",
        "k\xf6",
        "pa",
        "p\xe4",
    )
    __step2_suffixes = (
        "nsa",
        "ns\xe4",
        "mme",
        "nne",
        "si",
        "ni",
        "an",
        "\xe4n",
        "en",
    )
    __step3_suffixes = (
        "siin",
        "tten",
        "seen",
        "han",
        "hen",
        "hin",
        "hon",
        "h\xe4n",
        "h\xf6n",
        "den",
        "tta",
        "tt\xe4",
        "ssa",
        "ss\xe4",
        "sta",
        "st\xe4",
        "lla",
        "ll\xe4",
        "lta",
        "lt\xe4",
        "lle",
        "ksi",
        "ine",
        "ta",
        "t\xe4",
        "na",
        "n\xe4",
        "a",
        "\xe4",
        "n",
    )
    __step4_suffixes = (
        "impi",
        "impa",
        "imp\xe4",
        "immi",
        "imma",
        "imm\xe4",
        "mpi",
        "mpa",
        "mp\xe4",
        "mmi",
        "mma",
        "mm\xe4",
        "eja",
        "ej\xe4",
    )

    def stem(self, word):  # noqa: C901
        """
        Stem a Finnish word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        This method is too complex (51) -- ruff rule C901
        This method has too many branches (58) -- ruff rule PLR0912
        This method has too many statements (148) -- ruff rule PLR0915
        Future edits to this method should reduce, not increase its complexity.
        """
        word = word.lower()

        step3_success = False

        r1, r2 = self._r1r2_standard(word, self.__vowels)

        # STEP 1: Particles etc.
        for suffix in self.__step1_suffixes:
            if r1.endswith(suffix):
                if suffix == "sti":
                    if suffix in r2:
                        word = word[:-3]
                        r1 = r1[:-3]
                        r2 = r2[:-3]
                else:
                    if word[-len(suffix) - 1] in "ntaeiouy\xe4\xf6":
                        word = word[: -len(suffix)]
                        r1 = r1[: -len(suffix)]
                        r2 = r2[: -len(suffix)]
                break

        # STEP 2: Possessives
        for suffix in self.__step2_suffixes:
            if r1.endswith(suffix):
                if suffix == "si":
                    if word[-3] != "k":
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                elif suffix == "ni":
                    word = word[:-2]
                    r1 = r1[:-2]
                    r2 = r2[:-2]
                    if word.endswith("kse"):
                        word = "".join((word[:-3], "ksi"))

                    if r1.endswith("kse"):
                        r1 = "".join((r1[:-3], "ksi"))

                    if r2.endswith("kse"):
                        r2 = "".join((r2[:-3], "ksi"))

                elif suffix == "an":
                    if word[-4:-2] in ("ta", "na") or word[-5:-2] in (
                        "ssa",
                        "sta",
                        "lla",
                        "lta",
                    ):
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                elif suffix == "\xe4n":
                    if word[-4:-2] in ("t\xe4", "n\xe4") or word[-5:-2] in (
                        "ss\xe4",
                        "st\xe4",
                        "ll\xe4",
                        "lt\xe4",
                    ):
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                elif suffix == "en":
                    if word[-5:-2] in ("lle", "ine"):
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]
                else:
                    word = word[:-3]
                    r1 = r1[:-3]
                    r2 = r2[:-3]
                break

        # STEP 3: Cases
        for suffix in self.__step3_suffixes:
            if r1.endswith(suffix):
                if suffix in ("han", "hen", "hin", "hon", "h\xe4n", "h\xf6n"):
                    if (
                        (suffix == "han" and word[-4] == "a")
                        or (suffix == "hen" and word[-4] == "e")
                        or (suffix == "hin" and word[-4] == "i")
                        or (suffix == "hon" and word[-4] == "o")
                        or (suffix == "h\xe4n" and word[-4] == "\xe4")
                        or (suffix == "h\xf6n" and word[-4] == "\xf6")
                    ):
                        word = word[:-3]
                        r1 = r1[:-3]
                        r2 = r2[:-3]
                        step3_success = True

                elif suffix in ("siin", "den", "tten"):
                    if (
                        word[-len(suffix) - 1] == "i"
                        and word[-len(suffix) - 2] in self.__restricted_vowels
                    ):
                        word = word[: -len(suffix)]
                        r1 = r1[: -len(suffix)]
                        r2 = r2[: -len(suffix)]
                        step3_success = True
                    else:
                        continue

                elif suffix == "seen":
                    if word[-6:-4] in self.__long_vowels:
                        word = word[:-4]
                        r1 = r1[:-4]
                        r2 = r2[:-4]
                        step3_success = True
                    else:
                        continue

                elif suffix in ("a", "\xe4"):
                    if word[-2] in self.__vowels and word[-3] in self.__consonants:
                        word = word[:-1]
                        r1 = r1[:-1]
                        r2 = r2[:-1]
                        step3_success = True

                elif suffix in ("tta", "tt\xe4"):
                    if word[-4] == "e":
                        word = word[:-3]
                        r1 = r1[:-3]
                        r2 = r2[:-3]
                        step3_success = True

                elif suffix == "n":
                    word = word[:-1]
                    r1 = r1[:-1]
                    r2 = r2[:-1]
                    step3_success = True

                    if word[-2:] == "ie" or word[-2:] in self.__long_vowels:
                        word = word[:-1]
                        r1 = r1[:-1]
                        r2 = r2[:-1]
                else:
                    word = word[: -len(suffix)]
                    r1 = r1[: -len(suffix)]
                    r2 = r2[: -len(suffix)]
                    step3_success = True
                break

        # STEP 4: Other endings
        for suffix in self.__step4_suffixes:
            if r2.endswith(suffix):
                if suffix in ("mpi", "mpa", "mp\xe4", "mmi", "mma", "mm\xe4"):
                    if word[-5:-3] != "po":
                        word = word[:-3]
                        r1 = r1[:-3]
                        r2 = r2[:-3]
                else:
                    word = word[: -len(suffix)]
                    r1 = r1[: -len(suffix)]
                    r2 = r2[: -len(suffix)]
                break

        # STEP 5: Plurals
        if step3_success and len(r1) >= 1 and r1[-1] in "ij":
            word = word[:-1]
            r1 = r1[:-1]

        elif (
            not step3_success
            and len(r1) >= 2
            and r1[-1] == "t"
            and r1[-2] in self.__vowels
        ):
            word = word[:-1]
            r1 = r1[:-1]
            r2 = r2[:-1]
            if r2.endswith("imma"):
                word = word[:-4]
                r1 = r1[:-4]
            elif r2.endswith("mma") and r2[-5:-3] != "po":
                word = word[:-3]
                r1 = r1[:-3]

        # STEP 6: Tidying up
        if r1[-2:] in self.__long_vowels:
            word = word[:-1]
            r1 = r1[:-1]

        if len(r1) >= 2 and r1[-2] in self.__consonants and r1[-1] in "a\xe4ei":
            word = word[:-1]
            r1 = r1[:-1]

        if r1.endswith(("oj", "uj")):
            word = word[:-1]
            r1 = r1[:-1]

        if r1.endswith("jo"):
            word = word[:-1]
            r1 = r1[:-1]

        # If the word ends with a double consonant
        # followed by zero or more vowels, the last consonant is removed.
        for i in range(1, len(word)):
            if word[-i] in self.__vowels:
                continue
            else:
                if i == 1:
                    if word[-i - 1 :] in self.__double_consonants:
                        word = word[:-1]
                else:
                    if word[-i - 1 : -i + 1] in self.__double_consonants:
                        word = "".join((word[:-i], word[-i + 1 :]))
                break

        return word
