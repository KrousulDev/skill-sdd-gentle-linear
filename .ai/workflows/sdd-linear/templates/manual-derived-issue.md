# Manual Linear Derived Issue Payload

Use this payload ONLY after Engram save succeeds and all 3 Linear creation attempts fail.

1. Parent Linear issue ID: `{{parentLinearIssueId}}`
2. Parent Linear feature/project ID: `{{parentLinearFeatureId}}`
3. Title: `{{title}}`
4. Summary: `{{summary}}`
5. Impact: `{{impact}}`
6. Blocking: `{{blocking}}`
7. Proposed Linear state: `{{proposedLinearState}}`
8. Source change ID: `{{sourceChangeId}}`
9. Engram observation ID: `{{engramObservationId}}`
10. Evidence links: `{{evidenceLinks}}`
11. Operator notes: `{{operatorNotes}}`

## Suggested operator prompt

Create a Linear issue linked to `{{parentLinearIssueId}}` using the ordered payload above. Preserve the Engram observation reference, keep the issue relation to feature/project `{{parentLinearFeatureId}}` when present, and mark the item as manually created from fallback for change `{{sourceChangeId}}`.
