"""Domain-specific value providers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from boom_data.generation.seed import SeedManager
from boom_data.schema.models import TypeFamily


class DomainProfile(StrEnum):
    """Use-case profile for semantic value generation."""

    GENERAL = "general"
    FINANCIAL = "financial"
    HEALTHCARE = "healthcare"


class DomainValueProvider(Protocol):
    """Protocol for domain-specific value providers."""

    def value_for(
        self,
        *,
        table_name: str,
        column_name: str,
        type_family: TypeFamily,
        row_index: int,
        seed_manager: SeedManager,
    ) -> Any | None:
        """Return a domain-specific value, or `None` to use the generic fallback."""


@dataclass(frozen=True)
class GeneralValueProvider:
    """Default provider that lets the generic generator handle values."""

    def value_for(
        self,
        *,
        table_name: str,
        column_name: str,
        type_family: TypeFamily,
        row_index: int,
        seed_manager: SeedManager,
    ) -> None:
        return None


@dataclass(frozen=True)
class FinancialValueProvider:
    """Financial and banking semantic values."""

    def value_for(
        self,
        *,
        table_name: str,
        column_name: str,
        type_family: TypeFamily,
        row_index: int,
        seed_manager: SeedManager,
    ) -> Any | None:
        stream = seed_manager.stream("domain", "financial", table_name, column_name, row_index)
        name = column_name.lower()

        if type_family == TypeFamily.NUMERIC:
            if "credit_score" in name:
                return stream.randint(300, 850)
            if any(token in name for token in ("amount", "balance", "limit", "payment")):
                return round(stream.uniform(1, 25_000), 2)

        if type_family not in {TypeFamily.STRING, TypeFamily.ENUM, TypeFamily.UNKNOWN}:
            return None

        if "currency" in name:
            return _choice(stream, ("USD", "EUR", "GBP", "INR", "AED"))
        if "account_type" in name:
            return _choice(stream, ("checking", "savings", "credit_card", "loan", "brokerage"))
        if "transaction_type" in name or name == "type":
            return _choice(stream, ("deposit", "withdrawal", "card_payment", "transfer", "fee"))
        if "status" in name:
            return _choice(stream, ("posted", "pending", "reversed", "failed"))
        if "bank" in name or "institution" in name:
            return _choice(stream, ("Northstar Bank", "Cedar Credit Union", "Metro Trust"))
        if "merchant" in name:
            return _choice(stream, ("Aster Market", "Blue Transit", "Nova Telecom", "Orbit Fuel"))
        if "category" in name:
            return _choice(stream, ("payroll", "groceries", "travel", "utilities", "healthcare"))
        if "routing" in name:
            return f"{stream.randint(10_000_000, 99_999_999)}{stream.randint(0, 9)}"
        if "account_number" in name:
            return f"ACCT{stream.randint(10_000_000, 99_999_999)}"

        return None


@dataclass(frozen=True)
class HealthcareValueProvider:
    """Healthcare and patient semantic values."""

    def value_for(
        self,
        *,
        table_name: str,
        column_name: str,
        type_family: TypeFamily,
        row_index: int,
        seed_manager: SeedManager,
    ) -> Any | None:
        stream = seed_manager.stream("domain", "healthcare", table_name, column_name, row_index)
        name = column_name.lower()

        if type_family == TypeFamily.NUMERIC:
            if "age" in name:
                return stream.randint(1, 96)
            if "heart_rate" in name:
                return stream.randint(55, 115)
            if "systolic" in name:
                return stream.randint(95, 155)
            if "diastolic" in name:
                return stream.randint(60, 98)
            if "height" in name:
                return round(stream.uniform(140, 200), 1)
            if "weight" in name:
                return round(stream.uniform(42, 130), 1)

        if type_family not in {TypeFamily.STRING, TypeFamily.ENUM, TypeFamily.UNKNOWN}:
            return None

        if "mrn" in name or "medical_record" in name or "patient_number" in name:
            return f"MRN{row_index + 1:08d}"
        if "first_name" in name:
            return _choice(stream, ("Avery", "Maya", "Noah", "Priya", "Samir", "Elena"))
        if "last_name" in name:
            return _choice(stream, ("Shah", "Patel", "Rivera", "Chen", "Morgan", "Iyer"))
        if name == "name" or "patient_name" in name:
            return f"Patient {row_index + 1}"
        if "gender" in name or name == "sex":
            return _choice(stream, ("female", "male", "non_binary", "unknown"))
        if "blood_type" in name:
            return _choice(stream, ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"))
        if "diagnosis_code" in name or "icd" in name:
            return _choice(stream, ("E11.9", "I10", "J45.909", "M54.5", "R51.9"))
        if "diagnosis" in name or "condition" in name:
            return _choice(stream, ("hypertension", "asthma", "diabetes", "migraine", "back pain"))
        if "medication" in name:
            return _choice(stream, ("metformin", "atorvastatin", "albuterol", "lisinopril"))
        if "insurance" in name:
            return _choice(stream, ("CareFirst", "HealthBridge", "MediSure", "WellPath"))
        if "status" in name:
            return _choice(stream, ("scheduled", "checked_in", "discharged", "follow_up"))

        return None


def provider_for(domain: DomainProfile) -> DomainValueProvider:
    """Return the configured provider for a domain profile."""

    match domain:
        case DomainProfile.FINANCIAL:
            return FinancialValueProvider()
        case DomainProfile.HEALTHCARE:
            return HealthcareValueProvider()
        case DomainProfile.GENERAL:
            return GeneralValueProvider()


def _choice(stream, values: tuple[Any, ...]) -> Any:
    return values[stream.randrange(len(values))]
