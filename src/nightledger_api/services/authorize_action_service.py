import ast
import json
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from nightledger_api.services.errors import (
    PolicyCatalogVersionMismatchError,
    RuleConfigurationError,
    RuleExpressionError,
    RuleInputError,
)


AuthorizeActionState = Literal["allow", "requires_approval", "deny"]
RuleAction = Literal["allow", "require_approval", "deny"]
_USER_RULES_FILE_ENV = "NIGHTLEDGER_USER_RULES_FILE"
AUTHORIZE_ACTION_CONTRACT_VERSION = "2.0.0"
_POLICY_SET = "nightledger-v2-user-local"


class AuthorizeActionIntent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action: str = Field(min_length=1)


class AuthorizeActionContext(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="allow")

    user_id: str = Field(min_length=1)
    amount: float
    currency: Literal["EUR"]
    transport_decision_hint: AuthorizeActionState | None = None
    policy_catalog_version: str | None = None


class AuthorizeActionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    intent: AuthorizeActionIntent
    context: AuthorizeActionContext


@dataclass(frozen=True)
class RunFacts:
    event_count: int
    has_pending_approval: bool


@dataclass(frozen=True)
class RuleDefinition:
    id: str
    type: str
    applies_to: tuple[str, ...]
    when: str
    action: RuleAction
    reason: str


@dataclass(frozen=True)
class MatchResult:
    rule: RuleDefinition
    outcome: bool


@dataclass(frozen=True)
class LoadedRules:
    rules_by_user: dict[str, list[RuleDefinition]]
    source_path: str
    ruleset_hash: str
    catalog_version: str


class UserRulesRepository:
    def __init__(self) -> None:
        self._cached_path: str | None = None
        self._cached_mtime_ns: int | None = None
        self._cached_loaded: LoadedRules | None = None

    def rules_for_user(self, *, user_id: str) -> list[RuleDefinition]:
        loaded = self._load_rules()
        return loaded.rules_by_user.get(user_id, [])

    def load(self) -> LoadedRules:
        return self._load_rules()

    def _load_rules(self) -> LoadedRules:
        rules_file = os.getenv(_USER_RULES_FILE_ENV)
        if rules_file is None or rules_file.strip() == "":
            raise RuleConfigurationError(
                f"{_USER_RULES_FILE_ENV} is required for authorize_action policy evaluation"
            )

        path = Path(rules_file).expanduser()
        if not path.exists() or not path.is_file():
            raise RuleConfigurationError(
                f"Rule file '{path}' does not exist or is not a file"
            )

        try:
            stat = path.stat()
        except OSError as exc:
            raise RuleConfigurationError(f"Could not stat rule file '{path}': {exc}") from exc

        if (
            self._cached_loaded is not None
            and self._cached_path == str(path)
            and self._cached_mtime_ns == stat.st_mtime_ns
        ):
            return self._cached_loaded

        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuleConfigurationError(f"Could not read rule file '{path}': {exc}") from exc

        try:
            parsed = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise RuleConfigurationError(f"Rule file '{path}' contains invalid YAML: {exc}") from exc

        rules_by_user = _parse_rules_catalog(parsed)
        digest = sha256(raw.encode("utf-8")).hexdigest()
        loaded = LoadedRules(
            rules_by_user=rules_by_user,
            source_path=str(path),
            ruleset_hash=f"sha256:{digest}",
            catalog_version=f"pol_{digest[:12]}",
        )
        self._cached_path = str(path)
        self._cached_mtime_ns = stat.st_mtime_ns
        self._cached_loaded = loaded
        return loaded


class RuleEvaluator:
    _ALLOWED_COMPARE_OPS = (
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.In,
        ast.NotIn,
    )

    def evaluate(
        self,
        *,
        rule: RuleDefinition,
        context: dict[str, Any],
        run: dict[str, Any],
    ) -> bool:
        try:
            node = ast.parse(rule.when, mode="eval")
        except SyntaxError as exc:
            raise RuleExpressionError(
                rule_id=rule.id,
                expression=rule.when,
                message=f"Invalid rule expression syntax: {exc.msg}",
            ) from exc

        self._validate_node(node, rule=rule)

        try:
            value = self._eval(node.body, context=context, run=run)
        except RuleInputError:
            raise
        except Exception as exc:
            raise RuleExpressionError(
                rule_id=rule.id,
                expression=rule.when,
                message=f"Rule expression evaluation failed: {exc}",
            ) from exc

        if not isinstance(value, bool):
            raise RuleExpressionError(
                rule_id=rule.id,
                expression=rule.when,
                message="Rule expression must evaluate to a boolean",
            )
        return value

    def _validate_node(self, node: ast.AST, *, rule: RuleDefinition) -> None:
        allowed_nodes = (
            ast.Expression,
            ast.BoolOp,
            ast.And,
            ast.Or,
            ast.UnaryOp,
            ast.Not,
            ast.Compare,
            ast.Name,
            ast.Load,
            ast.Attribute,
            ast.Constant,
            ast.List,
            ast.Tuple,
        )
        for child in ast.walk(node):
            if isinstance(child, ast.Compare):
                for op in child.ops:
                    if not isinstance(op, self._ALLOWED_COMPARE_OPS):
                        raise RuleExpressionError(
                            rule_id=rule.id,
                            expression=ast.unparse(node) if hasattr(ast, "unparse") else "<expression>",
                            message="Rule expression uses unsupported comparison operator",
                        )
            elif isinstance(child, ast.cmpop):
                continue
            elif not isinstance(child, allowed_nodes):
                raise RuleExpressionError(
                    rule_id=rule.id,
                    expression=ast.unparse(node) if hasattr(ast, "unparse") else "<expression>",
                    message=f"Rule expression uses unsupported syntax: {child.__class__.__name__}",
                )

    def _eval(self, node: ast.AST, *, context: dict[str, Any], run: dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id == "context":
                return context
            if node.id == "run":
                return run
            if node.id == "True":
                return True
            if node.id == "False":
                return False
            if node.id == "None":
                return None
            raise RuleExpressionError(
                rule_id="unknown",
                expression=node.id,
                message=f"Unknown rule symbol '{node.id}'",
            )

        if isinstance(node, ast.Attribute):
            base = self._eval(node.value, context=context, run=run)
            if not isinstance(base, dict):
                raise RuleExpressionError(
                    rule_id="unknown",
                    expression=node.attr,
                    message="Rule attribute access is only supported on context and run objects",
                )
            if node.attr not in base:
                path = _attribute_path(node)
                raise RuleInputError(path=path, message=f"Missing rule input '{path}'")
            return base[node.attr]

        if isinstance(node, ast.List):
            return [self._eval(item, context=context, run=run) for item in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval(item, context=context, run=run) for item in node.elts)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not bool(self._eval(node.operand, context=context, run=run))

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(bool(self._eval(value, context=context, run=run)) for value in node.values)
            if isinstance(node.op, ast.Or):
                return any(bool(self._eval(value, context=context, run=run)) for value in node.values)

        if isinstance(node, ast.Compare):
            left = self._eval(node.left, context=context, run=run)
            for op, comparator in zip(node.ops, node.comparators, strict=False):
                right = self._eval(comparator, context=context, run=run)
                if not _compare_values(left=left, op=op, right=right):
                    return False
                left = right
            return True

        raise RuleExpressionError(
            rule_id="unknown",
            expression=node.__class__.__name__,
            message="Unsupported rule expression",
        )


def evaluate_authorize_action(
    payload: AuthorizeActionRequest,
    *,
    run_facts: RunFacts | None = None,
) -> dict[str, Any]:
    run_facts = run_facts or RunFacts(event_count=0, has_pending_approval=False)
    context = payload.context.model_dump(mode="json", exclude_none=True)
    run = {
        "event_count": run_facts.event_count,
        "has_pending_approval": run_facts.has_pending_approval,
    }

    loaded = _RULES_REPOSITORY.load()
    expected_version = payload.context.policy_catalog_version
    if expected_version is not None and expected_version.strip() and expected_version != loaded.catalog_version:
        raise PolicyCatalogVersionMismatchError(
            expected=expected_version,
            actual=loaded.catalog_version,
        )
    rules = loaded.rules_by_user.get(payload.context.user_id, [])

    matched: list[MatchResult] = []
    for rule in rules:
        if payload.intent.action not in rule.applies_to:
            continue
        outcome = _RULE_EVALUATOR.evaluate(rule=rule, context=context, run=run)
        if outcome:
            matched.append(MatchResult(rule=rule, outcome=True))

    if not matched:
        state: AuthorizeActionState = "allow"
        reason_code = "POLICY_ALLOW_NO_MATCH"
    else:
        winner = _winner_rule(matched)
        state = _decision_state_for_action(winner.action)
        reason_code = _reason_code_for_rule_action(winner.action)

    return {
        "decision_id": _build_deterministic_decision_id(payload=payload),
        "contract_version": AUTHORIZE_ACTION_CONTRACT_VERSION,
        "state": state,
        "reason_code": reason_code,
        "matched_rule_ids": [item.rule.id for item in matched],
        "matched_reasons": [item.rule.reason for item in matched],
        "policy_catalog_version": loaded.catalog_version,
    }


def get_policy_catalog(*, user_id: str | None = None) -> dict[str, Any]:
    loaded = _RULES_REPOSITORY.load()
    selected_users: list[tuple[str, list[RuleDefinition]]]
    if user_id is None:
        selected_users = sorted(loaded.rules_by_user.items(), key=lambda item: item[0])
    else:
        rules = loaded.rules_by_user.get(user_id, [])
        selected_users = [(user_id, rules)]

    users_payload = []
    protected_actions: set[str] = set()
    for uid, rules in selected_users:
        action_map: dict[str, dict[str, Any]] = {}
        for rule in rules:
            fields = sorted(_extract_context_paths(rule.when))
            for action in rule.applies_to:
                protected_actions.add(action)
                entry = action_map.setdefault(
                    action,
                    {
                        "action": action,
                        "rule_ids": [],
                        "required_context_fields": set(),
                    },
                )
                entry["rule_ids"].append(rule.id)
                entry["required_context_fields"].update(fields)
        users_payload.append(
            {
                "user_id": uid,
                "actions": [
                    {
                        "action": action_entry["action"],
                        "rule_ids": action_entry["rule_ids"],
                        "required_context_fields": sorted(action_entry["required_context_fields"]),
                    }
                    for action_entry in sorted(
                        action_map.values(),
                        key=lambda value: str(value["action"]),
                    )
                ],
            }
        )

    return {
        "policy_set": _POLICY_SET,
        "catalog_version": loaded.catalog_version,
        "ruleset_hash": loaded.ruleset_hash,
        "source_path": loaded.source_path,
        "protected_actions": sorted(protected_actions),
        "users": users_payload,
    }


def _build_deterministic_decision_id(*, payload: AuthorizeActionRequest) -> str:
    canonical_payload = {
        "intent": payload.intent.model_dump(mode="json"),
        "context": payload.context.model_dump(mode="json", exclude_none=True),
    }
    fingerprint = sha256(
        json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"dec_{fingerprint[:16]}"


def _winner_rule(matched: list[MatchResult]) -> RuleDefinition:
    best = matched[0].rule
    best_score = _action_priority(best.action)
    for item in matched[1:]:
        score = _action_priority(item.rule.action)
        if score > best_score:
            best = item.rule
            best_score = score
    return best


def _action_priority(action: RuleAction) -> int:
    if action == "deny":
        return 3
    if action == "require_approval":
        return 2
    return 1


def _decision_state_for_action(action: RuleAction) -> AuthorizeActionState:
    if action == "deny":
        return "deny"
    if action == "require_approval":
        return "requires_approval"
    return "allow"


def _reason_code_for_rule_action(action: RuleAction) -> str:
    if action == "deny":
        return "RULE_DENY"
    if action == "require_approval":
        return "RULE_REQUIRE_APPROVAL"
    return "RULE_ALLOW"


def _parse_rules_catalog(raw: Any) -> dict[str, list[RuleDefinition]]:
    if not isinstance(raw, dict):
        raise RuleConfigurationError("Rule file root must be an object")

    users = raw.get("users")
    if not isinstance(users, dict):
        raise RuleConfigurationError("Rule file must define object key 'users'")

    parsed: dict[str, list[RuleDefinition]] = {}
    for user_id, user_payload in users.items():
        if not isinstance(user_id, str) or user_id.strip() == "":
            raise RuleConfigurationError("Rule file contains invalid user id")
        if not isinstance(user_payload, dict):
            raise RuleConfigurationError(f"User '{user_id}' config must be an object")

        rules = user_payload.get("rules")
        if not isinstance(rules, list):
            raise RuleConfigurationError(f"User '{user_id}' rules must be a list")

        parsed_rules: list[RuleDefinition] = []
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise RuleConfigurationError(
                    f"User '{user_id}' rule at index {index} must be an object"
                )
            parsed_rules.append(_parse_rule_definition(user_id=user_id, index=index, rule=rule))

        parsed[user_id.strip()] = parsed_rules

    return parsed


def _parse_rule_definition(*, user_id: str, index: int, rule: dict[str, Any]) -> RuleDefinition:
    rule_id = rule.get("id")
    if not isinstance(rule_id, str) or rule_id.strip() == "":
        raise RuleConfigurationError(
            f"User '{user_id}' rule at index {index} is missing non-empty 'id'"
        )

    rule_type = rule.get("type")
    if not isinstance(rule_type, str) or rule_type.strip() == "":
        raise RuleConfigurationError(f"Rule '{rule_id}' is missing non-empty 'type'")

    applies_to = rule.get("applies_to")
    if not isinstance(applies_to, list) or len(applies_to) == 0:
        raise RuleConfigurationError(f"Rule '{rule_id}' requires non-empty list 'applies_to'")
    applies_to_values = []
    for action in applies_to:
        if not isinstance(action, str) or action.strip() == "":
            raise RuleConfigurationError(
                f"Rule '{rule_id}' contains invalid applies_to action value"
            )
        applies_to_values.append(action.strip())

    when = rule.get("when")
    if not isinstance(when, str) or when.strip() == "":
        raise RuleConfigurationError(f"Rule '{rule_id}' is missing non-empty 'when'")

    action = rule.get("action")
    if action not in {"allow", "require_approval", "deny"}:
        raise RuleConfigurationError(
            f"Rule '{rule_id}' has invalid action '{action}', expected allow|require_approval|deny"
        )

    reason = rule.get("reason")
    if not isinstance(reason, str) or reason.strip() == "":
        raise RuleConfigurationError(f"Rule '{rule_id}' is missing non-empty 'reason'")

    return RuleDefinition(
        id=rule_id.strip(),
        type=rule_type.strip(),
        applies_to=tuple(applies_to_values),
        when=when.strip(),
        action=action,
        reason=reason.strip(),
    )


def _attribute_path(node: ast.Attribute) -> str:
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    parts.reverse()
    return ".".join(parts)


def _compare_values(*, left: Any, op: ast.cmpop, right: Any) -> bool:
    if isinstance(op, ast.Eq):
        return left == right
    if isinstance(op, ast.NotEq):
        return left != right
    if isinstance(op, ast.Gt):
        return left > right
    if isinstance(op, ast.GtE):
        return left >= right
    if isinstance(op, ast.Lt):
        return left < right
    if isinstance(op, ast.LtE):
        return left <= right
    if isinstance(op, ast.In):
        return left in right
    if isinstance(op, ast.NotIn):
        return left not in right
    raise RuleExpressionError(rule_id="unknown", expression="compare", message="Unsupported compare")


def _extract_context_paths(expression: str) -> set[str]:
    try:
        node = ast.parse(expression, mode="eval")
    except SyntaxError:
        return set()
    paths: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Attribute):
            continue
        full = _attribute_path(child)
        if not full.startswith("context."):
            continue
        paths.add(full[len("context.") :])
    return paths


_RULES_REPOSITORY = UserRulesRepository()
_RULE_EVALUATOR = RuleEvaluator()
