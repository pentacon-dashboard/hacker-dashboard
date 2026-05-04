"""Client registry and deterministic reference resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Client, ClientAlias, Holding, PortfolioImportBatch, PortfolioSnapshot

ClientResolutionStatus = Literal["resolved", "ambiguous", "not_found", "mismatch"]

_DEFAULT_USER_ID = "pb-demo"
_CLIENT_ID_RE = re.compile(r"\bclient-(\d{3})\b", re.IGNORECASE)
_CLIENT_NUMERIC_RE = re.compile(r"\bclient\s*[-_ ]?\s*(\d{1,3})\b", re.IGNORECASE)
_CLIENT_LABEL_TOKEN_RE = re.compile(
    r"(?P<label>(?:고객|client|customer)\s*[-_:]?\s*[A-Za-z0-9]+)",
    re.IGNORECASE,
)
_LABEL_WITH_NAME_RE = re.compile(
    r"^\s*(?P<label>(?:고객|client|customer)\s*[-_:]?\s*[A-Za-z0-9]+)\s+"
    r"(?P<name>.+?)\s*(?:포트폴리오|요약|분석|리밸런싱|rebalance|summary|report)?\s*$",
    re.IGNORECASE,
)
_REFERENCE_STOPWORDS = (
    "포트폴리오",
    "요약",
    "분석",
    "리밸런싱",
    "보고서",
    "브리핑",
    "portfolio",
    "summary",
    "rebalance",
    "report",
)
_NAME_HONORIFICS = ("님", "씨", "고객")


@dataclass(frozen=True)
class ClientCandidate:
    user_id: str
    client_id: str
    label: str | None
    display_name: str | None
    match_type: str
    matched_value: str
    holdings_count: int = 0
    last_activity_at: datetime | None = None

    @property
    def display_label(self) -> str:
        return self.display_name or self.label or self.client_id


@dataclass(frozen=True)
class ClientResolution:
    status: ClientResolutionStatus
    client_id: str | None = None
    user_id: str | None = None
    label: str | None = None
    display_name: str | None = None
    candidates: tuple[ClientCandidate, ...] = ()
    reason: str = ""

    @property
    def display_label(self) -> str:
        return self.display_name or self.label or self.client_id or "선택 고객"


def normalize_client_label(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[\s_\-.:/()]+", "", value.strip().casefold())


def normalize_client_name(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"\s+", "", value.strip().casefold())
    text = re.sub(r"[\-_:./()]+", "", text)
    changed = True
    while changed:
        changed = False
        for token in _NAME_HONORIFICS:
            if text.endswith(token):
                next_text = text[: -len(token)]
                if len(next_text) >= 2:
                    text = next_text
                    changed = True
            if text.startswith(token):
                next_text = text[len(token) :]
                if len(next_text) >= 2:
                    text = next_text
                    changed = True
    return text


def default_client_label(client_id: str) -> str:
    match = _CLIENT_ID_RE.fullmatch(client_id.strip())
    if match is None:
        return client_id
    index = int(match.group(1)) - 1
    if 0 <= index < 26:
        return f"고객 {chr(ord('A') + index)}"
    return client_id


def client_id_from_legacy_label(label: str) -> str | None:
    compact = label.strip()
    numeric_match = _CLIENT_NUMERIC_RE.fullmatch(compact)
    if numeric_match is not None:
        return f"client-{int(numeric_match.group(1)):03d}"

    label_match = _CLIENT_LABEL_TOKEN_RE.fullmatch(compact)
    token = label_match.group("label") if label_match is not None else compact
    token = re.sub(r"^(고객|client|customer)\s*[-_:]?\s*", "", token, flags=re.IGNORECASE).strip()
    if len(token) == 1 and "A" <= token.upper() <= "Z":
        return f"client-{ord(token.upper()) - ord('A') + 1:03d}"
    return None


def _strip_reference_stopwords(value: str) -> str:
    text = value.strip()
    for stopword in _REFERENCE_STOPWORDS:
        text = re.sub(rf"\b{re.escape(stopword)}\b", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def _client_id_from_text(value: str) -> str | None:
    id_match = _CLIENT_ID_RE.search(value)
    if id_match is not None:
        return f"client-{id_match.group(1)}"
    numeric_match = _CLIENT_NUMERIC_RE.search(value)
    if numeric_match is not None:
        return f"client-{int(numeric_match.group(1)):03d}"
    return None


async def ensure_client_registry(
    db: AsyncSession,
    *,
    user_id: str = _DEFAULT_USER_ID,
    client_id: str,
    label: str | None = None,
    display_name: str | None = None,
    source_names: list[str] | None = None,
) -> Client:
    result = await db.execute(
        select(Client).where(Client.user_id == user_id, Client.client_id == client_id)
    )
    client = result.scalar_one_or_none()
    now = datetime.now()
    resolved_label = label or default_client_label(client_id)
    if client is None:
        client = Client(
            user_id=user_id,
            client_id=client_id,
            label=resolved_label,
            display_name=display_name,
            normalized_label=normalize_client_label(resolved_label),
            normalized_name=normalize_client_name(display_name),
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(client)
        await db.flush()
    else:
        if label and not client.label:
            client.label = label
            client.normalized_label = normalize_client_label(label)
        if display_name:
            if not client.display_name:
                client.display_name = display_name
                client.normalized_name = normalize_client_name(display_name)
            elif normalize_client_name(client.display_name) != normalize_client_name(display_name):
                await add_client_alias(
                    db,
                    user_id=user_id,
                    client_id=client_id,
                    alias_type="upload_source",
                    alias_value=display_name,
                )
        client.updated_at = now

    if resolved_label:
        await add_client_alias(
            db,
            user_id=user_id,
            client_id=client_id,
            alias_type="label",
            alias_value=resolved_label,
        )
    if display_name:
        await add_client_alias(
            db,
            user_id=user_id,
            client_id=client_id,
            alias_type="name",
            alias_value=display_name,
        )
    for source_name in source_names or []:
        if source_name:
            await add_client_alias(
                db,
                user_id=user_id,
                client_id=client_id,
                alias_type="upload_source",
                alias_value=source_name,
            )
    return client


async def add_client_alias(
    db: AsyncSession,
    *,
    user_id: str,
    client_id: str,
    alias_type: str,
    alias_value: str,
) -> None:
    normalized = (
        normalize_client_label(alias_value)
        if alias_type == "label"
        else normalize_client_name(alias_value)
    )
    if not normalized:
        return
    existing = await db.execute(
        select(ClientAlias).where(
            ClientAlias.user_id == user_id,
            ClientAlias.client_id == client_id,
            ClientAlias.alias_type == alias_type,
            ClientAlias.normalized_value == normalized,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(
        ClientAlias(
            user_id=user_id,
            client_id=client_id,
            alias_type=alias_type,
            alias_value=alias_value,
            normalized_value=normalized,
            created_at=datetime.now(),
        )
    )
    await db.flush()


async def sync_clients_from_portfolio(
    db: AsyncSession,
    *,
    user_ids: tuple[str, ...] = (_DEFAULT_USER_ID,),
) -> None:
    client_keys: set[tuple[str, str]] = set()
    for model in (Holding, PortfolioSnapshot, PortfolioImportBatch):
        result = await db.execute(
            select(model.user_id, model.client_id)
            .where(model.user_id.in_(user_ids))
            .group_by(model.user_id, model.client_id)
        )
        client_keys.update((str(user_id), str(client_id)) for user_id, client_id in result.all())

    for user_id, client_id in sorted(client_keys):
        await ensure_client_registry(
            db,
            user_id=user_id,
            client_id=client_id,
            label=default_client_label(client_id),
        )
    await db.flush()


async def resolve_client_reference(
    db: AsyncSession,
    reference: str,
    *,
    user_ids: tuple[str, ...] = (_DEFAULT_USER_ID,),
    sync_from_portfolio: bool = True,
) -> ClientResolution:
    cleaned = _strip_reference_stopwords(reference)
    if sync_from_portfolio:
        await sync_clients_from_portfolio(db, user_ids=user_ids)

    explicit_client_id = _client_id_from_text(cleaned)
    if explicit_client_id is not None:
        candidate = await _candidate_for_client_id(
            db,
            client_id=explicit_client_id,
            user_ids=user_ids,
            match_type="client_id",
            matched_value=explicit_client_id,
        )
        return _resolved(candidate)

    label_name_match = _LABEL_WITH_NAME_RE.match(cleaned)
    if label_name_match is not None:
        label_ref = label_name_match.group("label")
        name_ref = _strip_reference_stopwords(label_name_match.group("name"))
        label_matches = await _match_clients(
            db,
            label_ref,
            user_ids=user_ids,
            kind="label",
        )
        name_matches = await _match_clients(
            db,
            name_ref,
            user_ids=user_ids,
            kind="name",
        )
        if name_matches and label_matches:
            if len(name_matches) == 1 and len(label_matches) == 1:
                if name_matches[0].client_id == label_matches[0].client_id:
                    return _resolved(name_matches[0])
                return ClientResolution(
                    status="mismatch",
                    candidates=tuple(_sort_candidates([*name_matches, *label_matches])),
                    reason="label_and_name_point_to_different_clients",
                )
            return ClientResolution(
                status="ambiguous",
                candidates=tuple(_sort_candidates([*name_matches, *label_matches])),
                reason="label_or_name_ambiguous",
            )
        if name_matches:
            return _from_matches(name_matches, reason="name_match")
        if label_matches:
            return _from_matches(label_matches, reason="label_match")

    name_matches = await _match_clients(db, cleaned, user_ids=user_ids, kind="name")
    if name_matches:
        return _from_matches(name_matches, reason="name_match")

    label_matches = await _match_clients(db, cleaned, user_ids=user_ids, kind="label")
    if label_matches:
        return _from_matches(label_matches, reason="label_match")

    legacy_client_id = client_id_from_legacy_label(cleaned)
    if legacy_client_id is not None:
        candidate = await _candidate_for_client_id(
            db,
            client_id=legacy_client_id,
            user_ids=user_ids,
            match_type="legacy_label",
            matched_value=cleaned,
        )
        return _resolved(candidate)

    return ClientResolution(status="not_found", reason="client_reference_not_found")


async def _candidate_for_client_id(
    db: AsyncSession,
    *,
    client_id: str,
    user_ids: tuple[str, ...],
    match_type: str,
    matched_value: str,
) -> ClientCandidate:
    result = await db.execute(
        select(Client)
        .where(Client.user_id.in_(user_ids), Client.client_id == client_id)
        .order_by(Client.user_id)
        .limit(1)
    )
    client = result.scalar_one_or_none()
    user_id = client.user_id if client is not None else user_ids[0]
    stats = await _client_stats(db, user_id=user_id, client_id=client_id)
    return ClientCandidate(
        user_id=user_id,
        client_id=client_id,
        label=client.label if client is not None else default_client_label(client_id),
        display_name=client.display_name if client is not None else None,
        match_type=match_type,
        matched_value=matched_value,
        holdings_count=stats[0],
        last_activity_at=stats[1],
    )


async def _match_clients(
    db: AsyncSession,
    reference: str,
    *,
    user_ids: tuple[str, ...],
    kind: Literal["name", "label"],
) -> list[ClientCandidate]:
    normalized_reference = (
        normalize_client_label(reference) if kind == "label" else normalize_client_name(reference)
    )
    if not normalized_reference:
        return []

    client_result = await db.execute(select(Client).where(Client.user_id.in_(user_ids)))
    clients = list(client_result.scalars().all())
    alias_result = await db.execute(select(ClientAlias).where(ClientAlias.user_id.in_(user_ids)))
    aliases = list(alias_result.scalars().all())

    by_key: dict[tuple[str, str], ClientCandidate] = {}

    def accepts(candidate_normalized: str) -> bool:
        return bool(candidate_normalized) and candidate_normalized == normalized_reference

    for client in clients:
        if kind == "name":
            matched = client.display_name or ""
            candidate_normalized = client.normalized_name or normalize_client_name(matched)
            match_type = "name"
        else:
            matched = client.label or ""
            candidate_normalized = client.normalized_label or normalize_client_label(matched)
            match_type = "label"
        if accepts(candidate_normalized):
            by_key[(client.user_id, client.client_id)] = await _candidate_from_client(
                db,
                client,
                match_type=match_type,
                matched_value=matched,
            )

    allowed_alias_types = {"name", "manual", "upload_source"} if kind == "name" else {"label"}
    for alias in aliases:
        if alias.alias_type not in allowed_alias_types:
            continue
        if not accepts(alias.normalized_value):
            continue
        result = await db.execute(
            select(Client).where(
                Client.user_id == alias.user_id,
                Client.client_id == alias.client_id,
            )
        )
        client = result.scalar_one_or_none()
        if client is None:
            client = Client(
                user_id=alias.user_id,
                client_id=alias.client_id,
                label=default_client_label(alias.client_id),
                display_name=None,
            )
        by_key[(alias.user_id, alias.client_id)] = await _candidate_from_client(
            db,
            client,
            match_type=alias.alias_type,
            matched_value=alias.alias_value,
        )

    return _sort_candidates(list(by_key.values()))


async def _candidate_from_client(
    db: AsyncSession,
    client: Client,
    *,
    match_type: str,
    matched_value: str,
) -> ClientCandidate:
    stats = await _client_stats(db, user_id=client.user_id, client_id=client.client_id)
    return ClientCandidate(
        user_id=client.user_id,
        client_id=client.client_id,
        label=client.label,
        display_name=client.display_name,
        match_type=match_type,
        matched_value=matched_value,
        holdings_count=stats[0],
        last_activity_at=stats[1],
    )


async def _client_stats(
    db: AsyncSession,
    *,
    user_id: str,
    client_id: str,
) -> tuple[int, datetime | None]:
    count_result = await db.execute(
        select(func.count(Holding.id)).where(
            Holding.user_id == user_id,
            Holding.client_id == client_id,
        )
    )
    holdings_count = int(count_result.scalar_one() or 0)

    last_values: list[datetime] = []
    for column, model in (
        (Holding.updated_at, Holding),
        (PortfolioImportBatch.updated_at, PortfolioImportBatch),
        (PortfolioSnapshot.created_at, PortfolioSnapshot),
    ):
        result = await db.execute(
            select(func.max(column)).where(model.user_id == user_id, model.client_id == client_id)
        )
        value = result.scalar_one_or_none()
        if isinstance(value, datetime):
            last_values.append(value)
    return holdings_count, max(last_values) if last_values else None


def _sort_candidates(candidates: list[ClientCandidate]) -> list[ClientCandidate]:
    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.last_activity_at is None,
            -(candidate.last_activity_at.timestamp() if candidate.last_activity_at else 0),
            -candidate.holdings_count,
            candidate.client_id,
        ),
    )


def _from_matches(matches: list[ClientCandidate], *, reason: str) -> ClientResolution:
    sorted_matches = _sort_candidates(matches)
    if len(sorted_matches) == 1:
        return _resolved(sorted_matches[0], reason=reason)
    return ClientResolution(
        status="ambiguous",
        candidates=tuple(sorted_matches),
        reason=reason,
    )


def _resolved(candidate: ClientCandidate, *, reason: str = "resolved") -> ClientResolution:
    return ClientResolution(
        status="resolved",
        client_id=candidate.client_id,
        user_id=candidate.user_id,
        label=candidate.label,
        display_name=candidate.display_name,
        candidates=(candidate,),
        reason=reason,
    )
