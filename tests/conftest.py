import os
import tempfile


os.environ.setdefault(
    "NIGHTLEDGER_EXECUTION_TOKEN_SECRET",
    "nightledger-default-test-secret-material-32bytes!!",
)
os.environ.setdefault("NIGHTLEDGER_EXECUTION_TOKEN_ACTIVE_KID", "v1")
os.environ.setdefault(
    "NIGHTLEDGER_EXECUTION_REPLAY_DB_PATH",
    os.path.join(tempfile.gettempdir(), "nightledger_test_execution_replay.db"),
)
