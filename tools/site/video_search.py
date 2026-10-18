"""Find candidate YouTube videos for the best-known songs. Highest views wins, not newest upload.

Never edits data/videos.json. It writes data/videos.candidates.json and docs/video-candidates.md
for a person to check, then `videos_tool.py add` moves approved ones across.

Usage: python tools\\site\\video_search.py [--count 30] [--delay 1.5] [--debug]
Debug log: data/video_search.log
"""
import argparse
import json
import logging
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import songs as songs_data  # noqa: E402

log = logging.getLogger("site.video_search")

MAX_SECONDS = 600
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "CONSENT=YES+cb; SOCS=CAI",
}


def parse_views(text):
    """'1,234,567 views' -> 1234567; '1.2M views' -> 1200000; anything unreadable -> 0."""
    if not text:
        return 0
    m = re.search(r"([\d][\d.,]*)\s*([KMB])?\s*views?", text, re.I)
    if not m:
        return 0
    number = float(m.group(1).replace(",", ""))
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get((m.group(2) or "").upper(), 1)
    return int(round(number * mult))


def parse_duration(text):
    """'4:05' -> 245, '1:02:03' -> 3723, None (live stream) -> None."""
    if not text:
        return None
    try:
        parts = [int(p) for p in text.strip().split(":")]
    except ValueError:
        return None
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def _text(node):
    if not node:
        return ""
    if "simpleText" in node:
        return node["simpleText"]
    return "".join(r.get("text", "") for r in node.get("runs", []))


def _walk(node, found):
    if isinstance(node, dict):
        if "videoRenderer" in node:
            found.append(node["videoRenderer"])
        for v in node.values():
            _walk(v, found)
    elif isinstance(node, list):
        for v in node:
            _walk(v, found)


def extract_results(page):
    """Video results from a YouTube search page's embedded data. Empty list if none found."""
    marker = "ytInitialData = "
    start = page.find(marker)
    if start == -1:
        return []
    brace = page.find("{", start)
    try:
        data, _ = json.JSONDecoder().raw_decode(page[brace:])
    except ValueError:
        log.debug("could not decode ytInitialData")
        return []
    renderers = []
    _walk(data, renderers)
    results, seen = [], set()
    for r in renderers:
        vid = r.get("videoId")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        results.append(
            {
                "id": vid,
                "title": _text(r.get("title")),
                "channel": _text(r.get("ownerText")),
                "views": parse_views(_text(r.get("viewCountText"))),
                "seconds": parse_duration(_text(r.get("lengthText")) or None),
            }
        )
    return results


def _normalize(text):
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[^\w]+", " ", text).split()


def title_matches(song, video_title):
    """True when the video title carries (nearly) all the words of the song title, in Cyrillic or Latin."""
    video_words = set(_normalize(video_title))
    for title in (song["title_cyr"], song["title_latin"]):
        words = set(_normalize(title))
        if not words:
            continue
        hits = len(words & video_words)
        if hits >= min(2, len(words)) and hits / len(words) >= 0.8:
            return True
    return False


def choose_best(song, results, embeddable=None, max_seconds=MAX_SECONDS):
    """Highest-viewed matching video that is a normal length and, if checked, embeddable."""
    for r in sorted(results, key=lambda x: x["views"], reverse=True):
        if not title_matches(song, r["title"]):
            continue
        if r["seconds"] is None or r["seconds"] > max_seconds:
            continue
        if embeddable is not None and not embeddable(r["id"]):
            log.debug("skip %s: not embeddable", r["id"])
            continue
        return r
    return None


def _default_opener(url):
    try:
        with urlopen(Request(url, headers=HEADERS), timeout=20) as resp:
            return resp.status
    except HTTPError as err:
        return err.code


def is_embeddable(video_id, opener=None):
    """YouTube's oEmbed answers 200 for videos that allow embedding and 401 or 403 when they do not."""
    opener = opener or _default_opener
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        return opener(url) == 200
    except Exception as err:  # network trouble means "not confirmed"
        log.debug("oembed check failed for %s: %s", video_id, err)
        return False


def fetch_search_page(query):
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}&sp=EgIQAQ%253D%253D"
    with urlopen(Request(url, headers=HEADERS), timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def youtube_search(query, fetch=None):
    fetch = fetch or fetch_search_page
    results = extract_results(fetch(query))
    log.debug("query %r gave %d results", query, len(results))
    return results


def popular_songs(songs, n):
    """Songs with the most performers on Pesna.org, as a stand-in for well known."""
    ranked = sorted(songs, key=lambda s: (len(s["performers"]), len(s["audio"]), -s["id"]), reverse=True)
    return ranked[:n]


def find_candidate(song, search=youtube_search, embeddable=is_embeddable, delay=0.0):
    pool, seen = [], set()
    for query in (f"{song['title_cyr']} песна", f"{song['title_latin']} makedonska pesna"):
        for r in search(query):
            if r["id"] not in seen:
                seen.add(r["id"])
                pool.append(r)
        if delay:
            time.sleep(delay)
    return choose_best(song, pool, embeddable=embeddable)


def _review_markdown(candidates, missing):
    lines = [
        "# Video candidates",
        "",
        f"Generated {date.today().isoformat()}. For each song, the matching video with the most views.",
        "Click each link and listen. Add the ones you approve with `python tools\\site\\videos_tool.py add <song> <link>`.",
        "",
        "| Song | Song title | Video title | Channel | Views | Length | Link |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for c in candidates:
        mins, secs = divmod(c["seconds"], 60)
        lines.append(
            f"| {c['song_id']} | {c['title_cyr']} ({c['title_en']}) | {c['video_title']} | {c['channel']} "
            f"| {c['views']:,} | {mins}:{secs:02d} | [watch]({c['url']}) |"
        )
    if missing:
        lines += ["", "## No suitable video found", ""]
        lines += [f"- {m['song_id']}: {m['title_cyr']} ({m['title_en']})" for m in missing]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=30, help="how many songs to look up")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between searches")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args(argv)

    handlers = [logging.FileHandler(config.DATA_DIR / "video_search.log", mode="w", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(levelname)s %(name)s %(message)s", force=True
    )
    sys.stdout.reconfigure(encoding="utf-8")

    existing = set(songs_data.load_videos())
    targets = [s for s in popular_songs(songs_data.load_songs(), args.count * 2) if s["id"] not in existing]
    targets = targets[: args.count]
    candidates, missing = [], []
    for song in targets:
        try:
            best = find_candidate(song, delay=args.delay)
        except Exception as err:
            log.error("search failed for %s: %s", song["id"], err)
            print(f"song {song['id']}: search failed ({err})")
            best = None
        if best:
            candidates.append(
                {
                    "song_id": song["id"],
                    "title_cyr": song["title_cyr"],
                    "title_en": song["title_en"],
                    "video_id": best["id"],
                    "video_title": best["title"],
                    "channel": best["channel"],
                    "views": best["views"],
                    "seconds": best["seconds"],
                    "url": f"https://www.youtube.com/watch?v={best['id']}",
                    "embeddable": True,
                }
            )
            print(f"song {song['id']}: {best['views']:,} views  {best['title']}")
        else:
            missing.append({"song_id": song["id"], "title_cyr": song["title_cyr"], "title_en": song["title_en"]})
            print(f"song {song['id']}: no suitable video")
    out = config.DATA_DIR / "videos.candidates.json"
    out.write_text(
        json.dumps({"generated": date.today().isoformat(), "candidates": candidates, "no_match": missing},
                   ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    review = config.ROOT / "docs" / "video-candidates.md"
    review.write_text(_review_markdown(candidates, missing), encoding="utf-8")
    print(f"candidates: {len(candidates)}  no match: {len(missing)}  written to {out} and {review}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
