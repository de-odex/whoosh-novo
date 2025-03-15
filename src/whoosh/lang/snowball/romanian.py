from .bases import _StandardStemmer


class RomanianStemmer(_StandardStemmer):
    """
    The Romanian Snowball stemmer.

    :cvar __vowels: The Romanian vowels.
    :type __vowels: unicode
    :cvar __step0_suffixes: Suffixes to be deleted in step 0 of the algorithm.
    :type __step0_suffixes: tuple
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :note: A detailed description of the Romanian
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/romanian/stemmer.html

    """

    __vowels = "aeiou\u0103\xe2\xee"
    __step0_suffixes = (
        "iilor",
        "ului",
        "elor",
        "iile",
        "ilor",
        "atei",
        "a\u0163ie",
        "a\u0163ia",
        "aua",
        "ele",
        "iua",
        "iei",
        "ile",
        "ul",
        "ea",
        "ii",
    )
    __step1_suffixes = (
        "abilitate",
        "abilitati",
        "abilit\u0103\u0163i",
        "ibilitate",
        "abilit\u0103i",
        "ivitate",
        "ivitati",
        "ivit\u0103\u0163i",
        "icitate",
        "icitati",
        "icit\u0103\u0163i",
        "icatori",
        "ivit\u0103i",
        "icit\u0103i",
        "icator",
        "a\u0163iune",
        "atoare",
        "\u0103toare",
        "i\u0163iune",
        "itoare",
        "iciva",
        "icive",
        "icivi",
        "iciv\u0103",
        "icala",
        "icale",
        "icali",
        "ical\u0103",
        "ativa",
        "ative",
        "ativi",
        "ativ\u0103",
        "atori",
        "\u0103tori",
        "itiva",
        "itive",
        "itivi",
        "itiv\u0103",
        "itori",
        "iciv",
        "ical",
        "ativ",
        "ator",
        "\u0103tor",
        "itiv",
        "itor",
    )
    __step2_suffixes = (
        "abila",
        "abile",
        "abili",
        "abil\u0103",
        "ibila",
        "ibile",
        "ibili",
        "ibil\u0103",
        "atori",
        "itate",
        "itati",
        "it\u0103\u0163i",
        "abil",
        "ibil",
        "oasa",
        "oas\u0103",
        "oase",
        "anta",
        "ante",
        "anti",
        "ant\u0103",
        "ator",
        "it\u0103i",
        "iune",
        "iuni",
        "isme",
        "ista",
        "iste",
        "isti",
        "ist\u0103",
        "i\u015fti",
        "ata",
        "at\u0103",
        "ati",
        "ate",
        "uta",
        "ut\u0103",
        "uti",
        "ute",
        "ita",
        "it\u0103",
        "iti",
        "ite",
        "ica",
        "ice",
        "ici",
        "ic\u0103",
        "osi",
        "o\u015fi",
        "ant",
        "iva",
        "ive",
        "ivi",
        "iv\u0103",
        "ism",
        "ist",
        "at",
        "ut",
        "it",
        "ic",
        "os",
        "iv",
    )
    __step3_suffixes = (
        "seser\u0103\u0163i",
        "aser\u0103\u0163i",
        "iser\u0103\u0163i",
        "\xe2ser\u0103\u0163i",
        "user\u0103\u0163i",
        "seser\u0103m",
        "aser\u0103m",
        "iser\u0103m",
        "\xe2ser\u0103m",
        "user\u0103m",
        "ser\u0103\u0163i",
        "sese\u015fi",
        "seser\u0103",
        "easc\u0103",
        "ar\u0103\u0163i",
        "ur\u0103\u0163i",
        "ir\u0103\u0163i",
        "\xe2r\u0103\u0163i",
        "ase\u015fi",
        "aser\u0103",
        "ise\u015fi",
        "iser\u0103",
        "\xe2se\u015fi",
        "\xe2ser\u0103",
        "use\u015fi",
        "user\u0103",
        "ser\u0103m",
        "sesem",
        "indu",
        "\xe2ndu",
        "eaz\u0103",
        "e\u015fti",
        "e\u015fte",
        "\u0103\u015fti",
        "\u0103\u015fte",
        "ea\u0163i",
        "ia\u0163i",
        "ar\u0103m",
        "ur\u0103m",
        "ir\u0103m",
        "\xe2r\u0103m",
        "asem",
        "isem",
        "\xe2sem",
        "usem",
        "se\u015fi",
        "ser\u0103",
        "sese",
        "are",
        "ere",
        "ire",
        "\xe2re",
        "ind",
        "\xe2nd",
        "eze",
        "ezi",
        "esc",
        "\u0103sc",
        "eam",
        "eai",
        "eau",
        "iam",
        "iai",
        "iau",
        "a\u015fi",
        "ar\u0103",
        "u\u015fi",
        "ur\u0103",
        "i\u015fi",
        "ir\u0103",
        "\xe2\u015fi",
        "\xe2r\u0103",
        "ase",
        "ise",
        "\xe2se",
        "use",
        "a\u0163i",
        "e\u0163i",
        "i\u0163i",
        "\xe2\u0163i",
        "sei",
        "ez",
        "am",
        "ai",
        "au",
        "ea",
        "ia",
        "ui",
        "\xe2i",
        "\u0103m",
        "em",
        "im",
        "\xe2m",
        "se",
    )

    def stem(self, word):
        """
        Stem a Romanian word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        step1_success = False
        step2_success = False

        for i in range(1, len(word) - 1):
            if word[i - 1] in self.__vowels and word[i + 1] in self.__vowels:
                if word[i] == "u":
                    word = "".join((word[:i], "U", word[i + 1 :]))

                elif word[i] == "i":
                    word = "".join((word[:i], "I", word[i + 1 :]))

        r1, r2 = self._r1r2_standard(word, self.__vowels)
        rv = self._rv_standard(word, self.__vowels)

        # STEP 0: Removal of plurals and other simplifications
        for suffix in self.__step0_suffixes:
            if word.endswith(suffix):
                if suffix in r1:
                    if suffix in ("ul", "ului"):
                        word = word[: -len(suffix)]

                        if suffix in rv:
                            rv = rv[: -len(suffix)]
                        else:
                            rv = ""

                    elif (
                        suffix == "aua"
                        or suffix == "atei"
                        or (suffix == "ile" and word[-5:-3] != "ab")
                    ):
                        word = word[:-2]

                    elif suffix in ("ea", "ele", "elor"):
                        word = "".join((word[: -len(suffix)], "e"))

                        if suffix in rv:
                            rv = "".join((rv[: -len(suffix)], "e"))
                        else:
                            rv = ""

                    elif suffix in ("ii", "iua", "iei", "iile", "iilor", "ilor"):
                        word = "".join((word[: -len(suffix)], "i"))

                        if suffix in rv:
                            rv = "".join((rv[: -len(suffix)], "i"))
                        else:
                            rv = ""

                    elif suffix in ("a\u0163ie", "a\u0163ia"):
                        word = word[:-1]
                break

        # STEP 1: Reduction of combining suffixes
        while True:
            replacement_done = False

            for suffix in self.__step1_suffixes:
                if word.endswith(suffix):
                    if suffix in r1:
                        step1_success = True
                        replacement_done = True

                        if suffix in (
                            "abilitate",
                            "abilitati",
                            "abilit\u0103i",
                            "abilit\u0103\u0163i",
                        ):
                            word = "".join((word[: -len(suffix)], "abil"))

                        elif suffix == "ibilitate":
                            word = word[:-5]

                        elif suffix in (
                            "ivitate",
                            "ivitati",
                            "ivit\u0103i",
                            "ivit\u0103\u0163i",
                        ):
                            word = "".join((word[: -len(suffix)], "iv"))

                        elif suffix in (
                            "icitate",
                            "icitati",
                            "icit\u0103i",
                            "icit\u0103\u0163i",
                            "icator",
                            "icatori",
                            "iciv",
                            "iciva",
                            "icive",
                            "icivi",
                            "iciv\u0103",
                            "ical",
                            "icala",
                            "icale",
                            "icali",
                            "ical\u0103",
                        ):
                            word = "".join((word[: -len(suffix)], "ic"))

                        elif suffix in (
                            "ativ",
                            "ativa",
                            "ative",
                            "ativi",
                            "ativ\u0103",
                            "a\u0163iune",
                            "atoare",
                            "ator",
                            "atori",
                            "\u0103toare",
                            "\u0103tor",
                            "\u0103tori",
                        ):
                            word = "".join((word[: -len(suffix)], "at"))

                            if suffix in r2:
                                r2 = "".join((r2[: -len(suffix)], "at"))

                        elif suffix in (
                            "itiv",
                            "itiva",
                            "itive",
                            "itivi",
                            "itiv\u0103",
                            "i\u0163iune",
                            "itoare",
                            "itor",
                            "itori",
                        ):
                            word = "".join((word[: -len(suffix)], "it"))

                            if suffix in r2:
                                r2 = "".join((r2[: -len(suffix)], "it"))
                    else:
                        step1_success = False
                    break

            if not replacement_done:
                break

        # STEP 2: Removal of standard suffixes
        for suffix in self.__step2_suffixes:
            if word.endswith(suffix):
                if suffix in r2:
                    step2_success = True

                    if suffix in ("iune", "iuni"):
                        if word[-5] == "\u0163":
                            word = "".join((word[:-5], "t"))

                    elif suffix in (
                        "ism",
                        "isme",
                        "ist",
                        "ista",
                        "iste",
                        "isti",
                        "ist\u0103",
                        "i\u015fti",
                    ):
                        word = "".join((word[: -len(suffix)], "ist"))

                    else:
                        word = word[: -len(suffix)]
                break

        # STEP 3: Removal of verb suffixes
        if not step1_success and not step2_success:
            for suffix in self.__step3_suffixes:
                try:
                    if word.endswith(suffix):
                        if suffix in rv:
                            if suffix in (
                                "seser\u0103\u0163i",
                                "seser\u0103m",
                                "ser\u0103\u0163i",
                                "sese\u015fi",
                                "seser\u0103",
                                "ser\u0103m",
                                "sesem",
                                "se\u015fi",
                                "ser\u0103",
                                "sese",
                                "a\u0163i",
                                "e\u0163i",
                                "i\u0163i",
                                "\xe2\u0163i",
                                "sei",
                                "\u0103m",
                                "em",
                                "im",
                                "\xe2m",
                                "se",
                            ):
                                word = word[: -len(suffix)]
                                rv = rv[: -len(suffix)]
                            else:
                                if (
                                    not rv.startswith(suffix)
                                    and rv[rv.index(suffix) - 1]
                                    not in "aeio\u0103\xe2\xee"
                                ):
                                    word = word[: -len(suffix)]
                            break
                except UnicodeDecodeError:
                    # The word is unicode, but suffix is not
                    continue

        # STEP 4: Removal of final vowel
        for suffix in ("ie", "a", "e", "i", "\u0103"):
            if word.endswith(suffix):
                if suffix in rv:
                    word = word[: -len(suffix)]
                break

        word = word.replace("I", "i").replace("U", "u")
        return word
