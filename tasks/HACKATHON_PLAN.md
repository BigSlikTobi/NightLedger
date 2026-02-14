# Hackathon Plan (Tobi + Deborabotter)

## Cadence
- Two sync points per day (midday, evening)
- Merge to main only with passing local checks

## Lane Split

### Tobi — UI Lane
- [ ] Timeline view for journal entries
- [ ] Pending approval card + approve/reject controls
- [ ] Run detail view (entry + evidence links)

### Deborabotter — Runtime Lane
- [ ] Event schema implementation
- [ ] Event ingestion + storage (initially file or sqlite)
- [ ] Approval gate endpoints + state transitions
- [ ] Journal render function (event -> readable narrative)

## Integration Tasks
- [ ] Connect UI to API endpoints
- [ ] Validate demo flow end-to-end
- [ ] Record demo script in `docs/DEMO_SCRIPT.md`

## Day 2 Target
A working vertical slice: one run, one approval request, one approval resolution.
