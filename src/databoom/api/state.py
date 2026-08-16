"""State storage for API sessions, subscriptions, and generation runs."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    delete,
    insert,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from databoom.api.models import DemoUserResponse, GenerationRunResponse, SubscriptionResponse
from databoom.api.workspaces import (
    WorkspaceSource,
    default_workspace_sources,
    workspace_source_from_payload,
    workspace_source_to_payload,
)
from databoom.core.config import Settings

LOGGER = logging.getLogger(__name__)

metadata = MetaData()

sessions_table = Table(
    "databoom_sessions",
    metadata,
    Column("token", String(255), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

subscriptions_table = Table(
    "databoom_subscriptions",
    metadata,
    Column("subscription_id", String(255), primary_key=True),
    Column("user_email", String(320), nullable=False, index=True),
    Column("product_id", String(120), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_email", "product_id", name="uq_databoom_subscription_user_product"),
)

runs_table = Table(
    "databoom_runs",
    metadata,
    Column("run_id", String(64), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, index=True),
)

workspace_sources_table = Table(
    "databoom_workspace_sources",
    metadata,
    Column("source_id", String(120), primary_key=True),
    Column("product_id", String(120), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


class StateStore(Protocol):
    """Persistence boundary for API state."""

    def save_session(self, token: str, user: DemoUserResponse) -> None:
        """Persist an authenticated session."""

    def get_session(self, token: str) -> DemoUserResponse | None:
        """Return a session user by token."""

    def save_subscription(self, subscription: SubscriptionResponse) -> None:
        """Persist or replace a subscription."""

    def list_subscriptions(self, user_email: str) -> tuple[SubscriptionResponse, ...]:
        """List subscriptions for one user."""

    def get_subscription(self, user_email: str, product_id: str) -> SubscriptionResponse | None:
        """Return one subscription by user and product."""

    def save_run(self, run: GenerationRunResponse) -> None:
        """Persist a generation run."""

    def list_runs(self) -> tuple[GenerationRunResponse, ...]:
        """List known generation runs."""

    def get_run(self, run_id: str) -> GenerationRunResponse | None:
        """Return one generation run by ID."""

    def save_workspace_source(self, source: WorkspaceSource) -> None:
        """Persist or replace a workspace source."""

    def list_workspace_sources(self, product_id: str | None = None) -> tuple[WorkspaceSource, ...]:
        """List available workspace sources."""

    def get_workspace_source(self, source_id: str) -> WorkspaceSource | None:
        """Return one workspace source by ID."""


class MemoryStateStore:
    """In-process state store for tests and fallback local development."""

    def __init__(self) -> None:
        self._sessions: dict[str, DemoUserResponse] = {}
        self._subscriptions: dict[str, dict[str, SubscriptionResponse]] = {}
        self._runs: dict[str, GenerationRunResponse] = {}
        self._workspace_sources: dict[str, WorkspaceSource] = {
            source.id: source for source in default_workspace_sources()
        }

    def save_session(self, token: str, user: DemoUserResponse) -> None:
        self._sessions[token] = user

    def get_session(self, token: str) -> DemoUserResponse | None:
        return self._sessions.get(token)

    def save_subscription(self, subscription: SubscriptionResponse) -> None:
        self._subscriptions.setdefault(subscription.user_email, {})[
            subscription.product_id
        ] = subscription

    def list_subscriptions(self, user_email: str) -> tuple[SubscriptionResponse, ...]:
        return tuple(self._subscriptions.get(user_email, {}).values())

    def get_subscription(self, user_email: str, product_id: str) -> SubscriptionResponse | None:
        return self._subscriptions.get(user_email, {}).get(product_id)

    def save_run(self, run: GenerationRunResponse) -> None:
        self._runs[run.run_id] = run

    def list_runs(self) -> tuple[GenerationRunResponse, ...]:
        return tuple(self._runs.values())

    def get_run(self, run_id: str) -> GenerationRunResponse | None:
        return self._runs.get(run_id)

    def save_workspace_source(self, source: WorkspaceSource) -> None:
        self._workspace_sources[source.id] = source

    def list_workspace_sources(self, product_id: str | None = None) -> tuple[WorkspaceSource, ...]:
        sources = tuple(self._workspace_sources.values())
        if product_id is None:
            return sources
        return tuple(source for source in sources if source.product_id == product_id)

    def get_workspace_source(self, source_id: str) -> WorkspaceSource | None:
        return self._workspace_sources.get(source_id)


class SQLAlchemyStateStore:
    """SQL-backed state store used by the Dockerized API."""

    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True, future=True)
        metadata.create_all(self.engine)
        self._seed_workspace_sources()

    def save_session(self, token: str, user: DemoUserResponse) -> None:
        payload = user.model_dump(mode="json")
        with self.engine.begin() as connection:
            connection.execute(delete(sessions_table).where(sessions_table.c.token == token))
            connection.execute(
                insert(sessions_table).values(
                    token=token,
                    payload=payload,
                    updated_at=datetime.now(UTC),
                )
            )

    def get_session(self, token: str) -> DemoUserResponse | None:
        with self.engine.begin() as connection:
            payload = connection.execute(
                select(sessions_table.c.payload).where(sessions_table.c.token == token)
            ).scalar_one_or_none()
        return DemoUserResponse.model_validate(payload) if payload else None

    def save_subscription(self, subscription: SubscriptionResponse) -> None:
        payload = subscription.model_dump(mode="json")
        with self.engine.begin() as connection:
            connection.execute(
                delete(subscriptions_table).where(
                    subscriptions_table.c.user_email == subscription.user_email,
                    subscriptions_table.c.product_id == subscription.product_id,
                )
            )
            connection.execute(
                insert(subscriptions_table).values(
                    subscription_id=subscription.subscription_id,
                    user_email=subscription.user_email,
                    product_id=subscription.product_id,
                    payload=payload,
                    created_at=subscription.created_at,
                )
            )

    def list_subscriptions(self, user_email: str) -> tuple[SubscriptionResponse, ...]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(subscriptions_table.c.payload)
                .where(subscriptions_table.c.user_email == user_email)
                .order_by(subscriptions_table.c.created_at)
            )
            return tuple(_parse_subscriptions(row[0] for row in rows))

    def get_subscription(self, user_email: str, product_id: str) -> SubscriptionResponse | None:
        with self.engine.begin() as connection:
            payload = connection.execute(
                select(subscriptions_table.c.payload).where(
                    subscriptions_table.c.user_email == user_email,
                    subscriptions_table.c.product_id == product_id,
                )
            ).scalar_one_or_none()
        return SubscriptionResponse.model_validate(payload) if payload else None

    def save_run(self, run: GenerationRunResponse) -> None:
        payload = run.model_dump(mode="json")
        with self.engine.begin() as connection:
            connection.execute(delete(runs_table).where(runs_table.c.run_id == run.run_id))
            connection.execute(
                insert(runs_table).values(
                    run_id=run.run_id,
                    payload=payload,
                    created_at=run.created_at,
                )
            )

    def list_runs(self) -> tuple[GenerationRunResponse, ...]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(runs_table.c.payload).order_by(runs_table.c.created_at)
            )
            return tuple(_parse_runs(row[0] for row in rows))

    def get_run(self, run_id: str) -> GenerationRunResponse | None:
        with self.engine.begin() as connection:
            payload = connection.execute(
                select(runs_table.c.payload).where(runs_table.c.run_id == run_id)
            ).scalar_one_or_none()
        return GenerationRunResponse.model_validate(payload) if payload else None

    def save_workspace_source(self, source: WorkspaceSource) -> None:
        payload = workspace_source_to_payload(source)
        with self.engine.begin() as connection:
            connection.execute(
                delete(workspace_sources_table).where(
                    workspace_sources_table.c.source_id == source.id
                )
            )
            connection.execute(
                insert(workspace_sources_table).values(
                    source_id=source.id,
                    product_id=source.product_id,
                    payload=payload,
                    updated_at=datetime.now(UTC),
                )
            )

    def list_workspace_sources(self, product_id: str | None = None) -> tuple[WorkspaceSource, ...]:
        query = select(workspace_sources_table.c.payload).order_by(
            workspace_sources_table.c.product_id,
            workspace_sources_table.c.source_id,
        )
        if product_id is not None:
            query = query.where(workspace_sources_table.c.product_id == product_id)
        with self.engine.begin() as connection:
            rows = connection.execute(query)
            return tuple(workspace_source_from_payload(row[0]) for row in rows)

    def get_workspace_source(self, source_id: str) -> WorkspaceSource | None:
        with self.engine.begin() as connection:
            payload = connection.execute(
                select(workspace_sources_table.c.payload).where(
                    workspace_sources_table.c.source_id == source_id
                )
            ).scalar_one_or_none()
        return workspace_source_from_payload(payload) if payload else None

    def _seed_workspace_sources(self) -> None:
        with self.engine.begin() as connection:
            existing_source_id = connection.execute(
                select(workspace_sources_table.c.source_id).limit(1)
            ).scalar_one_or_none()
            if existing_source_id is not None:
                return
            for source in default_workspace_sources():
                connection.execute(
                    insert(workspace_sources_table).values(
                        source_id=source.id,
                        product_id=source.product_id,
                        payload=workspace_source_to_payload(source),
                        updated_at=datetime.now(UTC),
                    )
                )


def create_state_store(settings: Settings) -> StateStore:
    """Create the best available state store for this runtime."""

    if settings.environment == "test":
        return MemoryStateStore()

    try:
        return SQLAlchemyStateStore(settings.database_url)
    except SQLAlchemyError:
        if settings.environment == "docker":
            raise
        LOGGER.warning("Falling back to in-memory API state store", exc_info=True)
        return MemoryStateStore()


def _parse_subscriptions(payloads: Iterable[object]) -> Iterable[SubscriptionResponse]:
    for payload in payloads:
        yield SubscriptionResponse.model_validate(payload)


def _parse_runs(payloads: Iterable[object]) -> Iterable[GenerationRunResponse]:
    for payload in payloads:
        yield GenerationRunResponse.model_validate(payload)
