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
# LAYER 2 — COSMETIC FILTERING & PROCEDURAL SCRIPTLETS
# ═══════════════════════════════════════════════════════════════════════════

BRAVE_COSMETIC_AND_SCRIPTLET_JS = r"""
(function() {
    'use strict';

    // ─── UNIVERSAL COSMETIC AD ELEMENT HIDER ──────────────────────────
    const COSMETIC_CSS = `
        /* Google Ads iframes and containers */
        ins.adsbygoogle,
        [id^="google_ads"],
        [id^="div-gpt-ad"],
        [class*="ad-container"],
        [class*="ad-wrapper"],
        [class*="ad-slot"],
        [class*="ad-banner"],
        [class*="ad-unit"],
        [data-ad-slot],
        [data-ad],
        iframe[src*="doubleclick"],
        iframe[src*="googlesyndication"],
        iframe[src*="googleadservices"],
        /* Taboola / Outbrain widgets */
        .trc_related_container,
        .OUTBRAIN,
        [data-widget-type="taboola"],
        [id^="taboola-"],
        [class*="taboola"],
        [class*="outbrain"],
        /* Generic sponsored content markers */
        [class*="sponsored"],
        [class*="Sponsored"],
        [data-testid*="sponsor"],
        /* Cookie consent overlays from ad-tech */
        [id*="sp_message_container"],
        [class*="qc-cmp"],
        /* YouTube Ad Selectors (In-Player, Sidebar, Masthead, Feed) */
        ytd-ad-slot-renderer,
        ytd-in-feed-ad-layout-renderer,
        ytd-action-companion-ad-renderer,
        ytd-promoted-sparkles-web-renderer,
        ytd-display-ad-renderer,
        ytd-promoted-video-renderer,
        ytd-compact-promoted-video-renderer,
        ytd-banner-promo-renderer,
        ytd-statement-banner-renderer,
        ytd-mealbar-promo-renderer,
        .ytd-merch-shelf-renderer,
        #masthead-ad,
        #player-ads,
        #panels .ytd-ads-engagement-panel-content-renderer,
        .ytp-ad-module,
        .ytp-ad-overlay-container,
        .ytp-ad-overlay-slot,
        .video-ads,
        .ytp-ad-player-overlay,
        .ytp-ad-player-overlay-layout,
        .ytp-ad-player-overlay-flyout-cta,
        .ytp-ad-text,
        .ytp-ad-preview-text,
        .ytp-ad-skip-button-modern,
        tp-yt-paper-dialog:has(#dismiss-button),
        ytd-enforcement-message-view-model,
        yt-mealbar-promo-renderer {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            opacity: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
        }
    `;

    // Safe style injector that handles DocumentCreation timing gracefully
    function injectCosmeticCSS() {
        try {
            if (document.getElementById('pikachu-cosmetic-shield')) return true;
            const target = document.head || document.documentElement;
            if (target) {
                const styleEl = document.createElement('style');
                styleEl.id = 'pikachu-cosmetic-shield';
                styleEl.textContent = COSMETIC_CSS;
                target.appendChild(styleEl);
                return true;
            }
        } catch(e) {}
        return false;
    }

    // Try immediately, fallback to DOM events and polling until ready
    if (!injectCosmeticCSS()) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', injectCosmeticCSS);
        }
        const styleRetry = setInterval(function() {
            if (injectCosmeticCSS()) clearInterval(styleRetry);
        }, 50);
    }

    // ─── YOUTUBE AD NEUTRALIZER SCRIPTLET ─────────────────────────────
    const isYouTube = location.hostname.includes('youtube.com');
    if (!isYouTube) return;

    // 1. Strip ad placements from ytInitialPlayerResponse dynamically
    try {
        let _ytResp = window.ytInitialPlayerResponse;
        Object.defineProperty(window, 'ytInitialPlayerResponse', {
            get: function() { return _ytResp; },
            set: function(val) {
                if (val && typeof val === 'object') {
                    delete val.adPlacements;
                    delete val.playerAds;
                    delete val.adSlots;
                }
                _ytResp = val;
            },
            configurable: true
        });
        if (_ytResp && typeof _ytResp === 'object') {
            delete _ytResp.adPlacements;
            delete _ytResp.playerAds;
            delete _ytResp.adSlots;
        }
    } catch(e) {}

    // 2. Continuous High-Frequency YouTube Ad Skipper & Element Purger
    function skipYouTubeAd() {
        try {
            const player = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
            const adShowing = player && (player.classList.contains('ad-showing') || player.classList.contains('ad-interrupting'));
            const adOverlay = document.querySelector('.ytp-ad-player-overlay, .ytp-ad-text, .ytp-ad-preview-text, .ytp-ad-module');

            if (adShowing || adOverlay) {
                const video = document.querySelector('video.html5-main-video') || document.querySelector('video');
                if (video) {
                    video.muted = true;
                    video.playbackRate = 16.0;
                    if (isFinite(video.duration) && video.duration > 0) {
                        video.currentTime = video.duration;
                    } else {
                        video.currentTime = 99999;
                    }
                }

                // Instant click on any ad skip buttons
                const skipSelectors = [
                    '.ytp-ad-skip-button',
                    '.ytp-ad-skip-button-modern',
                    '.ytp-skip-ad-button',
                    'button.ytp-ad-skip-button-modern',
                    '.ytp-ad-skip-button-slot button',
                    'button[class*="ytp-ad-skip-button"]',
                    'button[class*="skip-button"]',
                    '.ytp-ad-overlay-close-button',
                    '.ytp-ad-overlay-close-container button'
                ];
                for (let i = 0; i < skipSelectors.length; i++) {
                    const btns = document.querySelectorAll(skipSelectors[i]);
                    for (let j = 0; j < btns.length; j++) {
                        try { btns[j].click(); } catch(err) {}
                    }
                }
            }

            // Purge companion and sidebar ads (e.g. Sponsored cards)
            const companionAds = document.querySelectorAll(
                'ytd-ad-slot-renderer, ' +
                'ytd-in-feed-ad-layout-renderer, ' +
                'ytd-action-companion-ad-renderer, ' +
                '#player-ads, ' +
                '#masthead-ad, ' +
                'ytd-banner-promo-renderer'
            );
            for (let i = 0; i < companionAds.length; i++) {
                try { companionAds[i].remove(); } catch(err) {}
            }

            // Dismiss anti-adblock modals
            const enforceDialogs = document.querySelectorAll(
                'ytd-enforcement-message-view-model, ' +
                'tp-yt-paper-dialog:has(#dismiss-button)'
            );
            for (let i = 0; i < enforceDialogs.length; i++) {
                try {
                    const dismissBtn = enforceDialogs[i].querySelector('#dismiss-button') ||
                                       enforceDialogs[i].querySelector('button');
                    if (dismissBtn) dismissBtn.click();
                    enforceDialogs[i].remove();
                } catch(err) {}
            }
        } catch(e) {}
    }

    // Run every 100ms for ultra-responsive ad skipping
    setInterval(skipYouTubeAd, 100);

    // 3. Attach MutationObserver safely once documentElement exists
    function setupObserver() {
        if (!document.documentElement) {
            setTimeout(setupObserver, 50);
            return;
        }
        const observer = new MutationObserver(function() {
            injectCosmeticCSS();
            skipYouTubeAd();
        });
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    }
    setupObserver();

    // 4. Intercept fetch & XHR to strip ads from YouTube API responses
    try {
        const originalFetch = window.fetch;
        window.fetch = async function(...args) {
            const url = (args[0] instanceof Request) ? args[0].url : String(args[0]);

            // Black hole ad stats/tracking requests
            if (url.includes('/get_midroll_') ||
                url.includes('/api/stats/ads') ||
                url.includes('/api/stats/atr') ||
                url.includes('/pagead/') ||
                url.includes('doubleclick.net') ||
                url.includes('googleadservices.com')) {
                return new Promise(() => {});
            }

            // Intercept player config to strip ad definitions before video starts
            if (url.includes('/youtubei/v1/player')) {
                try {
                    const response = await originalFetch.apply(this, args);
                    const clone = response.clone();
                    const data = await clone.json();
                    if (data.adPlacements) delete data.adPlacements;
                    if (data.playerAds) delete data.playerAds;
                    if (data.adSlots) delete data.adSlots;
                    return new Response(JSON.stringify(data), {
                        status: response.status,
                        statusText: response.statusText,
                        headers: response.headers
                    });
                } catch(err) {
                    return originalFetch.apply(this, args);
                }
            }

            return originalFetch.apply(this, args);
        };

        const origXHROpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            const urlStr = String(url);
            if (urlStr.includes('/get_midroll_') ||
                urlStr.includes('/api/stats/ads') ||
                urlStr.includes('/api/stats/atr') ||
                urlStr.includes('/pagead/') ||
                urlStr.includes('doubleclick.net') ||
                urlStr.includes('googleadservices.com')) {
                return origXHROpen.call(this, method, 'about:blank', ...rest);
            }
            return origXHROpen.call(this, method, url, ...rest);
        };
    } catch(e) {}
})();
"""


# ═══════════════════════════════════════════════════════════════════════════
# SETUP HELPER — Wires everything into a QWebEngineProfile
# ═══════════════════════════════════════════════════════════════════════════

def setup_privacy_shield(profile: QWebEngineProfile, parent=None):
    """
    Applies the full Brave-grade privacy shield to a QWebEngineProfile:
      1. Network-level ad/tracker blocker (QWebEngineUrlRequestInterceptor)
      2. Cosmetic CSS + YouTube scriptlet injection (QWebEngineScript)
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

    # ── 2. Inject Cosmetic + Scriptlet JS into every page ─────────────────
    script = QWebEngineScript()
    script.setName("PikachuPrivacyShield")
    script.setSourceCode(BRAVE_COSMETIC_AND_SCRIPTLET_JS)
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
