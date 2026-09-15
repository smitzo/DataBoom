"""Locale-aware row contexts for correlated person data.

Purpose:
    Build one deterministic identity and location context per generated row.

Data flow:
    locale + run seed + table + row index -> person context -> matching columns.

Why this layer exists:
    Generating names, gender, email, phone, and address independently creates
    individually plausible cells that contradict each other. A shared row context
    makes those fields agree without putting an LLM in the high-volume hot path.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from faker.providers.person.en_IN import Provider as IndiaPersonProvider
from faker.providers.person.en_US import Provider as UnitedStatesPersonProvider

from databoom.generation.domains import LocaleProfile
from databoom.generation.seed import SeedManager


@dataclass(frozen=True)
class LocationProfile:
    """One internally consistent city, region, postcode, and phone profile."""

    city: str
    region: str
    postcode_prefix: str
    area_code: str
    country_code: str
    country_name: str
    street_names: tuple[str, ...]


@dataclass(frozen=True)
class PersonContext:
    """Correlated values describing one synthetic person."""

    first_name: str
    last_name: str
    full_name: str
    gender: str
    age: int
    birth_date: date
    email: str
    phone: str
    city: str
    region: str
    country_code: str
    country_name: str
    postal_code: str
    street_address: str

    def value_for(self, column_name: str) -> Any | None:
        """Return a correlated value for a recognized person-related column."""

        name = column_name.casefold()
        values: dict[str, Any] = {
            "first_name": self.first_name,
            "given_name": self.first_name,
            "last_name": self.last_name,
            "surname": self.last_name,
            "family_name": self.last_name,
            "full_name": self.full_name,
            "customer_name": self.full_name,
            "patient_name": self.full_name,
            "contact_name": self.full_name,
            "name": self.full_name,
            "gender": self.gender,
            "sex": self.gender,
            "age": self.age,
            "date_of_birth": self.birth_date,
            "birth_date": self.birth_date,
            "dob": self.birth_date,
            "email": self.email,
            "email_address": self.email,
            "phone": self.phone,
            "phone_number": self.phone,
            "mobile": self.phone,
            "mobile_number": self.phone,
            "city": self.city,
            "state": self.region,
            "province": self.region,
            "region": self.region,
            "country": self.country_code,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "postal_code": self.postal_code,
            "postcode": self.postal_code,
            "zip": self.postal_code,
            "zip_code": self.postal_code,
            "address": self.street_address,
            "street_address": self.street_address,
        }
        return values.get(name)


class PersonContextProvider:
    """Create deterministic row contexts from locale-specific catalogues."""

    def __init__(self, seed_manager: SeedManager, locale: LocaleProfile) -> None:
        self.seed_manager = seed_manager
        self.locale = locale

    def for_row(
        self,
        table_name: str,
        column_names: Iterable[str],
        row_index: int,
    ) -> PersonContext | None:
        """Return a person context only for person-shaped rows."""

        normalized_columns = {name.casefold() for name in column_names}
        if not normalized_columns.intersection(_PERSON_SIGNALS):
            return None

        stream = self.seed_manager.stream(
            "person-context", self.locale.value, table_name, row_index
        )
        gender = "female" if stream.random() < 0.5 else "male"
        first_names, last_names, locations = _catalogue_for(self.locale, gender)
        first_name = first_names[stream.randrange(len(first_names))]
        last_name = last_names[stream.randrange(len(last_names))]
        location = locations[stream.randrange(len(locations))]
        age = stream.randint(18, 85)
        birth_date = _birth_date(stream, age)
        email_token = _email_token(first_name, last_name)
        email = f"{email_token}.{row_index + 1}@example.test"
        phone = _phone_number(stream, self.locale, location.area_code)
        postal_code = _postal_code(stream, self.locale, location.postcode_prefix)
        street_name = location.street_names[stream.randrange(len(location.street_names))]
        street_address = f"{stream.randint(1, 999)} {street_name}"
        return PersonContext(
            first_name=first_name,
            last_name=last_name,
            full_name=f"{first_name} {last_name}",
            gender=gender,
            age=age,
            birth_date=birth_date,
            email=email,
            phone=phone,
            city=location.city,
            region=location.region,
            country_code=location.country_code,
            country_name=location.country_name,
            postal_code=postal_code,
            street_address=street_address,
        )


def _catalogue_for(
    locale: LocaleProfile,
    gender: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[LocationProfile, ...]]:
    if locale == LocaleProfile.EN_IN:
        names = (
            _as_tuple(IndiaPersonProvider.first_names_female)
            if gender == "female"
            else _as_tuple(IndiaPersonProvider.first_names_male)
        )
        return names, _as_tuple(IndiaPersonProvider.last_names), _INDIA_LOCATIONS
    names = (
        _as_tuple(UnitedStatesPersonProvider.first_names_female)
        if gender == "female"
        else _as_tuple(UnitedStatesPersonProvider.first_names_male)
    )
    return names, _as_tuple(UnitedStatesPersonProvider.last_names), _US_LOCATIONS


def _as_tuple(values: Iterable[str] | Mapping[str, float]) -> tuple[str, ...]:
    return tuple(values.keys()) if isinstance(values, Mapping) else tuple(values)


def _birth_date(stream, age: int) -> date:
    reference = date(2025, 1, 1)
    month = stream.randint(1, 12)
    day = stream.randint(1, 28)
    year = reference.year - age - int((month, day) > (reference.month, reference.day))
    return date(year, month, day)


def _email_token(first_name: str, last_name: str) -> str:
    token = re.sub(r"[^a-z0-9]+", ".", f"{first_name}.{last_name}".casefold()).strip(".")
    return token or "user"


def _phone_number(stream, locale: LocaleProfile, area_code: str) -> str:
    if locale == LocaleProfile.EN_IN:
        return f"+91{stream.randint(6, 9)}{stream.randint(100_000_000, 999_999_999)}"
    return f"+1{area_code}{stream.randint(2_000_000, 9_999_999):07d}"


def _postal_code(stream, locale: LocaleProfile, prefix: str) -> str:
    if locale == LocaleProfile.EN_IN:
        return f"{prefix}{stream.randint(0, 999):03d}"
    return f"{prefix}{stream.randint(0, 99):02d}"


_PERSON_SIGNALS = {
    "first_name",
    "given_name",
    "last_name",
    "surname",
    "family_name",
    "full_name",
    "customer_name",
    "patient_name",
    "contact_name",
    "gender",
    "sex",
    "date_of_birth",
    "birth_date",
    "dob",
    "email",
    "email_address",
    "phone",
    "phone_number",
    "mobile",
    "mobile_number",
    "city",
    "postal_code",
    "postcode",
    "zip_code",
}


_US_LOCATIONS = (
    LocationProfile(
        "New York", "New York", "100", "212", "US", "United States", ("Broadway", "Madison Avenue")
    ),
    LocationProfile(
        "Los Angeles",
        "California",
        "900",
        "213",
        "US",
        "United States",
        ("Sunset Boulevard", "Wilshire Boulevard"),
    ),
    LocationProfile(
        "Chicago",
        "Illinois",
        "606",
        "312",
        "US",
        "United States",
        ("Michigan Avenue", "State Street"),
    ),
    LocationProfile(
        "Houston", "Texas", "770", "713", "US", "United States", ("Westheimer Road", "Main Street")
    ),
    LocationProfile(
        "Seattle",
        "Washington",
        "981",
        "206",
        "US",
        "United States",
        ("Pine Street", "Lake City Way"),
    ),
)


_INDIA_LOCATIONS = (
    LocationProfile(
        "Mumbai", "Maharashtra", "400", "22", "IN", "India", ("Linking Road", "Marine Drive")
    ),
    LocationProfile(
        "New Delhi", "Delhi", "110", "11", "IN", "India", ("Janpath Road", "Lodhi Road")
    ),
    LocationProfile(
        "Bengaluru", "Karnataka", "560", "80", "IN", "India", ("MG Road", "Indiranagar Main Road")
    ),
    LocationProfile(
        "Hyderabad",
        "Telangana",
        "500",
        "40",
        "IN",
        "India",
        ("Banjara Hills Road", "Hitech City Road"),
    ),
    LocationProfile(
        "Chennai", "Tamil Nadu", "600", "44", "IN", "India", ("Anna Salai", "Velachery Main Road")
    ),
    LocationProfile(
        "Kolkata", "West Bengal", "700", "33", "IN", "India", ("Park Street", "AJC Bose Road")
    ),
    LocationProfile("Pune", "Maharashtra", "411", "20", "IN", "India", ("FC Road", "Baner Road")),
)
