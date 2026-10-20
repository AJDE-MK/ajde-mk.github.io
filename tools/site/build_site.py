"""Build the static site into an output folder.

Usage: python tools\\site\\build_site.py [--out DIR] [--debug] [--only-skeleton]
Debug log is always written to data/site_build.log.
Exit code 0 on success, 1 if videos.json has problems.
"""
import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import layout  # noqa: E402
import bulk_videos as b1  # noqa: E402
import bulk_videos2 as b2  # noqa: E402
import render_pages  # noqa: E402
import render_song  # noqa: E402
import review_queue  # noqa: E402
import songs as songs_data  # noqa: E402
import videos_tool  # noqa: E402

log = logging.getLogger("site.build")


def _write(out, rel, text):
    target = Path(out) / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    log.debug("wrote %s", rel)


def copy_static(out):
    dest = Path(out) / "static"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(config.STATIC_DIR, dest)
    log.debug("copied static to %s", dest)


def build_skeleton(out):
    body = f"<h1>{config.SITE_TITLE}</h1>"
    _write(out, "index.html", layout.page(config.SITE_TITLE, body, active="home"))
    copy_static(out)


def _raw_videos():
    if config.VIDEOS_FILE.exists():
        return json.loads(config.VIDEOS_FILE.read_text(encoding="utf-8"))
    return {}


def _not_found():
    body = (
        "<h1>Page not found</h1>"
        f'<p>That page does not exist. Try the <a href="{layout.url("/songs/")}">song list</a> '
        f'or go back to the <a href="{layout.url("/")}">home page</a>.</p>'
    )
    return layout.page("Page not found", body)


def build_all(out):
    """Write every page. Returns 0, or 1 when videos.json has problems (nothing is written then)."""
    all_songs = songs_data.load_songs()
    problems = videos_tool.validate_videos(_raw_videos(), {s["id"] for s in all_songs})
    if problems:
        for p in problems:
            print("videos.json:", p)
        log.error("videos.json problems: %s", problems)
        return 1
    videos = songs_data.load_videos()
    review_rows = review_queue.page_order(
        review_queue.build_queue(
            b1.load_progress(b1.PROGRESS_FILE),
            b1.load_progress(b2.PROGRESS2_FILE),
            {s["id"]: s for s in all_songs},
            videos,
            review_queue.load_decisions(),
        )
    )

    copy_static(out)
    _write(out, "index.html", render_pages.render_home(all_songs, videos, review_count=len(review_rows)))
    _write(out, "needs-video/index.html",
           render_pages.render_needs_video(all_songs, videos, review_count=len(review_rows)))
    _write(out, "review/index.html", render_pages.render_review(review_rows, config.FORM_KEY))
    _write(out, "songs/index.html", render_pages.render_browse(all_songs))
    _write(out, "alphabet/index.html", render_pages.render_alphabet())
    _write(out, "progress/index.html", render_pages.render_progress())
    _write(out, "about/index.html", render_pages.render_about())
    _write(out, "404.html", _not_found())
    _write(out, ".nojekyll", "")
    _write(
        out,
        "search-index.json",
        json.dumps(render_pages.build_search_index(all_songs), ensure_ascii=False, separators=(",", ":")),
    )
    for song in all_songs:
        rel = f"songs/{song['id']:04d}-{song['slug']}/index.html"
        _write(out, rel, render_song.render_song_page(song, videos.get(song["id"])))
    log.debug("built %d song pages", len(all_songs))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(config.SITE_DIR))
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--only-skeleton", action="store_true")
    args = ap.parse_args(argv)

    handlers = [logging.FileHandler(config.LOG_FILE, mode="w", encoding="utf-8")]
    if args.debug:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG, handlers=handlers, format="%(levelname)s %(name)s %(message)s", force=True
    )

    Path(args.out).mkdir(parents=True, exist_ok=True)
    if args.only_skeleton:
        build_skeleton(args.out)
        return 0
    return build_all(args.out)


if __name__ == "__main__":
    sys.exit(main())
