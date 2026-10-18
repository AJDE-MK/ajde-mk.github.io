"""Shared page frame: head, border, nav, footer."""
import html
import logging

import config

log = logging.getLogger("site.layout")

NAV = [
    ("home", "Home", "/"),
    ("songs", "Songs", "/songs/"),
    ("alphabet", "Alphabet", "/alphabet/"),
    ("progress", "My progress", "/progress/"),
    ("about", "About", "/about/"),
]


def url(path):
    """Prefix a site path with BASE_PATH. `path` starts with '/'."""
    return f"{config.BASE_PATH}{path}"


def _nav(active):
    items = []
    for key, label, path in NAV:
        current = ' aria-current="page"' if key == active else ""
        items.append(f'<a href="{url(path)}"{current}>{html.escape(label)}</a>')
    return "\n".join(items)


def page(title, body, active=""):
    log.debug("layout.page title=%r active=%r", title, active)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{url('/static/style.css')}">
</head>
<body data-base="{html.escape(config.BASE_PATH)}">
<div class="border" aria-hidden="true"></div>
<header class="site-header">
<div class="brand">
<a class="site-title" href="{url('/')}" lang="mk">{html.escape(config.SITE_TITLE)}</a>
<span class="tagline">{html.escape(config.SITE_TAGLINE)}</span>
</div>
<nav class="site-nav">
{_nav(active)}
</nav>
</header>
<main>
{body}
</main>
<div class="border" aria-hidden="true"></div>
<script src="{url('/static/progress.js')}" defer></script>
<script src="{url('/static/app.js')}" defer></script>
<script src="{url('/static/feedback.js')}" defer></script>
</body>
</html>
"""
