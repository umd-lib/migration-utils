#!/usr/bin/env python3

import sys
import re
from csv import DictReader, writer

import pykakasi

# Gather information about Japanese and Romaji forms of Creator names
# in Japanese language records.

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
    return re.sub(r'\s+', '', s.lower())


# CSV input and output
csvinput = DictReader(sys.stdin)
csvoutput = writer(sys.stdout)

csvoutput.writerow(['F2 PID', 'Creator', 'Japanese', 'Romaji', 'Romaji Norm',
                    'Hepburn norm', 'Hepburn distance',
                    'Kunrei', 'Kunrei distance',
                    'Passport', 'Passport distance'])

kks = pykakasi.kakasi()

for record in csvinput:
    lang = set(record['Language'].split('|'))

    if 'jpn' in lang and record['Creator'] != "":
        pid = record['F2 PID']
        creator = record['Creator'].split('|')
        row = [pid, record['Creator']]

        if len(creator) % 2 == 1:
            print(f'Error: odd creator count: {creator}')

        i = 0
        while i+1 < len(creator):
            jpn = creator[i]
            romaji = creator[i+1]

            row.append(jpn)
            row.append(romaji)

            romaji_norm = normalize(romaji)
            row.append(romaji_norm)

            k = kks.convert(jpn)

            for romanization in ('hepburn', 'kunrei', 'passport'):
                norm = normalize(''.join([x[romanization] for x in k]))
                score = levenshtein(romaji_norm, norm)
                row.append(norm)
                row.append(score)

            i += 2

        csvoutput.writerow(row)

