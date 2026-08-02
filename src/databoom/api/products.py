"""Product catalog definitions for the demo dashboard API."""

from __future__ import annotations

from dataclasses import dataclass

from databoom.generation import DomainProfile, OutputFormat


@dataclass(frozen=True)
class ProductPlan:
    """Subscription plan metadata for one product."""

    id: str
    name: str
    price: str
    description: str


@dataclass(frozen=True)
class ProductCatalogEntry:
    """Runnable product module configuration."""

    id: str
    name: str
    family: str
    module: str
    description: str
    domain: DomainProfile
    schema_ddl: str
    default_row_counts: dict[str, int]
    output_formats: tuple[OutputFormat, ...]
    features: tuple[str, ...]
    plans: tuple[ProductPlan, ...]

    @property
    def tables(self) -> tuple[str, ...]:
        """Return generated table names in display order."""

        return tuple(self.default_row_counts)


DEFAULT_PLANS = (
    ProductPlan(
        id="starter",
        name="Starter",
        price="$0 local",
        description="Local demo subscription for development and product validation.",
    ),
    ProductPlan(
        id="team",
        name="Team",
        price="$499/mo",
        description="Planned shared workspace with persisted runs, retention, and access controls.",
    ),
)


PRODUCT_CATALOG: tuple[ProductCatalogEntry, ...] = (
    ProductCatalogEntry(
        id="bank-o-boom",
        name="Bank-O-Boom",
        family="Generator-Boom",
        module="Banking and fintech",
        description="Generate customers, accounts, and transactions for banking-style workflows.",
        domain=DomainProfile.FINANCIAL,
        schema_ddl="""
            CREATE TABLE customers (
                id bigint PRIMARY KEY,
                full_name text NOT NULL,
                email text NOT NULL,
                phone text,
                credit_score integer,
                status text NOT NULL
            );

            CREATE TABLE bank_accounts (
                id bigint PRIMARY KEY,
                customer_id bigint NOT NULL REFERENCES customers(id),
                account_number text NOT NULL,
                account_type text NOT NULL,
                currency text NOT NULL,
                balance numeric NOT NULL,
                status text NOT NULL
            );

            CREATE TABLE transactions (
                id bigint PRIMARY KEY,
                account_id bigint NOT NULL REFERENCES bank_accounts(id),
                merchant_name text,
                category text,
                transaction_type text NOT NULL,
                amount numeric NOT NULL,
                status text NOT NULL
            );
        """,
        default_row_counts={"customers": 8, "bank_accounts": 16, "transactions": 48},
        output_formats=(OutputFormat.CSV, OutputFormat.JSON, OutputFormat.SQL),
        features=(
            "Relationship-safe account and transaction rows.",
            "Financial profile values for balances, merchants, categories, and status.",
            "CSV, JSON, and SQL exports for downstream testing.",
        ),
        plans=DEFAULT_PLANS,
    ),
    ProductCatalogEntry(
        id="health-boom",
        name="Health-Boom",
        family="Generator-Boom",
        module="Healthcare and patient data",
        description="Generate patient, encounter, and vitals data for clinical test workflows.",
        domain=DomainProfile.HEALTHCARE,
        schema_ddl="""
            CREATE TABLE patients (
                id bigint PRIMARY KEY,
                mrn text NOT NULL,
                first_name text NOT NULL,
                last_name text NOT NULL,
                age integer,
                gender text,
                insurance_provider text
            );

            CREATE TABLE encounters (
                id bigint PRIMARY KEY,
                patient_id bigint NOT NULL REFERENCES patients(id),
                diagnosis_code text,
                diagnosis text,
                status text NOT NULL
            );

            CREATE TABLE vitals (
                id bigint PRIMARY KEY,
                encounter_id bigint NOT NULL REFERENCES encounters(id),
                heart_rate integer,
                systolic integer,
                diastolic integer,
                weight numeric,
                status text
            );
        """,
        default_row_counts={"patients": 10, "encounters": 18, "vitals": 36},
        output_formats=(OutputFormat.CSV, OutputFormat.JSON),
        features=(
            "Patient-style values without using real patient records.",
            "Encounter and vitals tables preserve foreign-key integrity.",
            "Useful for demos, QA flows, and analytics prototypes.",
        ),
        plans=DEFAULT_PLANS,
    ),
    ProductCatalogEntry(
        id="boom-commerce",
        name="Boom-Commerce",
        family="Generator-Boom",
        module="Commerce and order data",
        description="Generate customers, products, orders, line items, and payments.",
        domain=DomainProfile.FINANCIAL,
        schema_ddl="""
            CREATE TABLE commerce_customers (
                id bigint PRIMARY KEY,
                full_name text NOT NULL,
                email text NOT NULL,
                status text NOT NULL
            );

            CREATE TABLE products (
                id bigint PRIMARY KEY,
                sku text NOT NULL,
                name text NOT NULL,
                category text,
                price numeric NOT NULL,
                status text NOT NULL
            );

            CREATE TABLE orders (
                id bigint PRIMARY KEY,
                customer_id bigint NOT NULL REFERENCES commerce_customers(id),
                status text NOT NULL,
                total_amount numeric NOT NULL
            );

            CREATE TABLE order_items (
                id bigint PRIMARY KEY,
                order_id bigint NOT NULL REFERENCES orders(id),
                product_id bigint NOT NULL REFERENCES products(id),
                quantity integer NOT NULL,
                amount numeric NOT NULL
            );

            CREATE TABLE payments (
                id bigint PRIMARY KEY,
                order_id bigint NOT NULL REFERENCES orders(id),
                payment_method text NOT NULL,
                payment_amount numeric NOT NULL,
                status text NOT NULL
            );
        """,
        default_row_counts={
            "commerce_customers": 8,
            "products": 12,
            "orders": 20,
            "order_items": 42,
            "payments": 20,
        },
        output_formats=(OutputFormat.CSV, OutputFormat.JSON, OutputFormat.SQL),
        features=(
            "Multi-table ecommerce shape for order lifecycle testing.",
            "Line items and payments preserve order relationships.",
            "Good next-step module before deeper commerce-specific profiles.",
        ),
        plans=DEFAULT_PLANS,
    ),
    ProductCatalogEntry(
        id="schema-boom",
        name="Schema-Boom",
        family="Generator-Boom",
        module="Generic relational data",
        description="Generate typed relational data from a neutral SaaS-style schema.",
        domain=DomainProfile.GENERAL,
        schema_ddl="""
            CREATE TABLE organizations (
                id bigint PRIMARY KEY,
                name text NOT NULL,
                status text NOT NULL
            );

            CREATE TABLE users (
                id bigint PRIMARY KEY,
                organization_id bigint NOT NULL REFERENCES organizations(id),
                name text NOT NULL,
                email text NOT NULL,
                phone text,
                status text NOT NULL
            );

            CREATE TABLE audit_events (
                id bigint PRIMARY KEY,
                user_id bigint NOT NULL REFERENCES users(id),
                event_name text NOT NULL,
                metadata jsonb,
                created_at timestamp
            );
        """,
        default_row_counts={"organizations": 5, "users": 15, "audit_events": 45},
        output_formats=(OutputFormat.CSV, OutputFormat.JSON, OutputFormat.SQL),
        features=(
            "Generic relational fallback for custom app demos.",
            "JSON and timestamp values exercise broader type handling.",
            "Useful as a neutral product sandbox for Schema-Boom.",
        ),
        plans=DEFAULT_PLANS,
    ),
)


def list_products() -> tuple[ProductCatalogEntry, ...]:
    """Return the runnable product catalog."""

    return PRODUCT_CATALOG


def get_product(product_id: str) -> ProductCatalogEntry:
    """Return one product catalog entry by ID."""

    for product in PRODUCT_CATALOG:
        if product.id == product_id:
            return product
    raise KeyError(product_id)
