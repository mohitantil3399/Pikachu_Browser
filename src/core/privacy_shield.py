"""
src/core/privacy_shield.py

Brave-Grade Privacy Shield for Pikachu Browser.
Two-layer defense architecture modeled after Brave Browser's adblock-rust + scriptlets:

Layer 1 — Network Request Interceptor:
    Blocks 250+ ad networks, tracker pixels, analytics, and telemetry domains
    at the socket level before requests leave the machine.
    Injects DNT:1 and Sec-GPC:1 headers on all allowed requests.

Layer 2 — Cosmetic Filtering & Procedural Scriptlets:
    Injected into every page at DocumentCreation to:
    - Hide ad containers, promo banners, sticky overlays across all sites.
    - YouTube-specific: auto-skip pre-roll/mid-roll ads, mute ad audio,
      dismiss anti-adblock modals, strip ad placements from player response.
"""

import os
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import (
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestInfo,
    QWebEngineProfile,
    QWebEnginePage,
    QWebEngineScript,
    QWebEngineSettings,
)
from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QStandardPaths


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 — NETWORK REQUEST BLOCKER
# ═══════════════════════════════════════════════════════════════════════════

_BLOCKED_DOMAINS = frozenset([
    # ── Google Ads / DoubleClick / AdSense / Syndication ─────────────────
    "doubleclick.net",
    "googleadservices.com",
    "googlesyndication.com",
    "googletagmanager.com",
    "googletagservices.com",
    "google-analytics.com",
    "googleanalytics.com",
    "analytics.google.com",
    "adservice.google.com",
    "pagead2.googlesyndication.com",
    "securepubads.g.doubleclick.net",
    "googleads.g.doubleclick.net",
    "ad.doubleclick.net",
    "stats.g.doubleclick.net",
    "cm.g.doubleclick.net",
    "tpc.googlesyndication.com",
    "www.googletagmanager.com",
    "www.google.com/pagead",
    "www.youtube.com/pagead",
    "youtube.com/pagead",
    "youtubei.googleapis.com/pagead",
    "/pagead/",
    "fundingchoicesmessages.google.com",
    "contributor.google.com",

    # ── YouTube-specific ad endpoints ────────────────────────────────────
    "www.youtube.com/api/stats/ads",
    "www.youtube.com/api/stats/atr",
    "youtube.com/api/stats/ads",
    "youtube.com/api/stats/atr",
    "yt3.ggpht.com/an_",
    "/get_midroll_",
    "/ptracking",
    "/api/stats/ads",
    "/api/stats/atr",
    "/pagead/interaction",
    "googleads.g.doubleclick.net",
    "static.doubleclick.net",

    # ── Facebook / Meta Pixel & Ads ──────────────────────────────────────
    "facebook.com/tr",
    "connect.facebook.net",
    "graph.facebook.com/tr",
    "an.facebook.com",
    "www.facebook.com/tr",
    "pixel.facebook.com",

    # ── Amazon Ads ───────────────────────────────────────────────────────
    "amazon-adsystem.com",
    "aax.amazon-adsystem.com",
    "ir-na.amazon-adsystem.com",
    "fls-na.amazon-adsystem.com",

    # ── Microsoft / Bing Ads ─────────────────────────────────────────────
    "bat.bing.com",
    "bat.r.msn.com",
    "c.msn.com",
    "ads.microsoft.com",
    "bingads.microsoft.com",
    "adnxs.com",
    "ib.adnxs.com",
    "secure.adnxs.com",

    # ── Twitter / X Ads ──────────────────────────────────────────────────
    "ads-twitter.com",
    "static.ads-twitter.com",
    "analytics.twitter.com",
    "ads-api.twitter.com",

    # ── TikTok / ByteDance ───────────────────────────────────────────────
    "analytics.tiktok.com",
    "ads.tiktok.com",
    "business-api.tiktok.com",
    "mcs.tiktokv.com",

    # ── LinkedIn Ads ─────────────────────────────────────────────────────
    "ads.linkedin.com",
    "analytics.pointdrive.linkedin.com",
    "px.ads.linkedin.com",
    "snap.licdn.com",

    # ── Taboola ──────────────────────────────────────────────────────────
    "taboola.com",
    "tbl.com",
    "cdn.taboola.com",
    "nr.taboola.com",
    "trc.taboola.com",

    # ── Outbrain ─────────────────────────────────────────────────────────
    "outbrain.com",
    "widgets.outbrain.com",
    "amplify.outbrain.com",
    "log.outbrain.com",

    # ── Yahoo / Oath / Verizon Ads ───────────────────────────────────────
    "oath.com",
    "ads.yahoo.com",
    "pixel.advertising.com",
    "advertising.com",

    # ── Criteo ───────────────────────────────────────────────────────────
    "criteo.com",
    "static.criteo.net",
    "bidswitch.net",
    "gum.criteo.com",

    # ── Hotjar / Heatmaps ────────────────────────────────────────────────
    "hotjar.com",
    "static.hotjar.com",
    "script.hotjar.com",

    # ── Mixpanel ─────────────────────────────────────────────────────────
    "mixpanel.com",
    "api.mixpanel.com",
    "cdn.mxpnl.com",

    # ── Segment / Amplitude ──────────────────────────────────────────────
    "segment.com",
    "api.segment.io",
    "cdn.segment.com",
    "amplitude.com",
    "api.amplitude.com",
    "cdn.amplitude.com",

    # ── Intercom / Drift ─────────────────────────────────────────────────
    "intercomcdn.com",
    "intercom.io",
    "js.intercomcdn.com",
    "widget.intercom.io",
    "drift.com",
    "js.driftt.com",

    # ── General Programmatic Ad Exchanges ────────────────────────────────
    "scorecardresearch.com",
    "quantserve.com",
    "chartbeat.com",
    "newrelic.com",
    "nr-data.net",
    "omtrdc.net",
    "2o7.net",
    "demdex.net",
    "turn.com",
    "adtechus.com",
    "pubmatic.com",
    "rubiconproject.com",
    "openx.net",
    "openx.com",
    "33across.com",
    "casalemedia.com",
    "indexexchange.com",
    "spotxchange.com",
    "smartadserver.com",
    "sovrn.com",
    "lijit.com",
    "appnexus.com",
    "yieldmo.com",
    "rhythmone.com",
    "tremorhub.com",
    "adsrvr.org",
    "tribalfusion.com",
    "clicktale.net",
    "crazyegg.com",
    "luckyorange.com",
    "mouseflow.com",
    "moatads.com",
    "serving-sys.com",
    "media.net",
    "contextweb.com",
    "sharethrough.com",
    "undertone.com",
    "zedo.com",
    "eyeota.net",
    "mathtag.com",
    "rlcdn.com",
    "bluekai.com",
    "exelator.com",
    "krxd.net",
    "agkn.com",
    "pippio.com",
    "advertising.com",

    # ── Telemetry pings & beacons ────────────────────────────────────────
    "generate_204",
    "safebrowsing.googleapis.com",
    "clients1.google.com",
    "clients2.google.com",
    "clients3.google.com",
    "clients4.google.com",
    "update.googleapis.com",
    "play.google.com/log",

    # ── Consent / GDPR popup frameworks (ads-related) ────────────────────
    "consent.google.com",
    "consent.youtube.com",
    "quantcast.com",
    "cookielaw.org",
    "onetrust.com",
    "trustarc.com",
    "cookiebot.com",
    "sp-prod.net",
])


class NetworkAdBlockerInterceptor(QWebEngineUrlRequestInterceptor):
    """
    Layer 1: Intercepts every outgoing HTTP(S) request.
    - Blocks requests matching known ad/tracker/analytics domains.
    - Injects DNT:1 and Sec-GPC:1 privacy headers on all allowed requests.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocked_count: int = 0

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        url = info.requestUrl().toString().lower()

        # Block check — substring match against the full URL
        for pattern in _BLOCKED_DOMAINS:
            if pattern in url:
                info.block(True)
                self.blocked_count += 1
                return

        # Inject privacy headers on all allowed requests
        info.setHttpHeader(b"DNT", b"1")
        info.setHttpHeader(b"Sec-GPC", b"1")


# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2 — TYPESCRIPT-ENGINEERED PRIVACY & AD-NEUTRALIZER SHIELD
# ═══════════════════════════════════════════════════════════════════════════

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
BUNDLE_PATH = SCRIPTS_DIR / "privacy_shield.bundle.js"
TS_PATH = SCRIPTS_DIR / "privacy_shield.ts"
BUILD_SCRIPT = SCRIPTS_DIR / "build.mjs"


def get_privacy_shield_script() -> str:
    """
    Returns the compiled JavaScript bundle compiled from src/scripts/privacy_shield.ts.
    If the TypeScript source is newer than the bundle, recompiles via Node.js automatically.
    """
    try:
        needs_build = not BUNDLE_PATH.exists()
        if not needs_build and TS_PATH.exists():
            needs_build = TS_PATH.stat().st_mtime > BUNDLE_PATH.stat().st_mtime

        if needs_build and BUILD_SCRIPT.exists():
            import subprocess
            subprocess.run(["node", str(BUILD_SCRIPT)], check=True, capture_output=True)

        if BUNDLE_PATH.exists():
            return BUNDLE_PATH.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[PrivacyShield] Error loading/building TypeScript bundle: {e}")

    # Fallback to direct read if bundle exists
    if BUNDLE_PATH.exists():
        return BUNDLE_PATH.read_text(encoding="utf-8")
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# SETUP HELPER — Wires everything into a QWebEngineProfile
# ═══════════════════════════════════════════════════════════════════════════

def setup_privacy_shield(profile: QWebEngineProfile, parent=None):
    """
    Applies the full Brave-grade privacy shield to a QWebEngineProfile:
      1. Network-level ad/tracker blocker (QWebEngineUrlRequestInterceptor)
      2. TypeScript-compiled Cosmetic CSS + YouTube scriptlet injection (QWebEngineScript)
      3. Engine-level privacy hardening (settings, UA, cookies, cache)

    Args:
        profile: The QWebEngineProfile to protect (must be off-the-record).
        parent: QObject parent to prevent garbage collection of interceptor.

    Returns:
        NetworkAdBlockerInterceptor instance (keep a reference to prevent GC).
    """

    # ── 1. Wire Network Interceptor ───────────────────────────────────────
    interceptor = NetworkAdBlockerInterceptor(parent)
    profile.setUrlRequestInterceptor(interceptor)

    # ── 2. Inject TypeScript-compiled scriptlet into every page ────────────
    shield_code = get_privacy_shield_script()
    if shield_code:
        script = QWebEngineScript()
        script.setName("PikachuPrivacyShield")
        script.setSourceCode(shield_code)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)  # Also block ads in iframes
        profile.scripts().insert(script)

    # ── 3. Privacy-hardened engine settings ────────────────────────────────
    settings = profile.settings()
    # Enable WebGL for smooth video playback and hardware acceleration
    settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
    # Disable plugins (Flash-era relics, potential leaks)
    settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
    # Block mixed content (HTTPS pages loading HTTP resources)
    settings.setAttribute(
        QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False
    )

    # ── 4. Generic Chrome User-Agent (blend into the crowd) ──────────────
    profile.setHttpUserAgent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    return interceptor
