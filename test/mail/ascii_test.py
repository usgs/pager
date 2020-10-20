from copy import copy
import unicodedata


def _convert_ascii(text):
    """Temporary patch to encode text in ascii.

    Args:
        text (str): Text to convert to ascii encoding.
            any characters cannot be converted to ascii,
            then they are removed.

    Returns:
        str: text converted to ascii.
    """
    text = str(text)
    # Normalize characters and exclude leftovers with accents
    text = ''.join(c for c in unicodedata.normalize(
        'NFKD', text) if unicodedata.category(c) != 'Mn')
    # Remove any leftovers that cannot be normalized
    text = bytes(text, 'ascii', errors='ignore')
    return text.decode("utf-8")


def _is_ascii(text):
    """
    Args:
        text (str): Text to check.

    Returns:
        bool: whether or not the text can be encoded in ascii.
    """
    return all(ord(char) < 128 for char in text)


def convert_if_necessary(long_msg, subject, subject_update):
    # Code implemented in emailpager
    try:
        # Copy original text
        temp_message = copy(long_msg)
        temp_subject = copy(subject)
        temp_subject_update = copy(subject_update)

        # Check if the characters in the message and subject line are ascii
        if not _is_ascii(temp_subject):
            temp_subject = _convert_ascii(temp_subject)

        if not _is_ascii(temp_subject_update):
            temp_subject_update = _convert_ascii(temp_subject_update)

        if not _is_ascii(temp_message):
            temp_message = _convert_ascii(temp_message)

        # No errors in the check/convert so update
        long_msg = temp_message
        subject_update = temp_subject_update
        subject = temp_subject
    except:
        # If this code checking/encoding the text does not work
        # it should not change the original text
        pass
    return long_msg, subject, subject_update


def test_ascii_check():
    most_let_symb = ('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg'
                     'hijklmnopqrstuvwxyz,./<>?;:[]}{}1234567890-=_+')
    t1, t2, t3 = convert_if_necessary(
        most_let_symb, most_let_symb, most_let_symb)
    assert t1 == most_let_symb
    assert t2 == most_let_symb
    assert t3 == most_let_symb
    iceland = 'Hafnarfjörður, Iceland'
    ice_ascii = 'Hafnarfjorur, Iceland'
    mexico = 'María Xadani, Mexico'
    mex_ascii = 'Maria Xadani, Mexico'
    t4, t5, t6 = convert_if_necessary(iceland, mexico, iceland)
    assert t4 == ice_ascii
    assert t5 == mex_ascii
    assert t6 == ice_ascii
    t7, t8, t9 = convert_if_necessary(mexico, iceland, mexico)
    assert t7 == mex_ascii
    assert t8 == ice_ascii
    assert t9 == mex_ascii


if __name__ == '__main__':
    test_ascii_check()
