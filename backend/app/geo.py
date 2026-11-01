"""Location: EXIF GPS + capture time, offline reverse geocoding (GeoNames cities ≥ 1000 people) and trip detection.

Nothing leaves the machine: place names come from the dataset bundled with `reverse_geocoder`.
"""
from __future__ import annotations

import logging
import math
import threading
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .media import _parse_exif_dt, open_any

log = logging.getLogger(__name__)

GPS_IFD = 0x8825
EXIF_IFD = 0x8769

COUNTRIES = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan", "AG": "Antigua and Barbuda", "AL": "Albania", "AM": "Armenia",
    "AO": "Angola", "AR": "Argentina", "AT": "Austria", "AU": "Australia", "AW": "Aruba", "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina",
    "BB": "Barbados", "BD": "Bangladesh", "BE": "Belgium", "BF": "Burkina Faso", "BG": "Bulgaria", "BH": "Bahrain", "BJ": "Benin",
    "BM": "Bermuda", "BN": "Brunei", "BO": "Bolivia", "BR": "Brazil", "BS": "Bahamas", "BT": "Bhutan", "BW": "Botswana", "BY": "Belarus",
    "BZ": "Belize", "CA": "Canada", "CD": "DR Congo", "CH": "Switzerland", "CI": "Côte d'Ivoire", "CL": "Chile", "CM": "Cameroon",
    "CN": "China", "CO": "Colombia", "CR": "Costa Rica", "CU": "Cuba", "CV": "Cape Verde", "CW": "Curaçao", "CY": "Cyprus", "CZ": "Czechia",
    "DE": "Germany", "DK": "Denmark", "DM": "Dominica", "DO": "Dominican Republic", "DZ": "Algeria", "EC": "Ecuador", "EE": "Estonia",
    "EG": "Egypt", "ES": "Spain", "ET": "Ethiopia", "FI": "Finland", "FJ": "Fiji", "FO": "Faroe Islands", "FR": "France", "GA": "Gabon",
    "GB": "United Kingdom", "GD": "Grenada", "GE": "Georgia", "GF": "French Guiana", "GH": "Ghana", "GI": "Gibraltar", "GL": "Greenland",
    "GP": "Guadeloupe", "GR": "Greece", "GT": "Guatemala", "GU": "Guam", "HK": "Hong Kong", "HN": "Honduras", "HR": "Croatia", "HT": "Haiti",
    "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland", "IL": "Israel", "IM": "Isle of Man", "IN": "India", "IQ": "Iraq", "IR": "Iran",
    "IS": "Iceland", "IT": "Italy", "JE": "Jersey", "JM": "Jamaica", "JO": "Jordan", "JP": "Japan", "KE": "Kenya", "KG": "Kyrgyzstan",
    "KH": "Cambodia", "KR": "South Korea", "KW": "Kuwait", "KY": "Cayman Islands", "KZ": "Kazakhstan", "LA": "Laos", "LB": "Lebanon",
    "LC": "Saint Lucia", "LI": "Liechtenstein", "LK": "Sri Lanka", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "LY": "Libya",
    "MA": "Morocco", "MC": "Monaco", "MD": "Moldova", "ME": "Montenegro", "MG": "Madagascar", "MK": "North Macedonia", "ML": "Mali",
    "MM": "Myanmar", "MN": "Mongolia", "MO": "Macao", "MQ": "Martinique", "MT": "Malta", "MU": "Mauritius", "MV": "Maldives", "MW": "Malawi",
    "MX": "Mexico", "MY": "Malaysia", "MZ": "Mozambique", "NA": "Namibia", "NC": "New Caledonia", "NE": "Niger", "NG": "Nigeria",
    "NI": "Nicaragua", "NL": "Netherlands", "NO": "Norway", "NP": "Nepal", "NZ": "New Zealand", "OM": "Oman", "PA": "Panama", "PE": "Peru",
    "PF": "French Polynesia", "PG": "Papua New Guinea", "PH": "Philippines", "PK": "Pakistan", "PL": "Poland", "PR": "Puerto Rico",
    "PS": "Palestine", "PT": "Portugal", "PY": "Paraguay", "QA": "Qatar", "RE": "Réunion", "RO": "Romania", "RS": "Serbia", "RU": "Russia",
    "RW": "Rwanda", "SA": "Saudi Arabia", "SC": "Seychelles", "SD": "Sudan", "SE": "Sweden", "SG": "Singapore", "SI": "Slovenia",
    "SK": "Slovakia", "SM": "San Marino", "SN": "Senegal", "SR": "Suriname", "SV": "El Salvador", "SY": "Syria", "TC": "Turks and Caicos",
    "TH": "Thailand", "TJ": "Tajikistan", "TN": "Tunisia", "TR": "Türkiye", "TT": "Trinidad and Tobago", "TW": "Taiwan", "TZ": "Tanzania",
    "UA": "Ukraine", "UG": "Uganda", "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan", "VA": "Vatican City", "VC": "Saint Vincent",
    "VE": "Venezuela", "VG": "British Virgin Islands", "VI": "U.S. Virgin Islands", "VN": "Vietnam", "XK": "Kosovo", "YE": "Yemen",
    "ZA": "South Africa", "ZM": "Zambia", "ZW": "Zimbabwe",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ------------------------------------------------------------------ EXIF
def _rational(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError, ZeroDivisionError):
        num, den = v
        return float(num) / float(den) if den else 0.0


def _dms(values, ref) -> float | None:
    try:
        d, m, s = (_rational(x) for x in values)
    except (TypeError, ValueError):
        return None
    deg = d + m / 60.0 + s / 3600.0
    if str(ref).upper().startswith(("S", "W")):
        deg = -deg
    return deg


def read_geo(path: Path) -> dict:
    """{lat, lon, ts} from EXIF (any field may be None). Reads headers only (cheap)."""
    out: dict = {"lat": None, "lon": None, "ts": None}
    try:
        with open_any(path) as im:
            exif = im.getexif()
            gps = exif.get_ifd(GPS_IFD) if exif else {}
            if gps and 2 in gps and 4 in gps:
                lat, lon = _dms(gps[2], gps.get(1, "N")), _dms(gps[4], gps.get(3, "E"))
                if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180 and not (lat == 0 and lon == 0):
                    out["lat"], out["lon"] = round(lat, 6), round(lon, 6)
            sub = exif.get_ifd(EXIF_IFD) if exif else {}
            out["ts"] = _parse_exif_dt(sub.get(36867) or sub.get(36868) or exif.get(306))
    except Exception as exc:  # noqa: BLE001 - unreadable files simply have no location
        log.debug("geo read failed for %s: %s", path, exc)
    return out


# ------------------------------------------------------------------ reverse geocoding
_rg = None
_rg_lock = threading.Lock()


def _geocoder():
    global _rg
    with _rg_lock:
        if _rg is None:
            import reverse_geocoder

            _rg = reverse_geocoder.RGeocoder(mode=1, verbose=False)
        return _rg


def places_for(points: list[tuple[float, float]]) -> list[dict]:
    """[(lat, lon)] → [{city, region, cc, country}] (nearest GeoNames place)."""
    if not points:
        return []
    try:
        res = _geocoder().query(points)
    except Exception as exc:  # noqa: BLE001
        log.warning("reverse geocoding unavailable: %s", exc)
        return [{"city": None, "region": None, "cc": None, "country": None} for _ in points]
    return [{"city": r.get("name"), "region": r.get("admin1") or None, "cc": r.get("cc"),
             "country": COUNTRIES.get(r.get("cc", ""), r.get("cc"))} for r in res]


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))


# ------------------------------------------------------------------ trips
@dataclass
class Item:
    id: str
    ts: float | None
    lat: float | None = None
    lon: float | None = None
    place: dict | None = None


@dataclass
class Trip:
    ids: list[str] = field(default_factory=list)
    start: float = 0.0
    end: float = 0.0
    places: Counter = field(default_factory=Counter)
    countries: Counter = field(default_factory=Counter)
    regions: Counter = field(default_factory=Counter)
    center: tuple[float, float] | None = None

    def name(self) -> str:
        city, n = self.places.most_common(1)[0] if self.places else (None, 0)
        total = sum(self.places.values()) or 1
        if len(self.countries) >= 2:
            where = " & ".join(c for c, _ in self.countries.most_common(2))
        elif city and n / total >= 0.5:
            where = city
        elif self.regions:
            where = self.regions.most_common(1)[0][0]
        else:
            where = city or "Trip"
        a, b = datetime.fromtimestamp(self.start), datetime.fromtimestamp(self.end)
        if (a.year, a.month) == (b.year, b.month):
            when = f"{MONTHS[a.month - 1]} {a.year}"
        elif a.year == b.year:
            when = f"{MONTHS[a.month - 1]}–{MONTHS[b.month - 1]} {a.year}"
        else:
            when = f"{MONTHS[a.month - 1]} {a.year}–{MONTHS[b.month - 1]} {b.year}"
        return f"{where} · {when}"


def find_home(items: list[Item]) -> tuple[float, float] | None:
    """Home = the ~25 km grid cell with photos on the most distinct days."""
    days: dict[tuple[int, int], set] = {}
    sums: dict[tuple[int, int], list[float]] = {}
    for it in items:
        if it.lat is None or it.ts is None:
            continue
        cell = (round(it.lat * 4), round(it.lon * 4))
        days.setdefault(cell, set()).add(int(it.ts // 86400))
        s = sums.setdefault(cell, [0.0, 0.0, 0])
        s[0] += it.lat
        s[1] += it.lon
        s[2] += 1
    if not days:
        return None
    cell = max(days, key=lambda c: (len(days[c]), sums[c][2]))
    s = sums[cell]
    return s[0] / s[2], s[1] / s[2]


def detect_trips(items: list[Item], away_km: float = 80.0, gap_hours: float = 36.0, min_photos: int = 5,
                 home: tuple[float, float] | None = None) -> tuple[list[Trip], tuple[float, float] | None]:
    """Trips = runs of photos taken far from home with no long gap and no home photo in between.
    Photos without GPS (e.g. another camera) taken during a trip join it."""
    home = home or find_home(items)
    if home is None:
        return [], None
    located = [it for it in items if it.lat is not None and it.ts is not None]
    away = sorted((it for it in located if haversine_km(home, (it.lat, it.lon)) > away_km), key=lambda it: it.ts)
    at_home = sorted(it.ts for it in located if haversine_km(home, (it.lat, it.lon)) <= away_km)
    trips: list[Trip] = []
    cur: Trip | None = None
    hi = 0
    for it in away:
        while hi < len(at_home) and at_home[hi] < it.ts:
            hi += 1
        home_between = cur is not None and hi > 0 and at_home[hi - 1] > cur.end
        if cur is None or it.ts - cur.end > gap_hours * 3600 or home_between:
            cur = Trip(start=it.ts, end=it.ts)
            trips.append(cur)
        cur.ids.append(it.id)
        cur.end = it.ts
        if it.place:
            if it.place.get("city"):
                cur.places[it.place["city"]] += 1
            if it.place.get("country"):
                cur.countries[it.place["country"]] += 1
            if it.place.get("region"):
                cur.regions[it.place["region"]] += 1
    trips = [t for t in trips if len(t.ids) >= min_photos]
    by_id = {it.id: it for it in located}
    for t in trips:
        pts = [(by_id[i].lat, by_id[i].lon) for i in t.ids]
        t.center = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    margin = 3 * 3600
    in_trip = {i for t in trips for i in t.ids}
    for it in items:
        if it.id in in_trip or it.ts is None or it.lat is not None:
            continue
        for t in trips:
            if t.start - margin <= it.ts <= t.end + margin:
                t.ids.append(it.id)
                break
    return trips, home
