from databoom.generation import (
    DomainProfile,
    LocaleProfile,
    SeedManager,
    ValueGenerator,
    locale_from_intent,
)
from databoom.generation.plan import ColumnPlan, ColumnStrategy
from databoom.schema import TypeFamily


def column(name: str, family: TypeFamily = TypeFamily.STRING) -> ColumnPlan:
    return ColumnPlan(
        name=name,
        strategy=ColumnStrategy.GENERATED,
        type_family=family,
        nullable=False,
    )


def test_financial_profile_generates_domain_specific_values() -> None:
    generator = ValueGenerator(SeedManager(42), domain=DomainProfile.FINANCIAL)

    assert generator.value_for("public.accounts", column("currency"), 0) in {
        "USD",
        "EUR",
        "GBP",
        "INR",
        "AED",
    }
    assert generator.value_for("public.accounts", column("account_type"), 0) in {
        "checking",
        "savings",
        "credit_card",
        "loan",
        "brokerage",
    }
    assert isinstance(
        generator.value_for("public.transactions", column("amount", TypeFamily.NUMERIC), 0),
        float,
    )


def test_healthcare_profile_generates_domain_specific_values() -> None:
    generator = ValueGenerator(SeedManager(42), domain=DomainProfile.HEALTHCARE)

    assert str(
        generator.value_for("public.patients", column("medical_record_number"), 4)
    ).startswith("MRN")
    assert generator.value_for("public.patients", column("blood_type"), 0) in {
        "A+",
        "A-",
        "B+",
        "B-",
        "AB+",
        "AB-",
        "O+",
        "O-",
    }
    assert isinstance(
        generator.value_for("public.vitals", column("heart_rate", TypeFamily.NUMERIC), 0),
        int,
    )


def test_generation_plan_carries_domain_profile() -> None:
    from databoom.generation import create_generation_plan
    from databoom.ingest import parse_postgres_ddl

    database = parse_postgres_ddl("CREATE TABLE accounts (id bigint PRIMARY KEY);")
    plan = create_generation_plan(database, domain=DomainProfile.FINANCIAL)

    assert plan.domain == DomainProfile.FINANCIAL


def test_locale_is_inferred_from_explicit_country_or_city_language() -> None:
    assert locale_from_intent("Generate Indian customers in Mumbai") == LocaleProfile.EN_IN
    assert locale_from_intent("Generate customers in the United States") == LocaleProfile.EN_US
    assert locale_from_intent("Generate customers") == LocaleProfile.EN_US
