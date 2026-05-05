# UI Style Guide

## Product Feel

The platform should feel like a premium health analytics workspace:

- calm
- trustworthy
- professional
- readable
- field-friendly
- executive-ready

The UI should help both field assessors and management reviewers work quickly without visual clutter.

## Color Palette

- Primary dark navy: `#0B1F33`
- Deep blue: `#102A43`
- Teal: `#00A6A6`
- Cyan: `#37D5D6`
- Soft background: `#F5F7FA`
- Surface white: `#FFFFFF`
- Text dark: `#1F2937`
- Muted text: `#64748B`
- Border soft: `#D8E1EB`
- Success: `#10B981`
- Warning: `#F59E0B`
- Danger: `#EF4444`

## Typography

- Headings: bold, clean, concise
- Body text: highly legible at 14px to 16px
- Metric numbers: large and strong
- Metadata and helper text: smaller but still readable

Suggested hierarchy:

- Page title: 28px to 32px
- Section title: 18px to 22px
- Card metric: 28px to 36px
- Body: 14px to 16px
- Fine print: 12px to 13px

## Layout Principles

- Rounded `2xl` cards throughout
- Soft shadows instead of harsh panels
- Strong spacing and clear grouping
- Keep primary actions visible without crowding
- Prefer readable cards and tables over dense dashboards

## Navigation

- Sidebar should stay stable and uncluttered
- Use concise route labels with relevant Lucide icons
- Active route should be obvious but elegant
- Topbar should show:
  - page title
  - user identity
  - online/offline state
  - pending sync summary

## Card Pattern

- White or lightly tinted background
- Soft border or shadow
- Generous padding
- Short subtitle where needed
- Metric cards should use one strong number and one supporting line

## Table Pattern

- Subtle separators
- Calm header styling
- Numeric columns aligned consistently
- Status columns use badges
- Dense tables should still read well on smaller laptops
- Mobile fallback may use stacked blocks or horizontal scroll

## Form Pattern

- Always-visible labels
- Rounded inputs with clear focus rings
- Concise validation text near the field
- Group related fields inside cards
- Use helper text for ambiguous data entry or report/privacy controls

## Status Badge System

### Sync and connectivity

- `ONLINE` -> success/teal
- `OFFLINE` -> warning/amber
- `DRAFT_SAVED_LOCALLY` -> info
- `PENDING_SYNC` -> warning/info
- `SYNCING` -> info
- `SYNCED` -> success
- `SYNC_FAILED` -> danger
- `RELOGIN_REQUIRED` -> warning

### Workspace mode

- `EDIT` -> neutral or teal informational badge
- `READ_ONLY` -> navy or muted informational badge

### Comparison severity

- `EXACT` -> green
- `MINOR` -> yellow
- `MODERATE` -> orange
- `MAJOR` -> red
- `CRITICAL` -> deep red
- `MISSING` -> gray
- `NOT_APPLICABLE` -> muted blue/gray

### Corrective action status

- `OPEN` -> warning
- `IN_PROGRESS` -> info
- `RESOLVED` -> teal
- `VERIFIED` -> success
- `CLOSED` -> muted neutral
- `OVERDUE` -> danger
- `CANCELLED` -> muted neutral

### Report status

- `DRAFT` -> muted
- `GENERATED` -> info
- `REVIEWED` -> warning/info
- `APPROVED` -> success
- `EXPORTED` -> success
- `ARCHIVED` -> muted

## Workspace UI Pattern

The assessor workspace should prioritize clarity under field conditions.

- Sticky or high-visibility summary card at the top
- Clear display of:
  - facility
  - round
  - reporting period
  - deadline
  - status
- Main assessment table should show:
  - indicator
  - HMIS code
  - source register
  - register value
  - HMIS 105 value
  - DHIS2 value
  - percentage difference
  - flag
- DHIS2 value is read-only and visibly distinct from editable cells
- Do not show a separate technical DHIS2 side panel in the field workspace
- Show one simple DHIS2 availability banner when system values cannot be pulled
- Keep one general facility assessment comment below the table instead of per-row comments in the main grid
- Place the source document checklist below the assessment values as a compact section
- Read-only review mode must disable fields visibly rather than hide them
- Top summary should show Team Lead, Team Members, DHIS2 pull status, and sync status
- Hide or disable final submission when the current user does not have `can_submit`
- Explain disabled submit action with: `Only the Team Lead can send this assessment.`
- Use `Send to Manager` as the field-team final submission label
- Use one draft sync action for assessor-entered data. DHIS2 value refresh belongs to manager pre-sync/review workflows only.

## DHIS2 Search and Import UI Pattern

Facility and data element setup should make the DHIS2 source obvious.

- Settings must show a Manager-only DHIS2 sign-in card before live DHIS2 work
- The DHIS2 password field must never be prefilled or persisted in browser storage
- After successful DHIS2 sign-in, clear the password field
- Connection status should distinguish `Signed in`, `Not signed in`, and `Not checked`
- Separate live DHIS2 search from local saved registry tables
- Debounce search input by roughly 300-500ms
- Show `Searching DHIS2...` while requests are in flight
- Show `Import`, `Already imported`, or `View/Edit local metadata` action states
- Ask for DHIS2 credentials only in the Manager Settings sign-in card; never on facility, indicator, or workspace pages
- Facility results should show facility name, district or parent, type, DHIS2 UID, DHIS2 code, and parent name
- Data element results should show data element name, HMIS code, DHIS2 UID or operand, dataset, category combo, value type, and import status
- If DHIS2 fails, show a practical message: `Could not connect to DHIS2. Check DHIS2 credentials or network.`

## Assessment Team UI Pattern

Assessment round builder team assignment should use field language:

- Use `Assign field team`, not only `Assign assessor`
- Show one row or card per selected facility
- Require a Team Lead selector
- Support optional Team Members with multi-select behavior
- Keep Team Lead out of the Team Member checklist for the same facility
- Show a clear publish blocker when any facility has no Team Lead
- In My Assessments, show `My team role: Team Lead` or `My team role: Team Member`

## Offline and Sync UI Pattern

Keep offline behavior obvious and calming.

Suggested messages:

- Offline: `You are offline. Your work is being saved on this device.`
- Pending sync: `Your draft is saved locally and pending sync.`
- Syncing: `Syncing your assessment data...`
- Synced: `Synced successfully.`
- Sync failed: `Sync failed. Your draft is still saved locally. Try again when the network improves.`
- Relogin required: `Please log in again to sync your saved draft.`

## Analytics UI Pattern

- Summary cards first
- One or two charts per row max
- Heatmap should be color-meaningful but still readable with labels
- Facility rankings and indicator issues should use tables for precision
- Show severity and issue type with badges, not prose walls

Heatmap cell colors:

- Green -> exact
- Yellow -> minor
- Orange -> moderate
- Red -> major or critical
- Gray -> missing or not assessed

## Report UI Pattern

- Report type cards for generation entry
- Strong privacy warning if comments are included
- Clear preview area
- Report editor in its own card
- Separate review/approve actions from export actions
- Export actions should be disabled until approval
- Show prompt version and AI/template provenance in metadata

## Dashboard Pattern

Manager dashboard should prioritize:

- round progress
- exact match rate
- major and critical discrepancies
- corrective actions
- recent reports

Assessor dashboard should prioritize:

- assigned assessments
- pending sync
- cached offline packages
- next deadline

Reviewer dashboard should prioritize:

- submitted work needing review
- critical discrepancies
- actions needing verification

Viewer dashboard should prioritize:

- approved reports
- summary analytics

## Empty, Loading, and Error States

- Empty states should be calm and actionable
- Loading states should prefer soft placeholders over noisy spinners
- Error states should explain the practical next step
- Never expose stack traces or secret values in UI text

## Accessibility

- strong contrast
- visible keyboard focus
- touch-friendly targets
- avoid color-only meaning
- semantic labels for forms and tables

## Low-Bandwidth Guidance

- keep dependencies lightweight
- avoid decorative heavy media
- preserve local draft state before visual polish
- no unnecessary animations
- no service-worker-heavy workflow in V1

## Final Consistency Rule

Every major page should share the same design language:

- navy/teal/white palette
- rounded `2xl` surfaces
- soft shadows
- consistent status badges
- readable spacing
- calm interaction feedback
