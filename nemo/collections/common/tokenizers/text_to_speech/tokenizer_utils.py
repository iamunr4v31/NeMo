# Copyright (c) 2023, NVIDIA CORPORATION & AFFILIATES.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import string
import unicodedata
from builtins import str as unicode
from typing import List, Tuple

try:
    from indicnlp.syllable import syllabifier
except ImportError:
    pass

__all__ = [
    "chinese_text_preprocessing",
    "english_text_preprocessing",
    "any_locale_text_preprocessing",
    "spanish_text_preprocessing",
    "any_locale_word_tokenize",
    "english_word_tokenize",
    "LATIN_CHARS_ALL",
    "normalize_unicode_text",
    "indic_syllable_text_processing",
    "indic_syllable_text_processing_improved",
]

# Derived from LJSpeech
_synoglyphs = {
    "'": ['’'],
    '"': ['”', '“'],
}
SYNOGLYPH2ASCII = {g: asc for asc, glyphs in _synoglyphs.items() for g in glyphs}

# Example of parsing by groups via _WORDS_RE_EN.
# Regular expression pattern groups:
#   1st group -- valid english words,
#   2nd group -- any substring starts from | to | (mustn't be nested), useful when you want to leave sequence unchanged,
#   3rd group -- punctuation marks or whitespaces.
# Text (first line) and mask of groups for every char (second line).
# config file must contain |EY1 EY1|, B, C, D, E, F, and G.

# define char set based on https://en.wikipedia.org/wiki/List_of_Unicode_characters
LATIN_ALPHABET_BASIC = "A-Za-z"
ACCENTED_CHARS = "À-ÖØ-öø-ÿ"
LATIN_CHARS_ALL = f"{LATIN_ALPHABET_BASIC}{ACCENTED_CHARS}"
_WORDS_RE_EN = re.compile(
    fr"([{LATIN_ALPHABET_BASIC}]+(?:[{LATIN_ALPHABET_BASIC}\-']*[{LATIN_ALPHABET_BASIC}]+)*)|(\|[^|]*\|)|([^{LATIN_ALPHABET_BASIC}|]+)"
)
_WORDS_RE_ANY_LOCALE = re.compile(
    fr"([{LATIN_CHARS_ALL}]+(?:[{LATIN_CHARS_ALL}\-']*[{LATIN_CHARS_ALL}]+)*)|(\|[^|]*\|)|([^{LATIN_CHARS_ALL}|]+)"
)


def english_text_preprocessing(text, lower=True):
    text = unicode(text)
    text = ''.join(char for char in unicodedata.normalize('NFD', text) if unicodedata.category(char) != 'Mn')
    text = ''.join(char if char not in SYNOGLYPH2ASCII else SYNOGLYPH2ASCII[char] for char in text)

    if lower:
        text = text.lower()

    return text


def indic_syllable_text_processing(text, lang_symbols):
    """
    Process text for Indic syllable extraction.

    Args:
        text (str): The input text to be processed.
        lang_symbols (Iterable): The list of language-specific symbols. Could be a list, set or a tuple

    Returns:
        list: A list of clusters representing syllables extracted from the text.

    The function performs Indic syllable extraction on the provided text. It removes any digits, punctuation, and whitespace 
    characters from the text and then groups the remaining characters into clusters based on the language-specific symbols 
    provided. Each cluster represents a syllable.

    Example:
        >>> text = "असरारे मआबिद- उर्दू साप्ताहिक आवाज-ए-खल्क़"
        >>> lang_symbols = {"ा", "ि", "ी", "ु", "ू", "ृ", "े", "ै", "ो", "ौ", "्", "ं", "ः", "ऽ", "़", "ॄ", "ँ"}
        >>> indic_syllable_text_processing(text, lang_symbols)
        ["अ", "स", "रा", "रे", " ", "म", "आ", "बि", "द", " ", "उ", "र्", "दू", " ", "सा", "प्", "ता", "हि", "क", " ", "आ", "वा", "ज", "ए", "ख", "ल्", "क़"]
    """
    text = any_locale_text_preprocessing(text)

    clusters = []
    current_cluster = ""
    for i, char in enumerate(text):
        if char.isdigit() or char in string.punctuation or char in string.whitespace:
            continue
        if i == 0:
            current_cluster += char
        else:
            if char in lang_symbols:
                current_cluster += char
            else:
                clusters.append(current_cluster)
                current_cluster = char
    clusters.append(current_cluster)
    return clusters


def indic_syllable_text_processing_improved(text: str, lang_id: str):
    """
    Process text for improved Indic syllable extraction.

    Args:
        text (str): The input text to be processed.
        lang_id (str): The ID of the Indic language. Refer to the indicnlp library for supported languages.

    Returns:
        list: A list of clusters representing syllables extracted from the text.

    The function performs improved Indic syllable extraction on the provided text using the specified Indic language.
    It first applies any necessary locale-specific text preprocessing to the input text. Then, it sets the resources path
    for the indic_nlp library based on the "INDIC_RESOURCES_ROOT" environment variable. After loading the necessary 
    resources, it utilizes the indic_nlp library's orthographic syllabification method to extract syllables from the text.

    Example:
        >>> text = "असरारे मआबिद- उर्दू साप्ताहिक आवाज-ए-खल्क़"
        >>> lang_id = "hi"
        >>> indic_syllable_text_processing_improved(text, lang_id)
        ['अ','स','रा','रे',' ','म','आ','बि','द','-','उ','र्दू',' ','सा','प्ता','हि','क',' ','आ','वा','ज','-','ए','-','ख','ल्क़','अ','स','रा','रे',' ','म','आ','बि','द','-','उ','र्दू',' ','सा','प्ता','हि','क',' ','आ','वा','ज','-','ए','-','ख','ल्क़']

    Note:
        - Ensure that the "INDIC_RESOURCES_ROOT" environment variable is set to the path containing the necessary 
          resources for Indic language processing.
        - The lang_id should correspond to one of the supported Indic languages. Refer to the indicnlp library for a list
          of supported languages.
    """
    text = any_locale_text_preprocessing(text)
    words = text.split()
    syllables = []
    try:
        for i, word in enumerate(words):
            syllables += syllabifier.orthographic_syllabify_improved(word, lang_id)
            syllables += [" "] if i != len(words) - 1 else []
    except NameError as e:
        if e.name == "syllabifier":
            raise ImportError("The indic_nlp library is not installed. Please install the indic_nlp library to use this function.")
    return syllables


def any_locale_text_preprocessing(text: str) -> str:
    """
    Normalize unicode text with "NFC", and convert right single quotation mark (U+2019, decimal 8217) as an apostrophe.

    Args:
        text (str): the original input sentence.

    Returns: normalized text (str).
    """
    res = []
    for c in normalize_unicode_text(text):
        if c in ['’']:  # right single quotation mark (U+2019, decimal 8217) as an apostrophe
            res.append("'")
        else:
            res.append(c)

    return ''.join(res)


def normalize_unicode_text(text: str) -> str:
    """
    TODO @xueyang: Apply NFC form may be too aggressive since it would ignore some accented characters that do not exist
      in predefined German alphabet (nemo.collections.common.tokenizers.text_to_speech.ipa_lexicon.IPA_CHARACTER_SETS),
      such as 'é'. This is not expected. A better solution is to add an extra normalization with NFD to discard the
      diacritics and consider 'é' and 'e' produce similar pronunciations.

    Note that the tokenizer needs to run `unicodedata.normalize("NFC", x)` before calling `encode` function,
    especially for the characters that have diacritics, such as 'ö' in the German alphabet. 'ö' can be encoded as
    b'\xc3\xb6' (one char) as well as b'o\xcc\x88' (two chars). Without the normalization of composing two chars
    together and without a complete predefined set of diacritics, when the tokenizer reads the input sentence
    char-by-char, it would skip the combining diaeresis b'\xcc\x88', resulting in indistinguishable pronunciations
    for 'ö' and 'o'.

    Args:
        text (str): the original input sentence.

    Returns:
        NFC normalized sentence (str).
    """
    # normalize word with NFC form
    if not unicodedata.is_normalized("NFC", text):
        text = unicodedata.normalize("NFC", text)

    return text


def _word_tokenize(words: List[Tuple[str, str, str]], is_lower: bool = False) -> List[Tuple[List[str], bool]]:
    """
    Process a list of words and attach indicators showing if each word is unchangeable or not. Each word representation
    can be one of valid word, any substring starting from | to | (unchangeable word), or punctuation marks including
    whitespaces. This function will split unchanged strings by whitespaces and return them as `List[str]`. For example,

    .. code-block:: python
        [
            ('Hello', '', ''),  # valid word
            ('', '', ' '),  # punctuation mark
            ('World', '', ''),  # valid word
            ('', '', ' '),  # punctuation mark
            ('', '|NVIDIA unchanged|', ''),  # unchangeable word
            ('', '', '!')  # punctuation mark
        ]

    will be converted into,

    .. code-block:: python
        [
            (["Hello"], False),
            ([" "], False),
            (["World"], False),
            ([" "], False),
            (["NVIDIA", "unchanged"], True),
            (["!"], False)
        ]

    Args:
        words (List[str]): a list of tuples like `(maybe_word, maybe_without_changes, maybe_punct)` where each element
            corresponds to a non-overlapping match of either `_WORDS_RE_EN` or `_WORDS_RE_ANY_LOCALE`.
        is_lower (bool): a flag to trigger lowercase all words. By default, it is False.

    Returns: List[Tuple[List[str], bool]], a list of tuples like `(a list of words, is_unchanged)`.

    """
    result = []
    for word in words:
        maybe_word, maybe_without_changes, maybe_punct = word

        without_changes = False
        if maybe_word != '':
            if is_lower:
                token = [maybe_word.lower()]
            else:
                token = [maybe_word]
        elif maybe_punct != '':
            token = [maybe_punct]
        elif maybe_without_changes != '':
            without_changes = True
            token = maybe_without_changes[1:-1].split(" ")
        else:
            raise ValueError(
                f"This is not expected. Found empty string: <{word}>. "
                f"Please validate your regular expression pattern '_WORDS_RE_EN' or '_WORDS_RE_ANY_LOCALE'."
            )

        result.append((token, without_changes))

    return result


def english_word_tokenize(text: str) -> List[Tuple[List[str], bool]]:
    words = _WORDS_RE_EN.findall(text)
    return _word_tokenize(words, is_lower=True)


def any_locale_word_tokenize(text: str) -> List[Tuple[List[str], bool]]:
    words = _WORDS_RE_ANY_LOCALE.findall(text)
    return _word_tokenize(words)


# TODO @xueyang: deprecate language-specific text preprocessing and use any_locale_text_preprocessing.
def spanish_text_preprocessing(text):
    return text.lower()


def chinese_text_preprocessing(text):
    return text.lower()
