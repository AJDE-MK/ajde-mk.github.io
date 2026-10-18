"""Load song and video data from the data folder."""
import json
import logging

import config

log = logging.getLogger("site.songs")


def load_songs():
    """All song records, sorted by id."""
    songs = []
    for path in sorted(config.SONGS_DIR.glob("*.json")):
        songs.append(json.loads(path.read_text(encoding="utf-8")))
    songs.sort(key=lambda s: s["id"])
    log.debug("loaded %d songs", len(songs))
    return songs


def load_videos():
    """Map song id (int) to {"id": youtube_id, "start": seconds}. Missing file means no videos."""
    if not config.VIDEOS_FILE.exists():
        return {}
    raw = json.loads(config.VIDEOS_FILE.read_text(encoding="utf-8"))
    videos = {int(k): v for k, v in raw.items()}
    log.debug("loaded %d videos", len(videos))
    return videos
