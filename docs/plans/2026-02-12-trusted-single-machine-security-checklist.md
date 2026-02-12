# Trusted Single-Machine Security Baseline Checklist

> **Context:** This checklist assumes Tascade runs in a trusted, non-public, single-machine environment.

## 1) Network & Exposure

- [ ] Bind backend to loopback only (`127.0.0.1`) and do not expose it on `0.0.0.0`.
- [ ] Confirm no public ingress, reverse proxy exposure, or router port-forwarding exists.
- [ ] Keep MCP usage local-only (stdio/local process), not network-exposed.
- [ ] Verify host firewall blocks inbound access except explicitly required local ports.

## 2) Authentication & Authorization

- [ ] Ensure `TASCADE_AUTH_DISABLED` is unset (or `0`) for all non-test runtime usage.
- [ ] Create separate API keys per role/use-case (planner/agent/reviewer/operator/admin); avoid sharing one key.
- [ ] Keep admin-scoped keys limited and short-lived where possible.
- [ ] Revoke unused keys regularly via `/v1/api-keys/{key_id}/revoke`.
- [ ] Treat `force` transitions as privileged operational actions only.

## 3) Secrets Handling

- [ ] Store secrets only in local environment files with strict file permissions (`chmod 600`).
- [ ] Do not commit `.env` or any file containing API keys.
- [ ] If using the web UI with `VITE_API_TOKEN`, ensure machine profile is single-user and trusted.
- [ ] Rotate keys immediately if copied into logs, shell history, or chat.

## 4) Host & Runtime Hardening

- [ ] Run the app under a non-admin OS account.
- [ ] Keep OS, Python, Node, and package managers updated with security patches.
- [ ] Keep project directory permissions limited to trusted local users.
- [ ] Prefer PostgreSQL over SQLite for stronger operational controls if long-running.

## 5) Application Safety Controls

- [ ] Enforce reasonable query caps (for example `limit <= 500`) on list/read-heavy endpoints.
- [ ] Monitor and review use of `implemented -> integrated` transitions for governance integrity.
- [ ] Keep static serving rooted to built assets only (`web/dist`) and avoid extra file mounts.
- [ ] Keep migrations directory controlled and writable only by trusted maintainers.

## 6) Verification & Auditing

- [ ] Run backend tests: `pytest -q`.
- [ ] Run frontend tests: `cd web && npm run test`.
- [ ] Run dependency checks periodically:
  - `cd web && npm audit`
  - `uvx --with pip-audit pip-audit`
- [ ] Review event logs for auth denials and unusual state transition activity.

## 7) Operational Hygiene

- [ ] Create periodic DB backups and test restore at least once.
- [ ] Define a local incident process: revoke keys, stop service, rotate secrets, restore known-good state.
- [ ] Re-check this baseline after any architecture/auth/deployment change.

## Quick Weekly Cadence

- [ ] Weekly: dependency audits + unused key revocation.
- [ ] Bi-weekly: OS/runtime patching.
- [ ] Monthly: backup restore drill + permissions review.
