"""Calculs locaux indépendants de l'interface, sans fusion des blocs sources."""
from collections import Counter
from statistics import mean, median, pstdev


def sequence_stats(blocks, start, end):
    """Positions inclusives, numérotées à partir de 1."""
    if not 1 <= start <= end <= len(blocks):
        raise ValueError('Intervalle de blocs invalide')
    selected = blocks[start - 1:end]
    lengths = [b.words for b in selected if b.kind in ('paragraphe', 'dialogue')]
    marks = Counter(m['mark'] for b in selected for m in b.marks)
    return {
        'debut': start, 'fin': end, 'blocs': len(selected),
        'mots': sum(b.words for b in selected),
        'paragraphes_non_vides': len(lengths),
        'dialogues': sum(b.kind == 'dialogue' for b in selected),
        'silences': sum(b.kind == 'silence' for b in selected),
        'blancs': sum(b.kind == 'blanc' for b in selected),
        'moyenne': mean(lengths) if lengths else 0,
        'mediane': median(lengths) if lengths else 0,
        'ecart_type': pstdev(lengths) if lengths else 0,
        'minimum': min(lengths) if lengths else 0,
        'maximum': max(lengths) if lengths else 0,
        'ponctuation': dict(sorted(marks.items())),
        'longueurs': [b.words for b in selected],
    }
