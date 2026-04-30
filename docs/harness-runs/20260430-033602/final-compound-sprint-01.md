# Compound - sprint-01 iter 1

## Learned Principle
Investment dashboard UIs must degrade around malformed evidence instead of rendering invalid holdings, alerts, or news as if they were trustworthy.

## Immediate Document Promotion
none

## Promotion Candidates
| Type | Candidate | Reason | Owner |
|---|---|---|---|
| QA guidance | Add a degraded-data verification checklist to frontend QA instructions | This regression only became obvious in browser verification against dirty local data | frontend |
| Backend follow-up | Reseed or clean up local `client-001` holdings and alert data | The UI is safe now, but the demo source data is still broken | backend |

## Entropy Risk
Future contributors may unintentionally trust dirty demo data again unless degraded-state behavior is treated as a first-class path.

## Next Loop Delta
Only continue into backend/data cleanup if the user asks for the demo records themselves to be repaired.

## Direction Pivot
false - the current frontend hardening approach matched the requested scope.
