"""The "Wrong or missing video? Tell us" box on each song page."""
import html
import logging

log = logging.getLogger("site.feedback")

SUMMARY = "Wrong or missing video? Tell us"
SUBMIT_URL = "https://api.web3forms.com/submit"


def _e(text):
    return html.escape(text or "", quote=True)


def render_feedback_form(song_id, title, form_key):
    """Plain-language form. With no form key it only says the form is coming soon."""
    log.debug("feedback form song=%s key_set=%s", song_id, bool(form_key))
    if not form_key:
        return (
            '<details class="feedback">'
            f"<summary>{SUMMARY}</summary>"
            "<p>Feedback form coming soon.</p>"
            "</details>"
        )
    subject = f"Feedback for song {song_id}: {title}"
    return f"""<details class="feedback" data-feedback>
<summary>{SUMMARY}</summary>
<p>Thank you for helping! It takes about a minute. You can also tell us about a mistake in the words.</p>
<p><label>What is this about?<br>
<select name="kind" data-kind>
<option value="video" selected>The video is wrong or missing</option>
<option value="words">A mistake in the words or the English</option>
<option value="other">Something else</option>
</select></label></p>
<p>For a video, do this:</p>
<ol class="steps">
<li>Open YouTube and find this song.</li>
<li>Copy the web address from the top of the page.</li>
<li>Paste it here and press Send.</li>
</ol>
<details class="how-to-copy"><summary>How do I copy the web address?</summary>
<p>On a phone: tap the Share button under the video, then tap Copy link.</p>
<p>On a computer: click the address bar at the top of the browser, then hold Ctrl and press C. On a Mac, hold Command and press C.</p>
</details>
<form action="{SUBMIT_URL}" method="POST" data-feedback-form>
<input type="hidden" name="access_key" value="{_e(form_key)}">
<input type="hidden" name="subject" value="{_e(subject)}">
<input type="hidden" name="song_id" value="{song_id}">
<div class="botcheck" aria-hidden="true"><input type="checkbox" name="botcheck" tabindex="-1" autocomplete="off"></div>
<p><label>YouTube link (for a video report)<br><input type="text" name="url" inputmode="url" autocomplete="off" size="40"></label></p>
<p><label>Your note (needed for a words report or something else)<br><textarea name="note" rows="3" cols="40"></textarea></label></p>
<p><button type="submit">Send</button></p>
<p class="feedback-status" role="status" aria-live="polite"></p>
</form>
</details>"""
