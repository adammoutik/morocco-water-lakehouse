import pytest
from src.config.locations import (
    location_id_from_filename,
    location_type_for,
    display_name_for,
    region_for,
    dam_location_ids,
    BASIN_LOCATION_ID
)


def test_location_id_from_filename():
    assert location_id_from_filename("yacoub_el_mansour_2026-08-01_to_2026-09-30.json") == "yacoub_el_mansour"
    assert location_id_from_filename("tensift_2026-08-01_to_2026-09-30.parquet") == BASIN_LOCATION_ID
    assert location_id_from_filename("raw/open_meteo/lalla_takerkoust_2026-08-01_to_2026-09-30.json") == "lalla_takerkoust"


def test_location_metadata_lookups():
    assert location_type_for("yacoub_el_mansour") == "dam"
    assert location_type_for(BASIN_LOCATION_ID) == "basin"
    assert display_name_for("yacoub_el_mansour") == "Yacoub El Mansour"
    assert region_for("yacoub_el_mansour") == "High Atlas"
    assert "yacoub_el_mansour" in dam_location_ids()
    assert BASIN_LOCATION_ID not in dam_location_ids()
