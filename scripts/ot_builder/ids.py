"""ID allocation from xeelo-spec explicit map or per-table base."""

from __future__ import annotations

from typing import Any

DEFAULT_BASE = 9000

# Spec category / scalar key → SQL table (identity is per table, site-wide).
CATEGORY_TO_TABLE: dict[str, str] = {
    "fields": "ObjectLine",
    "refObjectLines": "ObjectLine",
    "tabs": "ObjectLineTab",
    "sections": "ObjectLineSection",
    "objectLineOnGrid": "ObjectLineOnGrid",
    "sources": "ObjectLineSource",
    "references": "ObjectLineSource",
    "sourceValues": "ObjectLineSourceValue",
    "sourceRefObjects": "ObjectLineSourceRefObject",
    "lookups": "ObjectLineLookup",
    "lookupValues": "ObjectLineLookupValue",
    "autonumbers": "ObjectLineAutoNumber",
    "templates": "ObjectDefault",
    "objectDefaultLines": "ObjectDefaultLine",
    "objectDefaultAccess": "ObjectDefaultAccess",
    "workflowSteps": "WorkflowStep",
    "workflowStepActions": "WorkflowStepAction",
    "workflowStepAccess": "WorkflowStepAccess",
    "objectActions": "ObjectAction",
    "objectActionParams": "ObjectActionParam",
    "objectActionConditions": "ObjectActionCondition",
    "workflowStepObjectActions": "WorkflowStepObjectAction",
    "updateActions": "ObjectUpdateAction",
    "objectUpdateAccess": "ObjectUpdateAccess",
    "objectUpdateActionConditions": "ObjectUpdateActionCondition",
    "objectUpdateMessages": "ObjectUpdateMessage",
    "objectMessages": "ObjectMessage",
    "objectMessageConditions": "ObjectMessageCondition",
    "roles": "Role",
    "statuses": "RequestStatus",
    "languageTables": "LanguageTable",
}

SCALAR_TO_TABLE: dict[str, str] = {
    "companyId": "Company",
    "objectTypeId": "ObjectType",
    "objectId": "Object",
    "workflowId": "Workflow",
    "objectDefaultId": "ObjectDefault",
}


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _table_for_category(category: str) -> str:
    return CATEGORY_TO_TABLE.get(category, category)


def _table_for_scalar(key: str) -> str:
    return SCALAR_TO_TABLE.get(key, key)


class IdRegistry:
    def __init__(self, spec: dict) -> None:
        ids_cfg = spec.get("ids") or {}
        self._explicit = ids_cfg.get("explicit") or {}
        self._used: dict[str, set[int]] = {}
        self._allocated_scalar: dict[str, int] = {}
        self._allocated: dict[str, dict[str, int]] = {}
        self._counters: dict[str, int] = {}
        self._default_base = DEFAULT_BASE
        self._base_map: dict[str, int] = {}
        raw_base = ids_cfg.get("base", DEFAULT_BASE)
        if isinstance(raw_base, dict):
            for table, val in raw_base.items():
                parsed = _as_int(val)
                if parsed is not None:
                    self._base_map[str(table)] = parsed
        else:
            parsed_default = _as_int(raw_base)
            if parsed_default is not None:
                self._default_base = parsed_default

    def _start(self, table: str) -> int:
        if table in self._counters:
            return self._counters[table]
        if table in self._base_map:
            return self._base_map[table]
        return self._default_base

    def _track(self, table: str, value: int) -> int:
        self._used.setdefault(table, set()).add(value)
        return value

    def _allocate(self, table: str) -> int:
        used = self._used.setdefault(table, set())
        n = self._start(table)
        while True:
            n += 1
            if n not in used:
                used.add(n)
                self._counters[table] = n
                return n

    def _scalar(self, key: str) -> int | None:
        val = self._explicit.get(key)
        if val is None:
            return None
        return int(val)

    def _map(self, category: str, key: str) -> int | None:
        group = self._explicit.get(category)
        if not isinstance(group, dict):
            return None
        val = group.get(key)
        if val is None:
            return None
        return int(val)

    def require_scalar(self, key: str) -> int:
        table = _table_for_scalar(key)
        existing = self._scalar(key)
        if existing is not None:
            return self._track(table, existing)
        cached = self._allocated_scalar.get(key)
        if cached is not None:
            return cached
        value = self._allocate(table)
        self._allocated_scalar[key] = value
        return value

    def require(self, category: str, key: str) -> int:
        table = _table_for_category(category)
        existing = self._map(category, key)
        if existing is not None:
            return self._track(table, existing)
        category_cache = self._allocated.setdefault(category, {})
        cached = category_cache.get(key)
        if cached is not None:
            return cached
        value = self._allocate(table)
        category_cache[key] = value
        return value

    def optional(self, category: str, key: str) -> int | None:
        table = _table_for_category(category)
        existing = self._map(category, key)
        if existing is not None:
            return self._track(table, existing)
        return None

    def get(self, category: str, key: str) -> int | None:
        """Return an already known ID without allocating."""
        existing = self.optional(category, key)
        if existing is not None:
            return existing
        return self._allocated.get(category, {}).get(key)

    def get_scalar(self, key: str) -> int | None:
        """Return an already known scalar ID without allocating."""
        table = _table_for_scalar(key)
        existing = self._scalar(key)
        if existing is not None:
            return self._track(table, existing)
        return self._allocated_scalar.get(key)

    def seed_used(self, table: str, *values: int) -> None:
        used = self._used.setdefault(table, set())
        for value in values:
            used.add(int(value))

    def set_table_start(self, table: str, max_id: int) -> None:
        """Set high-water from byTable unless ids.base already has that table."""
        if table in self._base_map:
            return
        self._counters[table] = max_id


def build_registry(spec: dict) -> IdRegistry:
    registry = IdRegistry(spec)
    explicit = (spec.get("ids") or {}).get("explicit") or {}
    by_table = (spec.get("ids") or {}).get("byTable") or {}
    for table, table_rows in by_table.items():
        if not isinstance(table_rows, dict):
            continue
        parsed_ids: list[int] = []
        for row_id in table_rows.values():
            parsed = _as_int(row_id)
            if parsed is None:
                continue
            registry.seed_used(str(table), parsed)
            parsed_ids.append(parsed)
        if parsed_ids:
            registry.set_table_start(str(table), max(parsed_ids))
    for key, val in explicit.items():
        parsed = _as_int(val)
        if parsed is not None:
            table = SCALAR_TO_TABLE.get(key)
            if table:
                registry.seed_used(table, parsed)
            continue
        if not isinstance(val, dict):
            continue
        table = CATEGORY_TO_TABLE.get(key)
        if not table:
            continue
        for nested in val.values():
            parsed_nested = _as_int(nested)
            if parsed_nested is not None:
                registry.seed_used(table, parsed_nested)
    return registry
