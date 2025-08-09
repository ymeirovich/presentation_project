from typing import Iterable

def to_title(s:str) -> str:
    """
    Return a human-friendly title-cased string.
    Pure function: input -> output; no I/O, no side effects.
    """
    # str.title() capitalizes first letter of each word
    # We also strip whitespace to be safe.
    return s.strip().title()

def comma_join(items:Iterable[str]) -> str:
    """
    Join an iterable of strings with commas and spaces.
    this keeps presentation code clean (slides, logs, etc.)
    """
    # Using ','.join(...) is idiomatic Python
    return ", ".join(items)