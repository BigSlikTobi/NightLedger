# Issue #47 Post-Implementation Gap Assessment

Date: 2026-02-18

## 1) What #47 closed

Issue #47 acceptance criteria are implemented at runtime boundary level:

- Direct `purchase.create` executor call without token is blocked.
- Valid token allows execution.
- Tampered token is rejected (`EXECUTION_TOKEN_INVALID`).
- Expired token is rejected (`EXECUTION_TOKEN_EXPIRED`).
- Replayed token is rejected (`EXECUTION_TOKEN_REPLAYED`).
- `allow` decisions now include an execution token.
- Approved decisions can mint execution token via
  `POST /v1/approvals/decisions/{decision_id}/execution-token`.

## 2) Remaining blockers for open issues

### #48 (append-only audit receipts with tamper-evident integrity)

Still open:

- No hash-chain (`hash`/`prev_hash`) integrity proof over event journal.
- No export artifact proving tamper-evidence for entire execution trace.
- Current token signing verifies execution authorization but is not a full
  append-only receipt integrity strategy.

### #49 (deterministic demo proof path)

Still open:

- No packaged single-command script proving full
  block -> approve -> execute flow for fresh clone users.
- README includes endpoint examples, but deterministic demo artifact/log bundle
  for judging is not yet produced.

### #75 (remote MCP transport wrapper)

Still open:

- #47 enforcement currently assumes local API invocation path and does not add
  remote transport wrapper compatibility guarantees.

### #76 (adoption bootstrap + contract versioning)

Still open:

- Execution token contract versioning and migration policy are not yet defined.
- No runtime bootstrap package tying MCP client config + enforcement contract
  versions together.

## 3) Risk notes

- Replay persistence is in-memory only; process restart clears used-token state.
- Secret rotation policy is not implemented yet; rotated secrets can invalidate
  previously minted tokens immediately.
- Legacy `POST /v1/approvals/{event_id}` remains available and can cause
  operational ambiguity if not formally deprecated later.

## 4) Recommended next steps

1. Land #48 hash-chain/export format and include execution token claims in
   exported trace context.
2. Build #49 deterministic demo script with both failure and success path and
   recorded terminal artifact.
3. Define secret rotation + replay persistence strategy (e.g., durable jti
   store) in runtime hardening follow-up.
4. Add explicit deprecation timeline for legacy approval-by-event route.
