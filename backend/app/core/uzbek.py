"""Conservative normalization for Latin, Cyrillic, and mixed Uzbek text."""
import re
import unicodedata

_APOSTROPHES = "'‘’`´ʻʼ"


def normalize_uzbek(text: str) -> str:
    text = unicodedata.normalize('NFC', text)
    text = re.sub(rf"(?<=[OoGg])[{_APOSTROPHES}](?=\w|\s|$)", 'ʻ', text)
    return ' '.join(text.split())

_ONES = ('nol', 'bir', 'ikki', 'uch', 'toʻrt', 'besh', 'olti', 'yetti', 'sakkiz', 'toʻqqiz')
_TENS = ('', 'oʻn', 'yigirma', 'oʻttiz', 'qirq', 'ellik', 'oltmish', 'yetmish', 'sakson', 'toʻqson')


def _integer_words(value: int) -> str:
    if value < 10:
        return _ONES[value]
    for unit, label in ((10**9, 'milliard'), (10**6, 'million'), (1000, 'ming'), (100, 'yuz')):
        if value >= unit:
            count, remainder = divmod(value, unit)
            return f'{_integer_words(count)} {label}' + (f' {_integer_words(remainder)}' if remainder else '')
    tens, ones = divmod(value, 10)
    return _TENS[tens] + (f' {_ONES[ones]}' if ones else '')


def normalize_uzbek_for_speech(text: str) -> str:
    text = normalize_uzbek(text)
    text = re.sub(r'(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)',
                  lambda m: f'{_integer_words(int(m[1]))} {_integer_words(int(m[2]))}', text)
    text = re.sub(r'(?<![\w.])([0-9]{1,10})(?!\d)', lambda m: _integer_words(int(m[1])), text)
    return text.replace('ʻ', "'")
