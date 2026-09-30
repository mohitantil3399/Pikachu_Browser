/**
 * Pikachu AI Browser — Privacy Shield & Ad Neutralizer Engine
 * Written in strict TypeScript for bulletproof DOM & YouTube player manipulation.
 */

// ─── TYPE DEFINITIONS ────────────────────────────────────────────────────────
                                                    
                            
                    
                       
                       
                          
                     
                              
                           
                              
                       
 

                                 
                           
                        
                      
                                     
                        
                                        
                                         
                                         
                         
                         
      
                           
 

;               
                      
                                                        
                                            
                                            
     
 

// ─── INITIALIZATION GUARD ───────────────────────────────────────────────────
(function initPikachuShield()       {
    'use strict';

    if (window.__PIKACHU_SHIELD_ACTIVE__) {
        return;
    }
    window.__PIKACHU_SHIELD_ACTIVE__ = true;

    console.log('[PikachuShield] TypeScript Shield initialized');

    // ─── 1. UNIVERSAL COSMETIC CSS FILTERING ─────────────────────────────────
    const COSMETIC_STYLES         = `
        /* Google Ads iframes and generic ad slots */
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
        /* Outbrain / Taboola */
        .trc_related_container,
        .OUTBRAIN,
        [data-widget-type="taboola"],
        [id^="taboola-"],
        [class*="taboola"],
        [class*="outbrain"],
        /* Sponsored content indicators */
        [class*="sponsored"],
        [class*="Sponsored"],
        [data-testid*="sponsor"],
        /* Ad-tech privacy modals */
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

    function injectCosmeticCSS()          {
        try {
            if (document.getElementById('pikachu-shield-css')) {
                return true;
            }
            const target                     = document.head || document.documentElement;
            if (target) {
                const styleEl                   = document.createElement('style');
                styleEl.id = 'pikachu-shield-css';
                styleEl.textContent = COSMETIC_STYLES;
                target.appendChild(styleEl);
                return true;
            }
        } catch {
            // Document context not yet ready
        }
        return false;
    }

    if (!injectCosmeticCSS()) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => injectCosmeticCSS());
        }
        const styleInterval         = window.setInterval(() => {
            if (injectCosmeticCSS()) {
                clearInterval(styleInterval);
            }
        }, 50);
    }

    // ─── 2. YOUTUBE AD NEUTRALIZER ENGINE ────────────────────────────────────
    const isYouTube          = location.hostname.includes('youtube.com');
    if (!isYouTube) {
        return;
    }

    // --- Helper: Deep ad property pruner ---
    function deepPruneAds(obj         )       {
        if (!obj || typeof obj !== 'object') return;
        if (Array.isArray(obj)) {
            for (let i = 0; i < obj.length; i++) {
                deepPruneAds(obj[i]);
            }
            return;
        }
        const record = obj                           ;
        if ('adPlacements' in record) delete record.adPlacements;
        if ('playerAds' in record) delete record.playerAds;
        if ('adSlots' in record) delete record.adSlots;
        if ('adBreakHeartbeatParams' in record) delete record.adBreakHeartbeatParams;
        if ('adBreakParams' in record) delete record.adBreakParams;

        if (record.playerResponse && typeof record.playerResponse === 'object') {
            deepPruneAds(record.playerResponse);
        }
    }

    // --- A. Root Payload Pruning: JSON.parse Interceptor ---
    const originalJSONParse = JSON.parse;
    JSON.parse = function(text        , reviver                                              )      {
        const parsed = originalJSONParse.call(this, text, reviver);
        deepPruneAds(parsed);
        return parsed;
    };

    // --- B. ytInitialPlayerResponse Property Descriptor Trap ---
    try {
        let internalPlayerResponse                                    = window.ytInitialPlayerResponse;
        Object.defineProperty(window, 'ytInitialPlayerResponse', {
            get()                                    {
                return internalPlayerResponse;
            },
            set(value                                   )       {
                deepPruneAds(value);
                internalPlayerResponse = value;
            },
            configurable: true
        });

        if (internalPlayerResponse && typeof internalPlayerResponse === 'object') {
            deepPruneAds(internalPlayerResponse);
        }
    } catch {
        // Ignore trap definition failure if already locked
    }

    // --- C. Fetch & XHR Response Body Rewriter ---
    const originalFetch = window.fetch;
    window.fetch = async function(...args                          )                    {
        const input = args[0];
        const urlStr         = (input instanceof Request) ? input.url : String(input);

        // Black-hole ad metrics and telemetry endpoints
        if (urlStr.includes('/api/stats/ads') ||
            urlStr.includes('/api/stats/atr') ||
            urlStr.includes('/get_midroll_') ||
            urlStr.includes('/pagead/') ||
            urlStr.includes('/ptracking') ||
            urlStr.includes('doubleclick.net') ||
            urlStr.includes('googleadservices.com')) {
            return new Promise          (() => {});
        }

        // Intercept player config responses and strip ad fields from payload
        if (urlStr.includes('/youtubei/v1/player')) {
            try {
                const response = await originalFetch.apply(this, args);
                const text = await response.text();
                // Replace ad triggers in raw response text (uBlock trusted-replace method)
                const sanitizedText = text
                    .replace(/"adPlacements"/g, '"no_adPlacements"')
                    .replace(/"playerAds"/g, '"no_playerAds"')
                    .replace(/"adSlots"/g, '"no_adSlots"')
                    .replace(/"adBreakHeartbeatParams"/g, '"no_adBreakHeartbeatParams"');

                return new Response(sanitizedText, {
                    status: response.status,
                    statusText: response.statusText,
                    headers: response.headers
                });
            } catch {
                return originalFetch.apply(this, args);
            }
        }

        return originalFetch.apply(this, args);
    };

    // --- D. High-Frequency Video Ad Skipper & Watchdog ---
    function executeYouTubeAdPurge()       {
        try {
            const player                              =
                document.getElementById('movie_player')                                ||
                document.querySelector('.html5-video-player')                               ;

            const isAdActive          = !!(
                (player && (player.classList.contains('ad-showing') || player.classList.contains('ad-interrupting'))) ||
                (player && typeof player.getAdState === 'function' && player.getAdState() === 1) ||
                document.querySelector('.ytp-ad-player-overlay') ||
                document.querySelector('.ytp-ad-text') ||
                document.querySelector('.ytp-ad-preview-text') ||
                document.querySelector('.ytp-ad-progress')
            );

            if (isAdActive) {
                // 1. Invoke native YouTube player skip method if exposed
                if (player && typeof player.skipAd === 'function') {
                    player.skipAd();
                }

                // 2. Fast-forward and terminate ad video stream
                const video                          =
                    document.querySelector('video.html5-main-video') ||
                    document.querySelector('video');

                if (video) {
                    video.muted = true;
                    video.playbackRate = 16.0;
                    if (isFinite(video.duration) && video.duration > 0) {
                        video.currentTime = video.duration;
                    }
                    // Dispatch ended event to force YouTube state machine transition
                    video.dispatchEvent(new Event('ended'));
                }

                // 3. Immediately click all skip buttons
                const skipButtonSelectors           = [
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

                for (const selector of skipButtonSelectors) {
                    const buttons = document.querySelectorAll             (selector);
                    buttons.forEach(btn => {
                        try {
                            btn.click();
                            btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                        } catch {}
                    });
                }
            }

            // 4. Purge companion ads from DOM tree
            const companionAdSelectors         =
                'ytd-ad-slot-renderer, ' +
                'ytd-in-feed-ad-layout-renderer, ' +
                'ytd-action-companion-ad-renderer, ' +
                '#player-ads, ' +
                '#masthead-ad, ' +
                'ytd-banner-promo-renderer';

            const companionNodes = document.querySelectorAll(companionAdSelectors);
            companionNodes.forEach(node => {
                try { node.remove(); } catch {}
            });

            // 5. Dismiss anti-adblock enforcement dialogs
            const antiAdblockDialogs = document.querySelectorAll(
                'ytd-enforcement-message-view-model, ' +
                'tp-yt-paper-dialog:has(#dismiss-button)'
            );
            antiAdblockDialogs.forEach(dialog => {
                try {
                    const dismissButton                     =
                        dialog.querySelector('#dismiss-button') ||
                        dialog.querySelector('button');
                    if (dismissButton) dismissButton.click();
                    dialog.remove();
                } catch {}
            });
        } catch {
            // Safe execution context
        }
    }

    // Run watchdog every 50ms for instantaneous ad termination
    window.setInterval(executeYouTubeAdPurge, 50);

    // --- E. DOM Mutation Observer for SPA Dynamic Navigations ---
    function attachDOMObserver()       {
        if (!document.documentElement) {
            setTimeout(attachDOMObserver, 30);
            return;
        }

        const observer                   = new MutationObserver(() => {
            injectCosmeticCSS();
            executeYouTubeAdPurge();
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    }

    attachDOMObserver();
})();
