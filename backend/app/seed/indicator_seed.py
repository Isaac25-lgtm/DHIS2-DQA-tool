from typing import Any


def _seed_item(
    *,
    indicator_name: str,
    indicator_group: str,
    hmis_code: str,
    dhis2_uid_or_operand: str,
    dataset_name: str,
    hmis_section: str,
    source_register: str,
    category_combo: str | None,
    sort_order: int,
    notes: str | None = None,
    is_death_indicator: bool = False,
) -> dict[str, Any]:
    return {
        "indicator_name": indicator_name,
        "indicator_group": indicator_group,
        "hmis_code": hmis_code,
        "dhis2_uid_or_operand": dhis2_uid_or_operand,
        "dataset_name": dataset_name,
        "hmis_section": hmis_section,
        "source_register": source_register,
        "category_combo": category_combo,
        "value_type": "integer",
        "is_active": True,
        "is_required_by_default": True,
        "default_discrepancy_threshold_percent": 5.0,
        "is_death_indicator": is_death_indicator,
        "sort_order": sort_order,
        "notes": notes,
    }


CONFIRMED_INDICATOR_SEED: list[dict[str, Any]] = [
    _seed_item(indicator_name="Total deliveries in the unit", indicator_group="Maternity", hmis_code="105-MA04", dhis2_uid_or_operand="idXOxt69W0e", dataset_name="HMIS 105:02-03 - OPD Monthly Report (MCH, FP, EID, EPI & HEPB)", hmis_section="Maternity", source_register="Maternity register", category_combo="MCH Age", sort_order=1),
    _seed_item(indicator_name="Live births total", indicator_group="Maternity", hmis_code="105-MA05A1", dhis2_uid_or_operand="fEz9wGsA6YU", dataset_name="HMIS 105:02-03 - OPD Monthly Report (MCH, FP, EID, EPI & HEPB)", hmis_section="Maternity", source_register="Maternity register", category_combo=None, sort_order=2),
    _seed_item(indicator_name="Live births less than 2.5kg", indicator_group="Maternity", hmis_code="105-MA05A2", dhis2_uid_or_operand="P1MyPWVxi5T", dataset_name="HMIS 105:02-03", hmis_section="Maternity", source_register="Maternity register", category_combo=None, sort_order=3),
    _seed_item(indicator_name="Fresh stillbirths total", indicator_group="Maternity", hmis_code="105-MA05B1", dhis2_uid_or_operand="T8W0wbzErSF", dataset_name="HMIS 105:02-03", hmis_section="Maternity", source_register="Maternity register", category_combo=None, sort_order=4, notes="High-risk outcome; review discrepancies carefully.", is_death_indicator=True),
    _seed_item(indicator_name="Macerated stillbirths total", indicator_group="Maternity", hmis_code="105-MA05C1", dhis2_uid_or_operand="ULL9lX3DO7V", dataset_name="HMIS 105:02-03", hmis_section="Maternity", source_register="Maternity register", category_combo=None, sort_order=5, notes="High-risk outcome; review discrepancies carefully.", is_death_indicator=True),
    _seed_item(indicator_name="Newborn deaths", indicator_group="KMC / Newborn Care", hmis_code="105-MA12", dhis2_uid_or_operand="oYyevZODdQp", dataset_name="HMIS 105:02-03", hmis_section="Newborn Care", source_register="Death register", category_combo="Age 0-7 days, 8-28 days", sort_order=6, notes="Category-specific operands still need to be added later.", is_death_indicator=True),
    _seed_item(indicator_name="Maternal deaths", indicator_group="Maternity", hmis_code="105-MA13", dhis2_uid_or_operand="F8Iz6QcexWB", dataset_name="HMIS 105:02-03", hmis_section="Maternity", source_register="Death register", category_combo="MCH Age", sort_order=7, is_death_indicator=True),
    _seed_item(indicator_name="Live babies at discharge", indicator_group="KMC / Newborn Care", hmis_code="105-MA09", dhis2_uid_or_operand="H1oTelCAQry", dataset_name="HMIS 105:02-03", hmis_section="Newborn Care", source_register="Maternity register", category_combo=None, sort_order=8),
    _seed_item(indicator_name="ANC 1st visit for women", indicator_group="ANC", hmis_code="105-AN01A", dhis2_uid_or_operand="Q9nSogNmKPt", dataset_name="HMIS 105:02-03", hmis_section="ANC", source_register="ANC register", category_combo="MCH Age", sort_order=9),
    _seed_item(indicator_name="ANC 1st contacts/visits in 1st trimester", indicator_group="ANC", hmis_code="105-AN01b", dhis2_uid_or_operand="uUYRrEU5iOB", dataset_name="HMIS 105:02-03", hmis_section="ANC", source_register="ANC register", category_combo=None, sort_order=10),
    _seed_item(indicator_name="ANC 4th visit for women", indicator_group="ANC", hmis_code="105-AN02", dhis2_uid_or_operand="RnLOFSYaAhp", dataset_name="HMIS 105:02-03", hmis_section="ANC", source_register="ANC register", category_combo="MCH Age", sort_order=11),
    _seed_item(indicator_name="Total ANC contacts/visits", indicator_group="ANC", hmis_code="105-AN04", dhis2_uid_or_operand="PaceRdSpmgy", dataset_name="HMIS 105:02-03", hmis_section="ANC", source_register="ANC register", category_combo="MCH Age", sort_order=12),
    _seed_item(indicator_name="Pregnant women who received IPT3", indicator_group="ANC", hmis_code="105-AN06C", dhis2_uid_or_operand="DuMMAbvDfjn", dataset_name="HMIS 105:02-03", hmis_section="ANC", source_register="ANC register", category_combo="MCH Age", sort_order=13),
    _seed_item(indicator_name="PNC attendance at 24 hours", indicator_group="PNC", hmis_code="105-PN01", dhis2_uid_or_operand="RYcEItpNCUp.K01CbPXaICz", dataset_name="HMIS 105:02-03", hmis_section="PNC", source_register="PNC register", category_combo="24 hours", sort_order=14),
    _seed_item(indicator_name="PNC attendance at 6 days", indicator_group="PNC", hmis_code="105-PN01", dhis2_uid_or_operand="RYcEItpNCUp.Ck8FveDhZSy", dataset_name="HMIS 105:02-03", hmis_section="PNC", source_register="PNC register", category_combo="6 days", sort_order=15),
    _seed_item(indicator_name="PNC attendance at 6 weeks", indicator_group="PNC", hmis_code="105-PN01", dhis2_uid_or_operand="RYcEItpNCUp.YftbycyVKYC", dataset_name="HMIS 105:02-03", hmis_section="PNC", source_register="PNC register", category_combo="6 weeks", sort_order=16),
    _seed_item(indicator_name="Baby received PNC check at 6 hours after birth", indicator_group="PNC", hmis_code="105-MA25A", dhis2_uid_or_operand="VBN3wvLEZjW", dataset_name="HMIS 105:02-03", hmis_section="PNC", source_register="PNC register", category_combo=None, sort_order=17),
    _seed_item(indicator_name="Mother received PNC check at 6 hours after birth", indicator_group="PNC", hmis_code="105-MA25B", dhis2_uid_or_operand="UrX15EcK8BZ", dataset_name="HMIS 105:02-03", hmis_section="PNC", source_register="PNC register", category_combo=None, sort_order=18),
    _seed_item(indicator_name="Mothers admitted with preterm labour", indicator_group="Maternity", hmis_code="105-MA06A", dhis2_uid_or_operand="jSoIv4DItaH", dataset_name="HMIS 105:02-03", hmis_section="Maternity", source_register="Maternity register", category_combo=None, sort_order=19),
    _seed_item(indicator_name="Preterm births in the unit", indicator_group="Maternity", hmis_code="105-MA07A", dhis2_uid_or_operand="WX0V1OdNB4i", dataset_name="HMIS 105:02-03", hmis_section="Maternity", source_register="Maternity register", category_combo=None, sort_order=20),
    _seed_item(indicator_name="Low birth weight babies initiated on KMC", indicator_group="KMC / Newborn Care", hmis_code="105-MA08", dhis2_uid_or_operand="X6rK1GHbLYp", dataset_name="HMIS 105:02-03", hmis_section="Newborn Care", source_register="KMC register", category_combo=None, sort_order=21),
    _seed_item(indicator_name="Babies with birth asphyxia", indicator_group="Birth Asphyxia", hmis_code="105-MA23", dhis2_uid_or_operand="nnmOsAUssg9", dataset_name="HMIS 105:02-03", hmis_section="Newborn Care", source_register="Maternity register", category_combo=None, sort_order=22),
    _seed_item(indicator_name="Live babies successfully resuscitated", indicator_group="Birth Asphyxia", hmis_code="105-MA24", dhis2_uid_or_operand="h5qpxtCVwAp", dataset_name="HMIS 105:02-03", hmis_section="Newborn Care", source_register="Maternity register", category_combo=None, sort_order=23),
    _seed_item(indicator_name="Referrals to maternity unit total", indicator_group="Referrals", hmis_code="105-MA02A", dhis2_uid_or_operand="AGmXoLiT89x", dataset_name="HMIS 105:02-03", hmis_section="Referrals", source_register="Referral register", category_combo=None, sort_order=24),
    _seed_item(indicator_name="Referrals from maternity", indicator_group="Referrals", hmis_code="105-MA03", dhis2_uid_or_operand="YNqGVS6GEyo", dataset_name="HMIS 105:02-03", hmis_section="Referrals", source_register="Referral register", category_combo=None, sort_order=25),
    _seed_item(indicator_name="Uterotonics, 3rd stage, Oxytocin", indicator_group="Uterotonics / PPH", hmis_code="105-MA27A", dhis2_uid_or_operand="nA0w3UvRDpD", dataset_name="HMIS 105:02-03", hmis_section="PPH Management", source_register="Maternity register", category_combo=None, sort_order=26),
    _seed_item(indicator_name="Uterotonics, 3rd stage, Misoprostol", indicator_group="Uterotonics / PPH", hmis_code="105-MA27B", dhis2_uid_or_operand="IRfdGnNJzGW", dataset_name="HMIS 105:02-03", hmis_section="PPH Management", source_register="Maternity register", category_combo=None, sort_order=27),
    _seed_item(indicator_name="Uterotonics, 3rd stage, Heat-stable Carbetocin", indicator_group="Uterotonics / PPH", hmis_code="105-MA27C", dhis2_uid_or_operand="qBXjgpcV5zX", dataset_name="HMIS 105:02-03", hmis_section="PPH Management", source_register="Maternity register", category_combo=None, sort_order=28),
    _seed_item(indicator_name="Uterotonics, 3rd stage, Ergometrine", indicator_group="Uterotonics / PPH", hmis_code="105-MA27D", dhis2_uid_or_operand="SxPXVqUFskM", dataset_name="HMIS 105:02-03", hmis_section="PPH Management", source_register="Maternity register", category_combo=None, sort_order=29),
    _seed_item(indicator_name="PPH treatment, Oxytocin", indicator_group="Uterotonics / PPH", hmis_code="105-MA28A", dhis2_uid_or_operand="PU4JyVtmAYY", dataset_name="HMIS 105:02-03", hmis_section="PPH Management", source_register="Maternity register", category_combo=None, sort_order=30),
    _seed_item(indicator_name="PPH treatment, Misoprostol", indicator_group="Uterotonics / PPH", hmis_code="105-MA28B", dhis2_uid_or_operand="hawWpaDwa8v", dataset_name="HMIS 105:02-03", hmis_section="PPH Management", source_register="Maternity register", category_combo=None, sort_order=31),
    _seed_item(indicator_name="PPH treatment, Tranexamic", indicator_group="Uterotonics / PPH", hmis_code="105-MA28C", dhis2_uid_or_operand="ziCT29DWKRC", dataset_name="HMIS 105:02-03", hmis_section="PPH Management", source_register="Maternity register", category_combo=None, sort_order=32),
    _seed_item(indicator_name="PPH treatment, Ergometrine", indicator_group="Uterotonics / PPH", hmis_code="105-MA28D", dhis2_uid_or_operand="nTMjQrqEa8m", dataset_name="HMIS 105:02-03", hmis_section="PPH Management", source_register="Maternity register", category_combo=None, sort_order=33),
]


def get_confirmed_indicator_seed() -> list[dict[str, Any]]:
    return CONFIRMED_INDICATOR_SEED
