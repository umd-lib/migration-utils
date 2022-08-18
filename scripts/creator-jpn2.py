#!/usr/bin/env python3

import sys
import re
from csv import DictReader, writer

import pykakasi
import unicodeblock.blocks as blocks

# Determine the language of various metadata in Japanese language
# materials

def levenshtein(s, t):
    ''' From Wikipedia article; Iterative with two matrix rows.

    Christopher P. Matthews
    christophermatthews1985@gmail.com
    Sacramento, CA, USA
    https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python
    '''
    if s == t: return 0
    elif len(s) == 0: return len(t)
    elif len(t) == 0: return len(s)
    v0 = [None] * (len(t) + 1)
    v1 = [None] * (len(t) + 1)
    for i in range(len(v0)):
        v0[i] = i
    for i in range(len(s)):
        v1[0] = i + 1
        for j in range(len(t)):
            cost = 0 if s[i] == t[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        for j in range(len(v0)):
            v0[j] = v1[j]

    return v1[len(t)]


def normalize(s):
    ''' Normalize to a comparable form. '''
    s = s.lower()
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'[\[\]・･\',;.\-?]','', s)
    s = re.sub(r'\(.*?\)','',s)
    return s


def get_score(v1, v2):
    ''' Get scores: 
    1. v1 being Japanese and v2 being a Latin transliteration.
    2. v1 being katakana
    '''

    v1_norm = normalize(v1)
    v1_blocks = get_blocks(v1_norm)

    v2_norm = normalize(v2)
    v2_blocks = get_blocks(v2_norm)

    k = kks.convert(normalize(v1))

    min_score = 100

    for romanization in ('hepburn', 'kunrei', 'passport'):
        v1_norm_romanization = normalize(''.join([x[romanization] for x in k]))
        romanization_score = levenshtein(v1_norm_romanization, v2_norm)
        min_score = min(min_score, romanization_score)

    katakana_score = levenshtein(
        v1_norm,
        normalize(''.join([x['kana'] for x in k]))
    )

    return min_score, katakana_score, v1_blocks, v2_blocks


def get_blocks(v):
    ''' Get the Unicode block counts for the characters in the string. '''
    counts = {}
    for c in v:
        block = blocks.of(c)
        if block in counts:
            counts[block] += 1
        else:
            counts[block] = 1
    return counts


# CSV input and output
csvinput = DictReader(sys.stdin)
csvoutput = writer(sys.stdout)

csvoutput.writerow(['F2 PID', 'Creator', 'Value 1', 'Katakana Score', 'Blocks 1', 'Value 2', 'Blocks 2', 'Score'])

kks = pykakasi.kakasi()

for record in csvinput:
    lang = set(record['Language'].split('|'))

    if 'jpn' in lang and record['Creator'] != "":
        pid = record['F2 PID']
        creator = record['Creator'].split('|')

        if len(creator) % 2 == 1:
            print(f'Error: odd creator count: {creator}')

        i = 0
        while i+1 < len(creator):

            value1 = creator[i]
            value2 = creator[i+1]
            score, katakana_score, blocks1, blocks2 = get_score(value1, value2)

            csvoutput.writerow([pid, record['Creator'], value1, katakana_score, blocks1, value2, blocks2, score])

            i += 2

