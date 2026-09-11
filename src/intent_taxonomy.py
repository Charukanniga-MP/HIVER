"""
Intent Taxonomy Module for SpotifyCares AI Support System.
Defines 6 core intent categories, keyword signals, inclusion/exclusion rules, and classification rules.
Provides enhanced intent classification with confidence scoring, security overrides, and reasoning.
Optimized with pre-compiled regexes for maximum performance over large corpora.
"""

import re

INTENT_TAXONOMY = {
    "playback_audio_issue": {
        "name": "Playback & Audio Issue",
        "description": "App freezing, playback pausing randomly, shuffle/repeat button stuck, audio stuttering or no sound.",
        "inclusion": "Mentions shuffle, repeat, pausing, stop playing, no sound, freezing, app crash during playback, songs stopping.",
        "exclusion": "Downloads not completing offline, billing or subscription renewal complaints.",
        "keywords": [
            "shuffle", "repeat", "pause", "pausing", "stop playing", "sound", "volume", "stutter", "lag", "crash", 
            "freeze", "freezing", "skip", "skipping", "song stops", "audio", "songs keep stopping", "music keeps stopping",
            "songs stopping", "music stops", "playback stops", "stops after a few seconds", "stops midway", 
            "audio cuts out", "playback interrupted", "keeps stopping", "stopping after", "stops after", "stops playing",
            "cannot listen", "can't listen", "stopping"
        ]
    },

    "offline_sync_issue": {
        "name": "Offline Mode & Sync Issue",
        "description": "Tracks not downloading for offline listen, offline mode toggle greyed out, SD card storage errors.",
        "inclusion": "Mentions offline mode, download failed, downloading, local storage, SD card, sync playlists offline.",
        "exclusion": "Online streaming audio quality or account login failures.",
        "keywords": ["offline", "download", "downloading", "downloads", "sync", "storage", "sd card", "downloaded", "cant listen offline", "offline mode"]
    },
    "billing_subscription_dispute": {
        "name": "Billing & Subscription Dispute",
        "description": "Unrecognized charges, double billing, Student discount verification failure, Premium cancellation.",
        "inclusion": "Mentions charge, charged, refund, payment, credit card, student discount, premium price, receipt, subscription.",
        "exclusion": "Technical playback bugs or password reset requests.",
        "keywords": ["billing", "charge", "charged", "refund", "payment", "subscription", "premium", "student", "discount", "receipt", "card", "money", "overcharged", "cancel subscription", "bank", "invoice"]
    },
    "account_access_security": {
        "name": "Account Access & Security",
        "description": "Forgotten password, account hacked/breached, email address changes, unauthorized login attempts.",
        "inclusion": "Mentions login, sign in, password, hacked, breach, unauthorized, email change, account locked.",
        "exclusion": "General app crashes or playlist modification issues.",
        "keywords": ["account", "login", "log in", "password", "hacked", "hacker", "stolen", "breach", "security", "email", "reset password", "cant sign in", "unauthorized", "compromised", "takeover"]
    },
    "playlist_library_management": {
        "name": "Playlist & Library Management",
        "description": "Missing saved tracks, deleted playlists, local audio file import failure, Daily Mix / Wrapped issues.",
        "inclusion": "Mentions playlist, saved songs, library, liked songs, daily mix, wrapped, local files, queue.",
        "exclusion": "Offline download storage failures or billing disputes.",
        "keywords": ["playlist", "playlists", "library", "saved", "liked songs", "daily mix", "wrapped", "queue", "local files", "deleted playlist", "missing songs"]
    },
    "general_feedback_inquiry": {
        "name": "General Inquiry & Feedback",
        "description": "UI redesign feedback, feature requests, lyrics availability inquiries, general questions.",
        "inclusion": "Mentions feature request, update, UI, lyrics, podcast request, general questions without a bug.",
        "exclusion": "Specific technical bugs, billing complaints, or account security issues.",
        "keywords": ["feature", "request", "update", "lyrics", "ui", "interface", "podcast", "suggestion", "feedback", "love spotify", "hate update", "question"]
    }
}

SECURITY_OVERRIDE_TERMS = [
    "hacked", "hacker", "stolen account", "account hacked", "unauthorized access",
    "someone changed my", "someone logged into", "compromised account", "takeover"
]

# Pre-compile regexes for fast execution
COMPILED_KEYWORDS = {}
for intent, meta in INTENT_TAXONOMY.items():
    compiled_list = []
    for kw in meta["keywords"]:
        if " " in kw:
            compiled_list.append((kw, 3.0, False))
        else:
            pattern = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            compiled_list.append((pattern, 1.5, True))
    COMPILED_KEYWORDS[intent] = compiled_list

OFFLINE_PATTERN = re.compile(r'\b(offline|download|downloading|downloads)\b', re.IGNORECASE)
BILLING_PATTERN = re.compile(r'\b(charge|charged|refund|billing|invoice|payment|subscription)\b', re.IGNORECASE)
ACCOUNT_PATTERN = re.compile(r'\b(login|log in|password|sign in|email|reset)\b', re.IGNORECASE)
PLAYBACK_PATTERN = re.compile(r'\b(stopping|stuck|freezing|stuttering|pausing|cuts out)\b|stops (midway|playing|after|playback)', re.IGNORECASE)

def classify_intent(text: str) -> dict:
    """
    Classify customer message into one of 6 intents using multi-layered heuristic signal matching.
    Fast pre-compiled execution.
    Returns dict: {"intent": str, "confidence": float, "reason": str}
    """
    text_clean = text.strip()
    text_lower = text_clean.lower()

    if not text_clean:
        return {
            "intent": "general_feedback_inquiry",
            "confidence": 0.30,
            "reason": "Empty customer query text."
        }

    # 1. High-Priority Security Override
    for sec_term in SECURITY_OVERRIDE_TERMS:
        if sec_term in text_lower:
            return {
                "intent": "account_access_security",
                "confidence": 0.95,
                "reason": f"Explicit account security / takeover keyword detected ('{sec_term}')."
            }

    # 2. Fast Pre-compiled Keyword Scoring
    scores = {intent: 0.0 for intent in INTENT_TAXONOMY}

    for intent, compiled_list in COMPILED_KEYWORDS.items():
        for item, weight, is_regex in compiled_list:
            if is_regex:
                if item.search(text_lower):
                    scores[intent] += weight
            else:
                if item in text_lower:
                    scores[intent] += weight

    # Contextual boosts
    if OFFLINE_PATTERN.search(text_lower):
        scores["offline_sync_issue"] += 2.0
    if BILLING_PATTERN.search(text_lower):
        scores["billing_subscription_dispute"] += 2.0
    if ACCOUNT_PATTERN.search(text_lower):
        scores["account_access_security"] += 2.0
    if PLAYBACK_PATTERN.search(text_lower):
        scores["playback_audio_issue"] += 2.0

    max_score = max(scores.values())
    total_score = sum(scores.values())

    if max_score == 0:
        words = text_clean.split()
        reason = "Short ambiguous message without specific intent signals." if len(words) <= 3 else "General inquiry/feedback with no specific bug or billing keywords detected."
        return {
            "intent": "general_feedback_inquiry",
            "confidence": 0.45,
            "reason": reason
        }

    best_intent = max(scores, key=scores.get)
    confidence = min(0.95, 0.55 + (max_score / (total_score + 1.0)) * 0.40)
    intent_display = INTENT_TAXONOMY[best_intent]["name"]
    reason = f"Matched key terms for {intent_display} (raw score {max_score:.1f})."

    return {
        "intent": best_intent,
        "confidence": round(float(confidence), 2),
        "reason": reason
    }

def classify_intent_rule_based(text: str) -> tuple[str, float]:
    """
    Backwards-compatible wrapper returning (intent, confidence).
    """
    res = classify_intent(text)
    return res["intent"], res["confidence"]

