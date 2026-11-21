# ADR-015: The roadmap database is PostgreSQL 18, scoped by tenant and keeping every version

- Status: Accepted — owner, 2026-11-20, after three reviews and grilling rounds 1–7
  (Options below, each marked ✅). Owner direction: PostgreSQL 18 (supported on Google
  Cloud); a detailed history of who changed what, where, over many versions, with all
  past content viewable; nothing may preclude a tenancy per NHS Wales organisation;
  technical detail is settled during EPC-022.
- Date: 2026-11-20 (amended by ADR-018 and ADR-019, 2026-11-21: identities, sessions,
  invitations, definer functions, permissions and platform jobs)

## Context

Google Sheets is a temporary data source; a PostgreSQL-backed HTTP API replaces it
behind the roadmap repository (ADR-002, `docs/operations/replacing-google-sheets.md`).
Much of today's domain code exists because a spreadsheet has no keys, constraints,
transactions or history: items without IDs, copied family cells that drift out of step
(ADR-013), row order as item order (ADR-012), tags as delimited text in one cell,
pending edits held in the browser, and client-side conflict detection with a re-read to
settle a lost answer (ADR-012). The database must not inherit those workarounds.

The requirements: every change is attributable to a person and every past version of a
roadmap can be seen; DHCW may later host other NHS Wales organisations, each with its
own roadmaps; the first deployment holds one organisation, DHCW. The scale is small:
dozens of roadmaps, hundreds of items, a handful of editors per organisation. The API's
framework, ORM and migration tool are decided in their own ADR, identity and
authorisation in theirs; this one binds the database, whatever writes to it.

## Decision

### Engine

- **Cloud SQL for PostgreSQL 18, in `europe-west2` (London).** AlloyDB is rejected as
  cost and capability this scale does not use. Use core features; extensions only as
  Cloud SQL supports them and a stated rule needs them (`pgaudit` is optional).
- PostgreSQL 18's `uuidv7()` generates keys. Its temporal constraints are not relied on:
  versions are ordered by revision number, not by time ranges (_History_).
- **Rejected:** a document store or JSON-first schema (the domain is relational, and
  constraints are the point); a backend-as-a-service (ties the data model to a vendor).

### Model the domain, not the spreadsheet

- **Normalised working tables with foreign keys** for roadmaps, items, families,
  categories, tags and organisations, with join tables linking items to tags and to
  organisations. A roadmap references its family and category by key, and an item its
  tags and organisations; names and colours are never copied, so "out of step" cannot
  happen.
- **Every list is the tenant's own** (Options 6, 7): families, categories, tags and
  organisations, each with English and Welsh names. A tag renamed is renamed on every
  item.
- **An item's details are text**, an English and a Welsh column (Option 10): one detail
  per line, nested by a `- ` marker after two spaces per level. The API parses it; a
  `CHECK` on the line format is the database's guard. Details are owned by their item
  and referenced by nothing, so text is enough.
- **The database enforces the rules it can**: `NOT NULL`, `CHECK`, `UNIQUE`, foreign
  keys. Constrained values (horizon, section, change-set kind) are `CHECK` constraints or
  lookup tables, not enum types, whose values cannot be removed. An item is never
  unplaced. The API validates too, but the database is the last line.
- **Typed columns**: a calendar date is `date` (a roadmap's Last updated, set by its
  Product Lead), a moment is `timestamptz` (stored in UTC), a colour is checked text.
- **Bilingual text as an English and a Welsh column per field** (ADR-008: exactly two
  languages), English required where the domain requires it, Welsh optional. A
  translations table is rejected as joins for no second axis of variation.
- **Order is stored**: each item has an integer position within its placement, `1..n`;
  a save that reorders rewrites its placement's positions under the roadmap lock
  (Option 14).
- **The public "Product Lead" is free text** on the roadmap, separate from who is
  assigned to edit it (Option 18).
- **Nothing a roadmap shows is deleted** (Options 8, 15): a roadmap or a list entry is
  retired, and can be reinstated.
  - A retired roadmap leaves the editor's roadmap list and the public site; its
    assigned leads and the tenant's admins see it in a retired view, read its history
    and reinstate it (Option 33).
  - A retired list entry can no longer be chosen; what already references it keeps it.
  - **Names stay reserved** (Option 31): a short name's address and a list entry's name
    are unique within their tenant across current and retired rows alike, so an old
    public address never shows another product and history never shows two entries
    with one name. A short name is not editable (STY-040); if it ever becomes so, its
    past addresses stay reserved. A retired entry's name returns by reinstating it.
- **Not carried over**: a template to copy, organisation codes the list doesn't hold,
  items without an ID, a lock on editing Welsh tags or details, a re-read to settle a
  lost answer. The import from Sheets reports every row these rules refuse (an unplaced
  item, an unknown organisation code, Welsh tags with no English) and quarantines it for
  the owner to fix; it never loosens a constraint to make a row fit.

### Identity of rows

- **Every row has a UUIDv7 surrogate key**, generated by `uuidv7()` or supplied by the
  client and validated, unique per tenant. A client-supplied key lets the editor name a
  new item before it is written. Keys appear in the API, never in the interface.
- **Natural keys are unique constraints, not primary keys** (a short name address, a
  list entry's name), so renaming a list entry is an update.
- **Public addresses outlive the move**: a roadmap's public address is its short name's
  address, unchanged by the import. Each item keeps today's eight-character item ID as a
  column unique within its roadmap, and new items get one too, until no reader outside
  the database uses it.

### Tenancy: one database, a tenant on every row

- **A `tenant_id` on every tenant-owned table**, `NOT NULL`, referencing `tenants`. DHCW
  is the first tenant.
- **Shared tables are named**: `tenants`, `people` and people's sign-in identities.
  Every other table is tenant-owned.
- **No reference crosses a tenant**: uniqueness is scoped by tenant, every tenant-owned
  parent has `UNIQUE (tenant_id, id)`, and every foreign key between tenant-owned tables
  includes `tenant_id`.
- **Row-level security, enabled and forced, from the first migration**, on every table:
  - a tenant-owned table's policy has `USING` and `WITH CHECK`, matching `tenant_id` to
    `current_setting('app.tenant_id', true)`, and fails closed when it is unset or empty;
  - shared tables are protected too (Option 27): a person is visible to themselves and
    to the tenants they are a member of; a sign-in identity is visible to its person,
    and found at sign-in only by its exact provider and subject, through a definer
    function; the memberships policy keyed on the person, which lets the API read a
    person's tenants and pending invitations before it sets a tenant, is read-only;
  - the tenant and the person are set per transaction only (`set_config(…, true)`),
    never per session, so neither leaks through a pooled connection;
  - views are created with `security_invoker = true`; the only `SECURITY DEFINER`
    functions are the commit path, the sign-in lookup, the tenant procedure and the
    redaction procedure, each with a pinned `search_path` and `EXECUTE` revoked from
    `PUBLIC`;
  - forced RLS binds the migration role too: a data fix or import sets its tenant.
- **Tenants are created by a platform procedure**, run by platform operators with the
  tenant's first admin (Option 21); the application's role cannot create one.
- **Rejected:** a schema or a database per tenant (migrations once per tenant, harder
  cross-tenant reporting, more connection pools), and leaving tenancy out "until needed"
  (adding it to every row, key, policy and snapshot later is a rewrite). A shared
  database with `tenant_id` throughout can still move a large tenant out later.

### People, access and permissions

The database holds who may do what; the API checks it on every request, and the
database enforces tenant isolation (Option 20), except for redaction, which the
database also checks (Option 34). How people sign in belongs to the identity ADR (ADR-018); the
permission catalogue and the shipped roles belong to the authorisation ADR (ADR-019) (Option 35).

- **A person has one or more sign-in identities** (Option 11): a provider (Microsoft or
  Google) and that provider's subject, unique together. A second identity is linked
  explicitly, by the person while signed in or by an admin; identities are never merged
  by matching email.
- **Access is a membership, granted by a tenant admin's invitation** (Option 12); nobody
  belongs to a tenant by default.
- **Permissions are a fixed catalogue defined by the application, bundled into roles
  each tenant defines** (Option 19); members hold roles. The schema keeps room for a
  permission granted to one person directly, later, without reworking roles.
- **Editing a roadmap needs an assignment to it** (Option 13), except for a tenant's
  admins, who edit every roadmap (Option 23). Who may assign, and that whoever adds a
  roadmap is assigned to it, are the authorisation ADR's (ADR-019; Options 16, 17).
- **Every change to memberships, roles, grants and assignments is a change set** of the
  tenant's access scope, so who gave whom access is history like any other.
- **Writes to shared tables go to a platform audit log** (Option 27): a person created,
  an identity linked or unlinked, a tenant created, each with who, when and why. They
  have no tenant, so they are not change sets.

### Editing: a private scratch, a shared draft and publications

- **Every save reads from the saver's scratch** (Options 3, 28): a private scratch on
  the server, one per person per roadmap, holding that person's unsaved edits as one
  schema-versioned JSONB row with the draft revision it started from.
  - It is visible to its owner alone, by a policy on the person as well as the tenant,
    never public, and never history: scratch writes are exempt from the change-set
    rules (_History_).
  - It is deleted on Save or Discard, when its owner's assignment or membership ends,
    when its roadmap is retired, and on expiry after a period without activity, with a
    warning first, both run by a scheduled API job (Option 29; the period is
    EPC-022's).
  - A second tab or device editing the same scratch is refused by the scratch's
    version, and refreshes.
  - EPC-022's adapter maps today's publish onto the API as a scratch write, then "save
    and publish", so the scratch is exercised from the first delivery.
- **Saving promotes the scratch to the roadmap's shared draft** as one change set
  (Option 3). Each roadmap has one draft, which its assigned leads edit together; the
  working tables hold it.
- **Saves merge field by field** (Options 3, 25): under the roadmap lock, the API
  compares the snapshot of the save's base revision, the current draft and the save's
  changes. A field the save changes, unchanged since its base, is written; a field
  changed since to another value is a conflict. A field means a roadmap's field or an
  item's, an item's tags or organisations as one set each, and a placement's order,
  which has its own version, so a reorder changes no item. Changing a removed item is a
  conflict, and so is removing an item changed since the base; a new item never is. These are ADR-012's conflicts, worked out on the
  server. A conflicted save writes nothing and returns its conflicts.
- **"Save and publish" is one transaction** of two change sets, a save then a publish
  (Option 3). A "Save all" across roadmaps is one change set per roadmap, in one
  transaction or several, as the editing-model epic decides; change sets saved together
  share a batch reference (Option 30).
- **Discarding the draft returns it to the published version**, as a change set, by any
  assigned lead (Option 3). A roadmap never published discards to empty.
- **Rejected:** pending edits held in the browser, as today (no attribution between
  co-leads before a publish, and lost with the tab); browser storage (unsaved content
  left on shared workstations); a draft per person (a merge at every publish); autosave
  straight into the draft (history noise); a save that bypasses the scratch (a second
  save path, tested late).

### History: a change set, a snapshot and a change summary per write

- **Every write to a draft, a list or access is a change set**: a tenant-owned row
  recording the person who made it, when, its scope (one roadmap, the tenant's lists, or
  the tenant's access), its kind, an optional note, an optional batch reference, and the
  revision it was based on and produced. Scratch writes and shared-table writes are not
  change sets.
- **Idempotency**: a change set's key is supplied by the client. A retry with the same
  key, tenant, person and request hash returns the first result and writes nothing; the
  same key with anything else is refused; a refused write leaves no change set, so its
  retry is judged afresh.
- **Revisions order everything** (Option 32): each roadmap has a revision, and the
  tenant's lists and its access each have their own. A change set locks its scope's row
  and increments its revision. List and access change sets are serialised by that lock
  and conflict only when they change the same entry. A transaction that takes several
  locks takes the tenant's first, then roadmaps by key, so concurrent writers never
  deadlock.
- **Snapshots and kinds**: save, discard, restore, retire, reinstate, list change,
  import and migration store a new snapshot of their scope; publish, unpublish and
  access change reference an existing one. A redaction that changes a draft or a list
  stores a new snapshot of that scope, as any other write to it does.
- **The commit function builds each snapshot itself** (Option 1), from the working
  tables, after the write: the whole roadmap (or the whole of the tenant's lists) in one
  JSONB document carrying its schema version, the list revision it was written against,
  and list entries by key, never by name. Past content is a snapshot read, with names
  resolved through the list snapshot of exactly that revision; nothing is reconstructed
  from rows. A snapshot is never rewritten except by redaction.
- **Sign-off is per change set** (Option 26): the commit function marks each change set
  complete in a row only it writes. A transaction may complete one change set and open
  the next. Triggers refuse:
  - at commit (deferred), a transaction that changed a working table outside a
    completed change set;
  - at once, a write to a working table in a change set already completed;
  - at once, a write outside the change set's scope, such as a roadmap change set
    writing another roadmap's rows.
- **Each change set has a change summary**: one row per field or entry changed, with its
  old and new value, derived from the previous snapshot and the new one, and rebuildable
  from them. "Who changed what", "everything one person did" and "who last changed this
  field" are queries on summaries.
- **History is written only by the commit function and the redaction procedure**:
  change sets, snapshots and summaries are readable by the application's role, never
  updated, deleted or truncated by it.
- **Restoring writes forward**: a past version's snapshot is upgraded to the current
  schema and written to the draft as a change set of kind `restore`; a retired list
  entry it references is kept and flagged for the lead to replace before publishing.
- **Redaction is the one exception to immutability** (Options 9, 34): an audited
  procedure, run by a tenant admin and checked by the database against that person's
  roles, replaces named content with a `[redacted]` marker wherever it is held: in
  snapshots, summaries, the draft, scratch and the current publication. It records one
  change set of kind `redaction` per scope it touches, sharing a batch reference,
  saying who, when, why and where, never the content.
  Backups keep the content until they expire.
- **The guarantee covers every ordinary writer**: the schema owner can disable triggers,
  and a database restore bypasses them. `TRUNCATE` is revoked, and the migration role's
  data fixes open a change set of kind `migration`.
- **Rejected:** row history tables kept by triggers, one per working table, with time
  ranges and a reconstruction function (more machinery to keep in step with every
  schema change, for answers snapshots and summaries give directly at this scale); an
  API-built snapshot (nothing proves it matches the data); a generic audit log of row
  images; event sourcing; versioning in the ORM (misses writes the ORM does not make).
  `pgaudit` statement logging may be added for security; it is not content history.

### Publication

- **A publication pins a snapshot**: a tenant-owned row naming a roadmap, the change set
  whose snapshot is public, who published it and when. Unpublishing is a change set that
  leaves the roadmap with no current publication; a roadmap never published, or retired,
  has none.
- **The public site reads through the API, never the database** (Option 4): the API
  sets the tenant from the tenant's public address (Option 5: one public site, each
  tenant under its own address) and reads current publications. The database has no
  public role.
- **List names are live** (Option 2): a published snapshot holds list entries by key,
  and the public read joins the tenant's current lists, so a family, category or tag
  renamed goes public at once on every published roadmap, with no republishing. A past
  version shows the names of its recorded list revision.

### Roles, operation and data protection

- **Database roles**: a plain, no-login role owns tables and functions (technical set);
  migrations run as a login role that switches to it. The application's role reads and
  writes data under RLS, writes history only through the commit function, and runs no
  DDL. No runtime role owns a table or bypasses RLS. `cloudsqlsuperuser` is for instance
  administration and optional `pgaudit` only.
- **Every schema change is a migration**, reviewed with its RLS policies, its tests and
  the snapshot schema version it introduces, if any.
- **Backups and point-in-time recovery stay in the UK**: Cloud SQL's backup location is
  set to a UK location, not left to its default, and checked at provisioning, with
  PostgreSQL 18's availability in `europe-west2`. Storage is encrypted as Cloud SQL
  provides.
- **Personal data is held once**: change sets, memberships and assignments reference a
  person by key; a person's name lives in `people`, which an audited privileged
  procedure can correct or pseudonymise without touching history. The retention period
  for people's records is set with the owner's data protection assessment.

### What enforces this

Tests run against a real PostgreSQL 18, never an in-memory substitute, as the
application's own role, and prove:

- one tenant cannot read or write another's rows; an unset tenant reads nothing; people
  and identities of another tenant are invisible; the person-keyed memberships policy
  cannot write;
- the tenant and person settings do not survive their transaction on a pooled
  connection;
- every draft, list or access write produces one completed change set, with a snapshot
  where its kind stores one and a summary; a write outside a change set, after its
  sign-off, or outside its scope cannot commit, and no setting the application can make
  satisfies the triggers;
- two change sets in one transaction ("Save and publish") commit;
- scratch writes need no change set, and a scratch is visible to its owner only;
- change sets, snapshots and summaries cannot be updated, deleted or truncated, except
  by the redaction procedure, which refuses a person without the permission, records
  itself, and leaves snapshots readable and restorable;
- two saves on one base revision merge when their fields don't overlap, and the second
  is refused when they do;
- a list change concurrent with a roadmap save completes without deadlock;
- a retried change set returns its first result; the same key with another payload is
  refused;
- a retired roadmap's short name and a retired entry's name stay reserved;
- a restore across a snapshot schema version works and flags retired entries;
- the import quarantines the rows the constraints refuse.

EPC-022 names the suite.

### ADR-018 and ADR-019 amendments

Accepted by the owner on 2026-11-21 with ADR-018 (identity) and ADR-019
(authorisation). Where these bullets differ from the text above, they hold; the rest
stands.

- **Sign-in identities** (Option 11): an identity is `(issuer, subject)`, never an
  email. Only the person attaches one, through a guarded link (ADR-018); the person
  (never their last) or a platform operator removes one, never a tenant admin.
- **Shared tables** (_Tenancy_): sessions and sign-in transactions join `tenants`,
  `people` and identities, each with row-level security.
- **Definer functions** (_Tenancy_): beside the four above, the closed list gains
  ADR-018's functions for sign-in transactions, sessions, the invitation lookup,
  redemption and the retention purges, and ADR-019's platform procedures (issuing an
  operator invitation, disabling a person and revoking their sessions, removing an
  identity). ADR-018's functions are owned by a dedicated no-login role with only the
  grants each needs, not by the schema owner.
- **Invitations** (_People, access and permissions_): an invitation names an address,
  not a person, until it is redeemed, rather than being a pending membership the
  person-keyed policy reads; creating, revoking and redeeming one are access change
  sets. A tenant keeps at least one admin, and admins review members every six months.
- **The platform audit log** (Option 27) also records a person disabled and invitations
  a platform job issues; it stays append-only and is never purged.
- **Permissions** (Options 16, 22, 23, 33): the Product Lead role also holds
  `roadmaps:edit` and `roadmaps:publish`; an admin's right to edit every roadmap is the
  `roadmaps:edit-any` permission; a co-lead must hold `roadmaps:edit`, and a lead may
  unassign themselves, even as the last; retired roadmaps are seen by their assigned
  leads and holders of `roadmaps:edit-any`, and retired or reinstated by assigned
  holders of `roadmaps:edit` and by holders of `roadmaps:edit-any`.
- **Roles** (_Roles, operation and data protection_): platform jobs run under their
  own database role and service account.

## Consequences

- One write path: every draft, list and access write opens a change set and ends in the
  commit function. It must stay the only path; a second one would write unrecorded
  changes.
- Snapshots are copies: storage grows with every save, small at this scale, and readers
  handle every snapshot schema version for as long as snapshots are kept.
- The editor's editing model changes before switch-over: pending edits in the browser
  (ADR-012) become a server scratch, a shared draft and publications, with permissions
  and assignments, in a later epic. `RoadmapRepository` gains calls for them then; until
  then, EPC-022's adapter maps today's calls onto the API through the scratch.
- Sheets-era rules leave as the API takes over: ADR-009, ADR-011, ADR-013 and ADR-014
  describe the spreadsheet, and ADR-012's pending edits, conflict detection and
  lost-answer settlement move to the API and database. Each is superseded, in whole or
  in part, by the ADR that switches the data source; until then they stand.
- History begins when the API holds the data: the import is each tenant's first batch of
  change sets, of kind `import`, by a system actor: its lists, its access, then one per
  roadmap; a final export of the spreadsheet is
  archived rather than its revision history imported.
- CHO-005 (Last updated in UTC) is settled by the API's contract; this schema keeps Last
  updated a `date`.
- STY-048 (removing a roadmap) is bound by Options 8 and 33: retired, never deleted, and
  reinstated from a retired view.
- Follow-on records: the API stack ADR (ADR-017); an identity ADR for Microsoft and
  Google sign-in (successor to ADR-003; ADR-018); an authorisation ADR (ADR-019) holding the permission
  catalogue, the shipped roles (Option 22) and who assigns leads (Options 16, 17);
  EPC-022 delivers the first schema and sets the scratch's expiry (Option 24).
  Infrastructure as code is a later epic.
- The glossary gains the terms this introduces (tenant, assignment, scratch, draft,
  change set, snapshot, publication, retired), and
  `docs/operations/replacing-google-sheets.md` points here.

## Options (owner's choice marked ✅, 2026-11-20)

Grilling rounds 1–5 after the second review, and rounds 6–7 after the third.

1. **Who builds a snapshot** (round 1)
   - ✅ (a) The commit function, from the working tables.
   - (b) The API, passed in. Lost: nothing proves a snapshot matches the data.
2. **How list names reach a published roadmap** (round 1)
   - ✅ (a) Keys in snapshots; the public read joins the current lists. _A family
     renamed goes public at once on all its published roadmaps._
   - (b) Republish every affected roadmap. Lost: snapshots matching no working state,
     and conflicts for open editors.
   - (c) Names frozen until republished. Lost: ADR-013's "goes public at once".
3. **Where unpublished edits live** (rounds 1–4)
   - ✅ A private server scratch per person per roadmap (round 4: over browser storage,
     which leaves content on shared workstations, and memory); Save promotes it to one
     shared draft per roadmap as a change set (round 2: over a draft per person; round
     3: the owner's own model, over saving each confirmed edit, an explicit "Save draft"
     from the browser, and autosave); non-overlapping saves merge (round 2); "Save and
     publish" in one step (round 3); any assigned lead discards the draft (round 3).
   - Lost: pending edits in the browser, as today: no attribution between co-leads.
4. **How the public site reads** (round 1)
   - ✅ (a) Through the API.
   - (b) A read-only database role. (c) Static files exported on publish. Lost: a schema
     the public site depends on; an export pipeline.
5. **Tenants and the public site** (round 1)
   - ✅ (a) One public site, each tenant under its own address.
   - (b) A deployment per tenant. (c) Decided later.
6. **Organisations** (round 1)
   - ✅ (b) Each tenant keeps its own list.
   - (a) One shared list. Lost (owner's choice): each tenant's control of its list.
7. **Tags** (round 1)
   - ✅ (a) A tenant's tag list with English and Welsh names, referenced by items.
   - (b) Free text per item. (c) Free text now, a list later.
8. **Removing a roadmap** (round 1)
   - ✅ (a) Retired, never deleted; reinstatable.
   - (b) Deleted, history kept unlinked. (c) Deleted with its history.
9. **Redaction** (rounds 1–2)
   - ✅ (a) An audited procedure, run by a tenant admin.
   - (b) None. Lost: a route to remove personal data published in error.
10. **Item details** (rounds 3–4)
    - ✅ Free text per language, one line per detail, format-checked.
    - JSONB with a check function. Lost (owner's choice): line-by-line pairing, which
      nothing needs.
11. **Sign-in identities** (round 2) — ✅ one or more per person, linked explicitly;
    over matching by email, and one identity per person.
12. **Access** (round 2) — ✅ invited by a tenant admin; over by email domain.
13. **Edit rights** (round 2) — ✅ assigned roadmaps only; over any roadmap, as today.
14. **Positions** (round 3) — ✅ integers rewritten per placement; over gapped or
    fractional.
15. **List entries** (round 2) — ✅ retired, never deleted; over deleting when unused.
16. **Assigning leads** (round 3) — ✅ an admin, or an assigned lead adding co-leads.
    Recorded in the authorisation ADR (ADR-019).
17. **Adding a roadmap** (round 3) — ✅ any Product Lead, assigned to it. Recorded in the
    authorisation ADR (ADR-019).
18. **The public Product Lead field** (round 3) — ✅ free text, over derived from
    assignments.
19. **Permissions** (round 4) — ✅ a fixed catalogue bundled into tenant roles, not
    precluding direct grants to a person later (the owner's own answer).
20. **Where permissions are enforced** (round 4) — ✅ the API checks; the database
    isolates tenants.
21. **Creating tenants** (round 5) — ✅ platform operators; over self-service.
22. **The Product Lead role** (round 5) — ✅ `roadmaps:create` and `tags:edit`; every
    other permission is admin-only by default. Recorded in the authorisation ADR (ADR-019).
23. **Admins and roadmaps** (round 5) — ✅ admins edit every roadmap.
24. **Scratch expiry** (round 5) — ✅ 30 days, warned at 23. Recorded in EPC-022.
25. **The unit of a merge** (round 6) — ✅ a field, as ADR-012's conflicts are; over an
    item (more conflicts than today). Merged three-way, with a version per placement's
    order (round 7, as walked through).
26. **Sign-off** (round 7) — ✅ per change set, several per transaction, scope-checked;
    over one change set per transaction (a combined kind, a coarser history).
27. **Shared tables** (round 6) — ✅ RLS on people and identities, and a platform audit
    log; over API-only protection, and a person per tenant (which undoes linked
    identities across tenants).
28. **A save without a scratch** (round 7) — ✅ every save reads from a scratch; over
    edits in the request (a second save path, tested late).
29. **Scratch expiry job** (round 6) — ✅ a scheduled API job; over `pg_cron` (which
    cannot send the warning).
30. **"Save all"** (round 7) — ✅ change sets share a batch reference.
31. **Retired names** (round 6) — ✅ reserved, returned by reinstating; over freed.
32. **List and access revisions** (round 6) — ✅ separate, conflicting only on the same
    entry; over one shared revision.
33. **Retired roadmaps** (round 6) — ✅ seen and reinstated by their leads and admins;
    over admins only.
34. **Redaction checks and scope** (round 6) — ✅ the database checks the permission
    too; the marker replaces content everywhere it is held; over an API-only check, and
    history only.
35. **What ADR-015 holds** (round 6) — ✅ the schema's shape; the permission catalogue
    and roles move to the authorisation ADR (ADR-019), the expiry to EPC-022.

The technical set (round 3, the owner's walk-through of the second review's findings):
✅ a plain no-login schema owner; ✅ a replay matches key, tenant, person and request
hash; ✅ restore upgrades and flags retired entries rather than refusing; ✅ integer
positions (Option 14); details as text (Option 10).
