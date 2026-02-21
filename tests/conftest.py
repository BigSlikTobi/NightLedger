import os
import tempfile

import pytest


os.environ.setdefault(
    "NIGHTLEDGER_EXECUTION_TOKEN_SECRET",
    "nightledger-default-test-secret-material-32bytes!!",
)
os.environ.setdefault("NIGHTLEDGER_EXECUTION_TOKEN_ACTIVE_KID", "v1")
os.environ.setdefault(
    "NIGHTLEDGER_EXECUTION_REPLAY_DB_PATH",
    os.path.join(tempfile.gettempdir(), "nightledger_test_execution_replay.db"),
)


@pytest.fixture(autouse=True)
def configure_authorize_action_user_rules(tmp_path, monkeypatch) -> None:
    rules_file = tmp_path / "user_rules.yaml"
    rules_file.write_text(
        (
            "users:\n"
            "  user_test:\n"
            "    rules:\n"
            "      - id: amount_threshold\n"
            "        type: guardrail\n"
            "        applies_to: [\"purchase.create\", \"invoice.pay\"]\n"
            "        when: \"context.amount > 100\"\n"
            "        action: \"require_approval\"\n"
            "        reason: \"Amount exceeds threshold\"\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NIGHTLEDGER_USER_RULES_FILE", str(rules_file))
