import re
from typing import Optional


LOCATIONS = {

    "tensift_basin": {
        "display_name": "Tensift Basin",
        "latitude": 31.627,
        "longitude": -8.011,
        "location_type": "basin",
        "region": "Tensift basin",
    },

    "yacoub_el_mansour": {
        "display_name": "Yacoub El Mansour",
        "latitude": 31.1899,
        "longitude": -8.0882,
        "location_type": "dam",
        "region": "High Atlas",
    },

    "lalla_takerkoust": {
        "display_name": "Lalla Takerkoust",
        "latitude": 31.3548,
        "longitude": -8.1360,
        "location_type": "dam",
        "region": "Haouz plain",
    },

    "abou_el_abess_sebti": {
        "display_name": "Abou El Abess Sebti",
        "latitude": 31.14,
        "longitude": -8.31,
        "location_type": "dam",
        "region": "High Atlas",
    },

    "sd_mohamed_ben_slimane_el_jazouli": {
        "display_name": "Sidi Mohamed Ben Slimane El Jazouli",
        "latitude": 31.25,
        "longitude": -9.18,
        "location_type": "dam",
        "region": "Western Tensift",
    },

    "bge_my_abdrhmane": {
        "display_name": "BGE Moulay Abderrahmane",
        "latitude": 31.10,
        "longitude": -8.76,
        "location_type": "dam",
        "region": "High Atlas foothills",
    }
}

BASIN_LOCATION_ID = "tensift_basin"
_FILENAME_DATE_RANGE = re.compile(
    r"^(?P<location>.+)_\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}$"
)
_LEGACY_BASIN_IDS = {"tensift", "tensift_basin"}


def get_location(location_id: str) -> Optional[dict]:
    return LOCATIONS.get(location_id)


def dam_location_ids() -> set:
    return {k for k, v in LOCATIONS.items() if v["location_type"] == "dam"}


def location_id_from_filename(filename: str) -> str:
    """Parse location_id from Bronze keys like yacoub_el_mansour_2026-08-01_to_2026-09-30.json."""
    base_name = filename.rsplit("/", 1)[-1]
    if base_name.lower().endswith(".json"):
        base_name = base_name[:-5]
    elif base_name.lower().endswith(".parquet"):
        base_name = base_name[:-8]

    match = _FILENAME_DATE_RANGE.match(base_name)
    location_id = match.group("location") if match else base_name
    if location_id in _LEGACY_BASIN_IDS:
        return BASIN_LOCATION_ID
    return location_id


def location_type_for(location_id: str) -> str:
    site = get_location(location_id)
    if site:
        return site["location_type"]
    return "basin" if location_id == BASIN_LOCATION_ID else "dam"


def display_name_for(location_id: str) -> str:
    site = get_location(location_id)
    if site:
        return site["display_name"]
    return location_id.replace("_", " ").title()


def region_for(location_id: str) -> str:
    site = get_location(location_id)
    if site and site.get("region"):
        return site["region"]
    return "Tensift basin"
