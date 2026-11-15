"""Reject incomplete HTML documents before submitting them to browser checks."""
from html.parser import HTMLParser
import re


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.starts = []
        self.ends = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        self.starts.append(tag)
        self.ids.extend(value for key, value in attrs if key == "id")

    def handle_endtag(self, tag):
        self.ends.append(tag)


def validate_html(source):
    if not re.search(r"<!doctype\s+html\s*>", source, re.I):
        raise ValueError("Return a complete HTML document including <!DOCTYPE html>")
    document = Document()
    document.feed(source)
    document.close()
    for tag in ("html", "head", "title", "body"):
        if document.starts.count(tag) != 1 or document.ends.count(tag) != 1:
            raise ValueError(f"Expected one complete <{tag}> element")
    if document.starts.count("script") != document.ends.count("script"):
        raise ValueError("Unclosed script element")
    if len(document.ids) != len(set(document.ids)):
        raise ValueError("Duplicate HTML element IDs")
