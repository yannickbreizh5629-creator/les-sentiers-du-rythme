"""Moteur descriptif V0.1 : aucune modification du texte source."""
import re
from dataclasses import dataclass, asdict
from odf.opendocument import load
from odf import teletype

WORD = re.compile(r"[^\W_]+(?:[’'-][^\W_]+)*", re.UNICODE)
PUNCT = re.compile(r"[,:;.!?…]+|[—–]", re.UNICODE)
SILENCE = re.compile(r"\s*(?:\.{3,}|…+)\s*")

@dataclass
class Block:
    index: int
    text: str
    kind: str
    words: int
    segments: list
    marks: list


def read_odt(path):
    doc = load(path)
    blocks = []
    for element in doc.text.childNodes:
        if element.qname[1] not in ('p', 'h'):
            continue
        # Conserve les paragraphes vides, et les sauts de ligne internes en les représentant dans le texte.
        blocks.append(teletype.extractText(element))
    return blocks


def analyze(texts):
    output = []
    for i, text in enumerate(texts):
        if not text.strip(): kind = 'blanc'
        elif SILENCE.fullmatch(text): kind = 'silence'
        elif text.lstrip().startswith(('—', '–', '-')): kind = 'dialogue'
        else: kind = 'paragraphe'
        # Segments séparés aux ponctuations fortes ET faibles ; chaque signe reste disponible.
        matches = list(PUNCT.finditer(text))
        segments, start = [], 0
        for match in matches:
            piece = text[start:match.start()]
            if piece.strip():
                segments.append({'text':piece, 'words':len(WORD.findall(piece)), 'end_mark':match.group()})
            start = match.end()
        if text[start:].strip():
            piece=text[start:]
            segments.append({'text':piece,'words':len(WORD.findall(piece)), 'end_mark':''})
        output.append(Block(i, text, kind, len(WORD.findall(text)), segments,
                            [{'mark':m.group(), 'offset':m.start()} for m in matches]))
    return output


def export_json(blocks):
    return [asdict(b) for b in blocks]
