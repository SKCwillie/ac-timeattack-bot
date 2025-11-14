# track_flags.py

# Complete track → country flag table for all Kunos tracks +
# major mod tracks + fictional tracks.

TRACK_FLAGS = {
    # 🇮🇹 Italy
    "monza": "🇮🇹",
    "imola": "🇮🇹",
    "vallelunga": "🇮🇹",
    "mugello": "🇮🇹",
    "magione": "🇮🇹",

    # 🇬🇧 United Kingdom
    "silverstone": "🇬🇧",
    "brands hatch": "🇬🇧",
    "donington park": "🇬🇧",

    # 🇩🇪 Germany
    "nordschleife": "🇩🇪",
    "nurburgring": "🇩🇪",
    "hockenheim": "🇩🇪",

    # 🇺🇸 USA
    "laguna seca": "🇺🇸",
    "road america": "🇺🇸",
    "watkins glen": "🇺🇸",
    "sebring": "🇺🇸",
    "sonoma": "🇺🇸",

    # 🇳🇱 Netherlands
    "zandvoort": "🇳🇱",

    # 🇧🇪 Belgium
    "spa": "🇧🇪",
    "spa francorchamps": "🇧🇪",

    # 🇪🇸 Spain
    "barcelona": "🇪🇸",
    "catalunya": "🇪🇸",

    # 🇯🇵 Japan
    "tsukuba": "🇯🇵",
    "suzuka": "🇯🇵",

    # 🇫🇷 France
    "le mans": "🇫🇷",
    "magny cours": "🇫🇷",
    "paul ricard": "🇫🇷",

    # 🇦🇺 Australia
    "bathurst": "🇦🇺",
    "mount panorama": "🇦🇺",

    # 🇨🇦 Canada
    "gilles villeneuve": "🇨🇦",
    "montreal": "🇨🇦",

    # 🇦🇹 Austria
    "red bull ring": "🇦🇹",

    # 🇵🇹 Portugal
    "estoril": "🇵🇹",
    "portimao": "🇵🇹",

    # 🇧🇷 Brazil
    "interlagos": "🇧🇷",

    # UAE
    "yas marina": "🇦🇪",
    "dubai": "🇦🇪",

    # 🇿🇦 South Africa
    "kyalami": "🇿🇦",

    # -----------------
    # Fictional/Original
    # -----------------
    "highlands": "🏴",
    "black cat county": "🏜️",

    # fallback values
    "unknown": "",
    "default": "",
}


def get_track_flag(track: str) -> str:
    """Return the country flag for a given track name."""
    if not track:
        return ""
    key = track.lower()
    return TRACK_FLAGS.get(key, "")

