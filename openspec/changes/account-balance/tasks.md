# Account Balance Feature — Tasks

## Implementation Checklist

- [ ] Create OpenSpec spec: `openspec/specs/account_balance/spec.md`
- [ ] Create ADR: `docs/decisions/002-account-balance.md`
- [ ] Create OpenSpec change proposal: `openspec/changes/account-balance/proposal.md`
- [ ] Generate Alembic migration for `account_balances` table
- [ ] Create `features/account_balance/` directory
- [ ] Create `features/account_balance/__init__.py`
- [ ] Create `features/account_balance/models.py` with `AccountBalance` model
- [ ] Create `features/account_balance/service.py` with `get_balance()` and `upsert_balance()`
- [ ] Update `MovementsService._get_last_balance()` to read from `AccountBalance`
- [ ] Update `MovementsService.upload()` to call `upsert_balance()` after commit
- [ ] Add tests for account_balance integration
- [ ] Run `make checks`
- [ ] Verify end-to-end with real file
