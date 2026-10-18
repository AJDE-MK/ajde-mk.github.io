# Align English to Cyrillic (agent instructions)

Goal: every Cyrillic lyric line gets one English line beside it. Songs are Macedonian folk songs.
Input files: `D:\Repos\Macedonian\data\work\NNNN.json` (you get a list of ids).
Output files: `D:\Repos\Macedonian\data\work_out\NNNN.json` (create the folder if missing). Write nothing else. Do not edit the input files or anything under `songbook`.

## Input shape
- `kind`: `"verify"` or `"align"`.
- `versions[i].stanzas[j]`: `{"cyr": [lines], "lat": [lines]}`. Songs with more than one version have more than one entry.
- `pesna_english_stanzas`: English from Pesna.org, as a list of stanzas, each a list of lines. It is the only trusted English.
- `proposed_en_version_0`: for `verify` only. A line-for-line pairing a script made by position. Same shape as version 0 stanzas.

## What to do
**kind = verify.** Read each Cyrillic line next to its proposed English line. If every pair means the same thing (wording may differ), write `{"id": N, "status": "ok"}` and nothing else. If lines are shifted or mismatched anywhere, fix it (see align rules) and write status `"fixed"` with the full `versions` output.

**kind = align.** Produce English for every Cyrillic line in every version.
1. Reuse Pesna's words. Move only the line breaks, so each English line carries the meaning of its Cyrillic line. Do not reword Pesna's text. Fix nothing else about it, not even typos.
2. Pesna English may cover only version 1, may skip repeated lines or refrains, or may merge lines. Where Pesna has no words for a Cyrillic line (an omitted repeat, a missing refrain, version 2 or 3), write your own English translation of that line. If the line repeats an earlier Cyrillic line, copy that line's English.
3. Mark every line you wrote yourself with `true` in `mt`. Lines made from Pesna's words get `false`.
4. Same number of `en` lines as `cyr` lines in every stanza. Same number of stanzas.
5. Never type an em-dash or en-dash (U+2014, U+2013). Use a comma, colon, or plain hyphen.

## Output shape
```json
{"id": 4, "status": "aligned",
 "versions": [
  {"index": 0, "stanzas": [
    {"en": ["line one", "line two"], "mt": [false, true]}
  ]}
 ]}
```
Status values: `"ok"` (verify, no change), `"fixed"` (verify, corrected), `"aligned"` (align).
Write JSON with real UTF-8 characters. Include a `"notes"` string only when you are unsure about a song.

## Final report (keep it short)
One line of counts: ok / fixed / aligned. Then the ids you were unsure about, one short phrase each.
