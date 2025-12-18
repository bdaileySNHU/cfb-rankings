# GitHub Issue Templates - Usage Guide

This directory contains issue templates for creating structured GitHub issues for the cfb-rankings project.

## Available Templates

### Story Templates (Epic: Fix CFBD Client Test Failures)

1. **`story-cfbd-01-investigate-api-schema.md`**
   - Investigation story to verify CFBD API schema
   - Use for: STORY-CFBD-01
   - Labels: `investigation`, `tests`, `priority-high`

2. **`story-cfbd-02-fix-test-mocks.md`**
   - Implementation story to fix test mocks
   - Use for: STORY-CFBD-02
   - Labels: `bug`, `tests`, `priority-high`
   - Blocked by: STORY-CFBD-01

## How to Use These Templates

### Method 1: Via GitHub Web Interface (Recommended)

1. Go to: https://github.com/bdaileySNHU/cfb-rankings/issues/new/choose
2. Select the appropriate template from the list
3. Fill in the checkboxes as you complete tasks
4. Click "Submit new issue"

### Method 2: Using GitHub CLI

```bash
# Create Story 1 issue
gh issue create --template story-cfbd-01-investigate-api-schema.md

# Create Story 2 issue
gh issue create --template story-cfbd-02-fix-test-mocks.md
```

### Method 3: Manual Creation

1. Copy the contents of the template file
2. Go to: https://github.com/bdaileySNHU/cfb-rankings/issues/new
3. Paste the template content
4. Update the title and labels manually
5. Submit the issue

## Template Structure

Each template includes:

- **📋 Story Overview**: High-level info (ID, effort, priority, status)
- **🎯 User Story**: Standard format (As a/I want/So that)
- **📝 Context**: Problem statement, goals, integration points
- **✅ Acceptance Criteria**: Checklist of requirements (functional, integration, quality)
- **🔧 Implementation Guide**: Step-by-step technical instructions
- **📊 Definition of Done**: Final completion checklist
- **⚠️ Risk Mitigation**: Risks, mitigation strategies, rollback plans
- **🔗 Related Links**: Documentation, files, and resource links
- **💡 Notes**: Additional context and guidance

## Working with Issue Checklists

GitHub renders `- [ ]` as interactive checkboxes in issues. As you complete tasks:

1. Edit the issue
2. Change `- [ ]` to `- [x]` for completed items
3. Save the issue

Or simply click the checkbox in the rendered issue view!

## Issue Workflow

### Recommended Workflow

1. **Create STORY-CFBD-01 issue first** (investigation)
2. Assign to developer
3. Developer completes investigation and fills in "Investigation Results" section
4. Mark all checkboxes as completed
5. Close STORY-CFBD-01

6. **Create STORY-CFBD-02 issue** (implementation)
7. Reference findings from STORY-CFBD-01
8. Assign to developer
9. Developer implements fixes and checks off tasks
10. Verify all tests pass and CI/CD is green
11. Close STORY-CFBD-02

### Epic Completion

Both stories complete → Epic complete → CI/CD restored to green ✅

## Labels Reference

Recommended labels for these stories:

- `investigation`: For research/discovery work (Story 1)
- `bug`: For fixing issues (Story 2)
- `tests`: Test-related work
- `priority-high`: High priority items
- `epic-cfbd-test-failures`: Groups issues under this epic
- `blocked`: When Story 2 is waiting for Story 1

## Tips

- ✅ Use checkboxes to track progress
- 📝 Fill in "Investigation Results" and "Notes" sections during work
- 🔗 Link related PRs using "Closes #issue-number" in PR description
- 💬 Add comments to issues for updates and findings
- 🏷️ Update labels as status changes (e.g., remove `blocked` when unblocked)

## Questions?

See the full epic documentation at `docs/epic-fix-cfbd-test-failures.md`
