"""Build the curated offline world-city list used by Rohini Astro.

Input files come from the official GeoNames gazetteer dump.  Bulgaria is
excluded because the application keeps its more detailed Bulgarian list.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


MIN_POPULATION = 250_000


def read_countries(path: Path) -> dict[str, str]:
    countries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) >= 5:
            countries[fields[0]] = fields[4]
    return countries


def read_admin_areas(path: Path) -> dict[str, str]:
    areas: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) >= 2:
            areas[fields[0]] = fields[1]
    return areas


def read_selected_cities(
    archive_path: Path,
    countries: dict[str, str],
    admin_areas: dict[str, str],
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    with ZipFile(archive_path) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".txt"))
        with archive.open(member) as source:
            for raw_line in source:
                fields = raw_line.decode("utf-8").rstrip("\n").split("\t")
                if len(fields) < 19:
                    continue

                country_code = fields[8]
                feature_class = fields[6]
                feature_code = fields[7]
                population = int(fields[14] or 0)

                if country_code == "BG" or feature_class != "P":
                    continue
                if feature_code != "PPLC" and population < MIN_POPULATION:
                    continue

                city_name = fields[1].strip()
                country_name = countries.get(country_code, country_code)
                admin_key = f"{country_code}.{fields[10]}" if fields[10] else ""
                selected.append(
                    {
                        "geoname_id": int(fields[0]),
                        "city": city_name,
                        "country": country_name,
                        "country_code": country_code,
                        "admin1": admin_areas.get(admin_key, ""),
                        "lat": float(fields[4]),
                        "lon": float(fields[5]),
                        "timezone": fields[17],
                        "population": population,
                        "is_capital": feature_code == "PPLC",
                        "source": "GeoNames",
                    }
                )
    return selected


def add_unique_display_names(cities: list[dict[str, object]]) -> None:
    bases = [f"{city['city']}, {city['country']}" for city in cities]
    counts = Counter(bases)
    used: set[str] = set()

    for city, base in zip(cities, bases):
        display = base
        if counts[base] > 1 and city["admin1"]:
            display = f"{city['city']}, {city['admin1']}, {city['country']}"
        if display in used:
            display = f"{display} [{city['geoname_id']}]"
        city["name"] = display
        used.add(display)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cities", required=True, type=Path)
    parser.add_argument("--countries", required=True, type=Path)
    parser.add_argument("--admin1", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    cities = read_selected_cities(
        args.cities,
        read_countries(args.countries),
        read_admin_areas(args.admin1),
    )
    add_unique_display_names(cities)
    cities.sort(key=lambda city: (str(city["country"]), str(city["city"]), -int(city["population"])))

    args.output.write_text(
        json.dumps(cities, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    capitals = sum(bool(city["is_capital"]) for city in cities)
    print(f"Wrote {len(cities)} cities ({capitals} national capitals) to {args.output}")


if __name__ == "__main__":
    main()
