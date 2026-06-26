"""
Background "Stats for Nerds" logger for video-streaming sessions.

Supported platforms:
  * YouTube - reads the player object directly via `movie_player.getStatsForNerds()`
    (the same data behind the right-click "Stats for Nerds" overlay), merged with
    the raw <video> element.
  * Twitch - has no public "Stats for Nerds" API, so we read the standard
    HTMLVideoElement API (resolution, dropped/total frames, buffer-ahead,
    playback state) plus the channel name from the URL.

A daemon thread samples on a fixed interval and appends one JSON object per sample
to a JSONL file, so the log survives even if the session crashes before `stop()`
is called.

Note on thread-safety: Selenium drivers are not strictly thread-safe. We sample
from a background thread while the main state-machine loop also touches the
driver, so every sample is wrapped in try/except - a transient collision skips a
single sample rather than crashing the run. Sampling every couple of seconds
against a loop that mostly sleeps makes collisions rare in practice.
"""

import json
import logging
import threading
import time

logger = logging.getLogger(__name__)


# Runs in the page. Detects the platform by hostname and returns a normalized
# stats object. Returns {"platform": "unknown", "error": ...} if no player/video
# is present. Field names mirror each platform's native terminology where useful.
_STATS_JS = r"""
const host = location.hostname || '';

function youtubeStats() {
    const player = document.getElementById('movie_player')
        || document.querySelector('.html5-video-player');
    const video = document.querySelector('video');
    if (!player && !video) { return {platform: 'youtube', error: 'no_player'}; }

    const out = {platform: 'youtube'};
    try {
        if (player && typeof player.getStatsForNerds === 'function') {
            Object.assign(out, player.getStatsForNerds());
        }
    } catch (e) { out.stats_for_nerds_error = String(e); }

    try {
        if (player && typeof player.getVideoData === 'function') {
            const d = player.getVideoData();
            out.video_id = d && d.video_id;
            out.title = d && d.title;
            out.author = d && d.author;
            out.is_live = d && d.isLive;
        }
        if (player && typeof player.getCurrentTime === 'function') {
            out.current_time_secs = player.getCurrentTime();
        }
        if (player && typeof player.getDuration === 'function') {
            out.duration_secs = player.getDuration();
        }
        if (player && typeof player.getVideoLoadedFraction === 'function') {
            out.loaded_fraction = player.getVideoLoadedFraction();
        }
        if (player && typeof player.getPlayerState === 'function') {
            out.player_state = player.getPlayerState();
        }
    } catch (e) { out.player_data_error = String(e); }

    addVideoElementStats(out, video);
    return out;
}

function twitchStats() {
    const video = document.querySelector('video');
    if (!video) { return {platform: 'twitch', error: 'no_video'}; }

    const out = {platform: 'twitch'};
    try {
        // Channel name from the first non-empty path segment (e.g. /channelname).
        const seg = location.pathname.split('/').filter(Boolean);
        out.channel = seg.length ? seg[0] : null;
        out.is_live = true; // Twitch watch pages are live unless it's a VOD (/videos/).
        if (location.pathname.startsWith('/videos/')) {
            out.is_live = false;
            out.video_id = seg.length > 1 ? seg[1] : null;
        }
    } catch (e) { out.page_data_error = String(e); }

    addVideoElementStats(out, video);
    return out;
}

function addVideoElementStats(out, video) {
    try {
        if (!video) { return; }
        out.video_width = video.videoWidth;
        out.video_height = video.videoHeight;
        out.resolution = video.videoWidth + 'x' + video.videoHeight;
        out.playback_rate = video.playbackRate;
        out.paused = video.paused;
        out.muted = video.muted;
        out.volume = video.volume;
        out.current_time_secs = out.current_time_secs != null
            ? out.current_time_secs : video.currentTime;
        // Buffer-ahead: how many seconds are buffered past the current position.
        if (video.buffered && video.buffered.length) {
            const end = video.buffered.end(video.buffered.length - 1);
            out.buffer_ahead_secs = Math.max(0, end - video.currentTime);
        }
        if (typeof video.getVideoPlaybackQuality === 'function') {
            const q = video.getVideoPlaybackQuality();
            out.dropped_video_frames = q.droppedVideoFrames;
            out.total_video_frames = q.totalVideoFrames;
            if ('corruptedVideoFrames' in q) {
                out.corrupted_video_frames = q.corruptedVideoFrames;
            }
        }
    } catch (e) { out.video_element_error = String(e); }
}

if (host.indexOf('youtube.com') !== -1 || host.indexOf('youtu.be') !== -1) {
    return youtubeStats();
}
if (host.indexOf('twitch.tv') !== -1) {
    return twitchStats();
}
// Fallback: try whatever <video> is on the page.
const video = document.querySelector('video');
if (!video) { return {platform: 'unknown', error: 'no_video'}; }
const out = {platform: 'unknown'};
addVideoElementStats(out, video);
return out;
"""


class VideoStatsLogger:
    """Samples video-player stats on a background thread into a JSONL file.

    Site-aware: works on YouTube ("Stats for Nerds") and Twitch (HTMLVideoElement
    metrics). The platform is detected per-sample from the page, so a single
    logger handles a session that navigates between sites.
    """

    def __init__(self, driver, out_path: str = "netgent_video_stats.jsonl",
                 interval: float = 2.0):
        self.driver = driver
        self.out_path = out_path
        self.interval = interval
        self._thread = None
        self._stop_event = threading.Event()

    def configure(self, out_path: str = None, interval: float = None):
        """Update output path / interval before starting."""
        if out_path is not None:
            self.out_path = out_path
        if interval is not None:
            self.interval = interval

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def sample(self) -> dict:
        """Capture a single stats snapshot (stamped with time and URL)."""
        sample = {"timestamp": time.time()}
        try:
            sample["url"] = self.driver.current_url
        except Exception:
            sample["url"] = None
        try:
            stats = self.driver.execute_script(_STATS_JS)
            sample["stats"] = stats
        except Exception as e:
            sample["stats"] = None
            sample["sample_error"] = str(e)
        return sample

    def _run(self):
        # Line-buffered append so each sample is flushed to disk immediately.
        with open(self.out_path, "a", buffering=1) as f:
            while not self._stop_event.is_set():
                sample = self.sample()
                try:
                    f.write(json.dumps(sample) + "\n")
                except Exception as e:
                    logger.warning(f"Failed to write stats sample: {e}")
                # Wait the interval, but wake immediately on stop().
                self._stop_event.wait(self.interval)

    def start(self):
        if self.is_running():
            logger.info("Stats logger already running; ignoring start()")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="video-stats-logger")
        self._thread.start()
        logger.info(f"Video stats logging started -> {self.out_path} "
                    f"(every {self.interval}s)")

    def stop(self):
        if not self.is_running():
            return
        self._stop_event.set()
        self._thread.join(timeout=self.interval + 5)
        logger.info(f"Video stats logging stopped -> {self.out_path}")
        self._thread = None


# Backwards-compatible alias (the logger now covers Twitch as well as YouTube).
YouTubeStatsLogger = VideoStatsLogger
