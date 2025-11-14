# car_flags.py

# Manufacturer → country flag mapping

CAR_FLAGS = {
    # 🇮🇹 Italy
    "ferrari": "🇮🇹",
    "lamborghini": "🇮🇹",
    "maserati": "🇮🇹",
    "fiat": "🇮🇹",
    "abarth": "🇮🇹",
    "pagani": "🇮🇹",
    "alfa romeo": "🇮🇹",

    # 🇩🇪 Germany
    "bmw": "🇩🇪",
    "mercedes": "🇩🇪",
    "mercedes-benz": "🇩🇪",
    "audi": "🇩🇪",
    "porsche": "🇩🇪",
    "vw": "🇩🇪",
    "volkswagen": "🇩🇪",

    # 🇯🇵 Japan
    "mazda": "🇯🇵",
    "nissan": "🇯🇵",
    "toyota": "🇯🇵",
    "honda": "🇯🇵",
    "mitsubishi": "🇯🇵",
    "subaru": "🇯🇵",

    # 🇺🇸 USA
    "chevrolet": "🇺🇸",
    "ford": "🇺🇸",
    "dodge": "🇺🇸",
    "cadillac": "🇺🇸",
    "corvette": "🇺🇸",

    # 🇬🇧 UK
    "lotus": "🇬🇧",
    "mclaren": "🇬🇧",
    "aston martin": "🇬🇧",
    "caterham": "🇬🇧",
    "jaguar": "🇬🇧",

    # 🇸🇪 Sweden
    "koenigsegg": "🇸🇪",

    # 🇰🇷 Korea
    "hyundai": "🇰🇷",
    "kia": "🇰🇷",

    # fallback
    "unknown": "",
    "default": "",
}


def get_car_flag(car_name: str) -> str:
    """
    Returns a country flag for a given car name.
    Uses manufacturer detection with exact and prefix matching.
    """
    if not car_name:
        return ""

    # Extract manufacturer (first word)
    manufacturer = car_name.split()[0].lower()

    # 1. Exact match
    if manufacturer in CAR_FLAGS:
        return CAR_FLAGS[manufacturer]

    # 2. Prefix match: handles Abarth500 → Abarth, Corvette → Chevrolet
    for key in CAR_FLAGS.keys():
        if manufacturer.startswith(key):
            return CAR_FLAGS[key]

    return ""

