# DHCW Roadmap Editor

The shared vocabulary for Product Leads managing their public-facing roadmaps.
Interface copy speaks the user's words below; code speaks the same words, and data-source
words stay inside infrastructure (ADR-002). Terms marked _(planned)_ name things the
product brief describes and the code does not have yet.

## Language

### People

**Product Lead**:
A DHCW member of staff who leads one or more products and manages their roadmaps in
this tool; a product may have several. The primary user
(`docs/backlog/personas/product-lead.md`). A roadmap names its product lead as free
text; the app does not know which Product Lead is using it.
_Avoid_: Product owner, admin, editor

**Public reader**:
Anyone who reads a roadmap on the public site: first health boards and Welsh Government
stakeholders, then DHCW staff, then patients and the public. They never use this tool,
but every roadmap item is written for them.
_Avoid_: Customer, end user

**Public site**:
The separate app that reads the shared data source and shows published roadmaps to
public readers. This tool never renders it.
_Avoid_: Viewer (a role in this tool), front end, website

### Roadmaps

**Roadmap**:
A product's public plan, in the Now / Next / Later format, managed by its Product Lead.
Each roadmap is one row of the **roadmap index** (ADR-009). Its identity is its **short
name**, which outlives the data source. Its title is the name of the product it is for,
so the editor labels it "Product name" (STY-065). A Product Lead adds one from the
roadmap list; it is written at once and starts not published (STY-040).
_Avoid_: Sheet, worksheet, tab, board

**Product details**:
What a roadmap says about the product it is for: its vision, service description,
family and category. A roadmap's page shows them on request, and the roadmap dialog
edits them with the roadmap's title, status label, product lead and last updated date
(STY-065).
_Avoid_: About this roadmap

**Short name**:
The name a Product Lead gives a roadmap when adding it, such as "Community Nursing":
the roadmap's identity, never changed in the editor. Its **address**, the end of the
roadmap's address on the public site and here, is the short name in lower case with
hyphens between its words (`community-nursing`); two short names with the same address
are the same. It holds letters, numbers, spaces and hyphens only (STY-040). In the
connected spreadsheet it is the `Sheet` value and the name of the roadmap's worksheet.
An organisation's short name (`Cardiff and Vale`) is another thing.
_Avoid_: Slug, ID, key, sheet name, tab name

**Horizon**:
One of the three groups a roadmap sorts its work into, by how soon it is expected:
**Now** (being worked on), **Next** (coming up) and **Later** (intended, further out).
Horizons are not dates.
_Avoid_: Column, lane, quarter, phase

**Section**:
One of three groups shown around the horizons, shared with the public site: **Recently
delivered**, **Delivered this year** and **Not doing** (ADR-011).
_Avoid_: Horizon, status

**Placement**:
Where a roadmap item appears: one of the three horizons or one of the three sections.
A roadmap item has at most one; an item with none is an **unplaced item** (ADR-011).
A Product Lead moves an item by changing its placement, which never unplaces it
(ADR-014). Code and records use the word; interface copy names the horizon or section
itself.
_Avoid_: Column, lane, status

**Unplaced item**:
A roadmap item with no recognised horizon or section, which the public site does not
show. The editor shows it, flagged, so the Product Lead can place it (ADR-011).
_Avoid_: Draft, hidden item

**Order**:
The sequence a placement's items show in, here and on the public site. A Product Lead
changes it from an item's Move menu, and a changed order is one pending edit of its
placement, whatever number of its items moved (STY-050; ADR-012). Order says nothing
about importance.
_Avoid_: Rank, priority, sort order, row order

**Position**:
An item's place in its placement's order, counted from the top: "4 of 4".
_Avoid_: Rank, row, index

**Roadmap item**:
One piece of work on a roadmap: a title, a description, expected outcomes, tags and any
other details that help a public reader. It fits on one card no bigger than a phone
screen. A **new item** is one a Product Lead has added, with a title and a placement,
and not yet published: a pending edit, which goes last in its placement unless the
Product Lead reorders it (STY-050; ADR-012).
_Avoid_: Ticket, task, feature, epic, story

**Expected outcome**:
The change a roadmap item should bring about for patients, staff or the public, in their
terms rather than as an output delivered.
_Avoid_: Deliverable, benefit, KPI

**Tag**:
A short label on a roadmap item for grouping and filtering, such as a theme or an
audience. Free text chosen by the Product Lead today, who is offered the tags the
roadmap's other items carry; a shared list may follow. A comma or a line break ends a
tag, so a tag holds neither.
_Avoid_: Label, category, keyword

**Detail**:
One line of the list a roadmap item's card shows under "Details", and the public site
under "What this covers". A detail is nested under the one above it or sits at the top
level; a list has three levels. It is text on one line, which never starts with a
hyphen: in the data source, hyphens at the start of a line are its nesting.
_Avoid_: Bullet, point, sub-item

**Phase**:
A free-text word shown above a roadmap item's title, such as "Discovery" or "Beta",
saying what stage the work is at. Not a roadmap's status label.
_Avoid_: Stage, status

**Organisation**:
One of the NHS Wales bodies a roadmap item's work is for, such as Cardiff and Vale
University Health Board, or **All Wales** for national work; shared with the public
site, which filters by it (ADR-011). Each has a code (`CAVUHB`), a short name (`Cardiff
and Vale`) and a full name. The repository serves the list; in Sheets it is the built-in
list (ADR-014).
_Avoid_: Health board (only some are), customer

**Pending edit**:
A change to a roadmap or roadmap item, a new item, a placement's order, or the removal
of an item, that the Product Lead has made but not yet published or saved; the public
site does not show it. It is kept in this browser tab, in memory, through an expired
session, Reconnect and, if the Product Lead chooses, Disconnect. A change is kept with
the value it was edited from, which a co-lead's change is found by; a removal with the
item as loaded; a new item has none, so it never conflicts with one. A removed item's
other changes wait beneath its removal until it is undone (STY-070). It is lost on
closing the tab, after asking (ADR-012).
_Avoid_: Unsaved change, draft (drafts are a later feature)

**Publish**:
To write a published roadmap's pending edits to the shared data source in one deliberate
step, all or none, after which the public site shows them from its next nightly update
("Publish changes"). The MVP has no review or draft step (ADR-012). Also, to make a
roadmap a published roadmap ("Publish roadmap"), taking any pending edits with it
("Save and publish"); unpublishing takes it off the public site (STY-035).
_Avoid_: Save (for a published roadmap), sync, push, go live, enable

**Save**:
To write the pending edits of a roadmap that is not published: the same step as
publishing, and nothing becomes public until the roadmap is published (ADR-012,
STY-035).
_Avoid_: Publish (for a roadmap that is not published), store

**Conflict** _(planned)_:
A field, or a placement's order, a co-lead changed in the data source, to a different
value, after the Product Lead loaded what they have edited. Any change a co-lead makes
to a placement's items is one to its order: a reorder, or an item added, moved in,
moved out or removed (STY-050). Any change a co-lead makes to a field of an item the
Product Lead has removed is one to the removal; a reorder alone is not (STY-070).
Publishing stops until, for each conflict, the Product Lead keeps their change or uses
the co-lead's (ADR-012).
_Avoid_: Clash, merge conflict

**Last updated**:
The date a roadmap says it was last updated, which the public site shows. The Product
Lead sets it as a pending edit, or marks it as today when publishing or saving ("Mark as
updated today"); publishing changes it only then. It is never after today, by the
Product Lead's own clock (STY-036). Among the product details the editor labels it
"Roadmap last updated", since it is the roadmap's date, not the product's (STY-065).
_Avoid_: Last modified, published date, last published

**Stale roadmap** _(planned)_:
A roadmap not published for longer than the staleness threshold, suggested as six weeks.

**Item card**:
A roadmap item as the Cards view of a roadmap's page shows it, every field it has under
its label; its size is the budget for the item's text.

**Compact view**:
The second view of a roadmap's page, in which each item is a row under the same headings
that opens in place to its other fields, by its chevron or a press on its text
(STY-069); Cards is the view first seen (STY-067). A
**row** of it is an item shown that way, never an item's position.
_Avoid_: List view, table

**Quick add**:
The "Add an item" control that ends each placement on a roadmap's page, in both views,
and the title field it opens, where a Product Lead types a **new item**'s title and adds
it there, one after another (STY-080). In an empty placement it reads "Add the first
item".
_Avoid_: Inline add, ghost card, placeholder

**Moved mark**:
The edge and label on the item a Product Lead moved last, saying how it moved ("Moved
up", "Moved from Now", "Placed"), until the next move, or until the move is undone,
published or gone from the page (STY-071 S8). Display only: never a pending edit, and
never published.
_Avoid_: Highlight, moved tag (a **tag** is the item's own label)

**Roadmap list**:
The roadmaps available to the user, grouped by product family (families in name order,
then the roadmaps with no family) and sorted by title within each group.
_Avoid_: Dashboard, workspace

**Published roadmap**:
A roadmap the public site shows. A roadmap that is not published is still listed here,
marked "Not published" (ADR-009), and a roadmap added here starts that way (STY-040).
A Product Lead publishes or unpublishes it from its page, written at once; publishing
is refused while the public site's nightly update would fail on it (STY-035).
_Avoid_: Enabled, live, public roadmap

**Category**:
One of six fixed areas of care a roadmap belongs to, such as "GP & Community Services",
shared with the public site and defined once in the category list; a roadmap may have
none.
_Avoid_: Group, section, tag

**Product family**:
A named group of related products with one colour, such as "Single Record", defined once
in the family list. A roadmap belongs to at most one, and the roadmap list groups
roadmaps under it.
_Avoid_: Programme, portfolio

**Out of step**:
A roadmap whose own copy of its family or category differs from the family or category
list, as after a hand edit to the data source.
_Avoid_: Drift, mismatch

**Status label**:
Free text describing a product's stage, such as "Beta", shown as a badge.
_Avoid_: Phase (an item's tag on the public site), state

**Roadmap detail**:
The page for one roadmap, reached from its card or by deep link.
_Avoid_: Roadmap view, sheet page

**Roadmap card**:
A roadmap's entry in the roadmap list, which opens its roadmap detail. Not to be
confused with an item card.

### Data source

**Data source**:
Where roadmaps are read from and published to, hidden behind the roadmap repository,
and shared with the public site, so its format is a contract between the two apps. Today
it is one shared Google spreadsheet; a PostgreSQL-backed HTTP API is expected to replace
it.
_Avoid_: Backend, database

**Roadmap repository**:
The single boundary through which the application reads roadmaps, whatever the data
source.
_Avoid_: Sheets client, API service

**Connected spreadsheet**:
The one Google spreadsheet, fixed by configuration, that the data source reads. Only
infrastructure and setup documentation use this term.
_Avoid_: Workbook, file

**Roadmap index**:
The first worksheet of the connected spreadsheet, one row per roadmap, which the editor
and the public site both read (ADR-009). Only infrastructure and setup documentation use
this term.
_Avoid_: Roadmap list (the roadmaps shown to the user), roadmaps tab

**Worksheet**:
A tab of the connected spreadsheet. The first worksheet is the **roadmap index**; each
worksheet it names holds one roadmap's items, found by header rather than position. The
`Template` worksheet shows the permitted columns: the editor copies it to start a
roadmap, reading its header row to check it, and never changes it (ADR-009, ADR-011,
STY-040). Only infrastructure uses this term.
_Avoid_: Sheet (ambiguous with spreadsheet)

**Item ID**:
The column of a roadmap's worksheet holding each roadmap item's identity, which the
editor reads (an item without one has none), adds and fills when it publishes, and
never shows. A new item's is made when the item is added, and written with its row
(ADR-012). Only infrastructure and setup documentation use this term.
_Avoid_: Row number, key

### Tenancy and history

Planned with the database that replaces the spreadsheet (ADR-015).

**Tenant** _(planned)_:
An NHS Wales organisation that keeps its own roadmaps, lists and people in this tool;
DHCW is the first. Nothing one tenant holds is visible to another.
_Avoid_: Organisation (a body a roadmap item's work is for), account, workspace

**Directory** _(planned)_:
Microsoft's register of people who can sign in with a work account; NHS Wales has one,
shared by all its organisations. Microsoft calls it a tenant, but it never says which of
this tool's tenants someone belongs to (ADR-018).
_Avoid_: Tenant (for Microsoft's), Entra tenant

**Invitation** _(planned)_:
An offer of a membership to one email address, made by a tenant admin (or, for a
tenant's first admin, a platform operator), redeemed by that person signing in with the
link; the only way into a tenant (ADR-018).
_Avoid_: Sign-up, registration

**Membership** _(planned)_:
A person's place in one tenant, with the roles they hold there; a person can have
memberships in several tenants (ADR-015, ADR-019).
_Avoid_: Account, seat

**Sign-in identity** _(planned)_:
One account a person signs in with, at Google or in the NHS Wales directory, known by
its issuer and that issuer's ID for it, never by email; a person can have more than
one (ADR-018).
_Avoid_: Login, account, user

**Platform operator** _(planned)_:
A DHCW engineer who runs the platform's jobs, such as creating a tenant; holds no tenant
access unless invited like anyone else (ADR-019).
_Avoid_: Admin (a tenant's role), superuser

**Admin** _(planned)_:
A tenant's role that holds every permission but `roadmaps:edit`, and edits every
roadmap (ADR-019).
_Avoid_: Owner, superuser, operator (someone who runs the platform, not a tenant)

**Viewer** _(planned)_:
A tenant's role that reads every current roadmap, draft and history and changes nothing
(ADR-019).
_Avoid_: Reader, guest

**Assignment** _(planned)_:
A Product Lead's right to edit one roadmap. Admins edit every roadmap without one. Not
the roadmap's public "Product Lead" text.
_Avoid_: Ownership, lead (as a permission)

**Scratch** _(planned)_:
A person's own unsaved edits to one roadmap, kept for them alone until they save or
discard them, or until they expire. Never public, never history.
_Avoid_: Pending edit (the browser-held edits of the spreadsheet era), draft

**Draft** _(planned)_:
A roadmap's saved content that is not yet published, shared by its assigned leads; each
save adds to it.
_Avoid_: Pending edit, working copy

**Change set** _(planned)_:
One saved step by one person: a save, a publish, a restore, a list or access change.
History is the list of a roadmap's change sets, each saying who, when and what changed.
_Avoid_: Commit, revision (its number), audit entry

**Snapshot** _(planned)_:
A roadmap, or a tenant's lists, exactly as it stood after one change set; every past
version is one.
_Avoid_: Backup, copy

**Publication** _(planned)_:
The snapshot of a roadmap the public site shows, chosen by publishing; unpublishing
leaves a roadmap with none.
_Avoid_: Release, live version

**Retired** _(planned)_:
Of a roadmap or a list entry: taken out of use but kept, with its history and its name,
and able to be reinstated. Nothing a roadmap shows is deleted.
_Avoid_: Deleted, archived, removed

### Connection

Plumbing: these terms matter while Google is the data source, and copy keeps them out of
the Product Lead's way. With the API, people sign in and hold a server-side session
instead (ADR-018), and these terms retire with the Sheets adapter.

**Connection**:
The user's authorisation for the app to read and write the data source on their
behalf. It proves access, not identity: the app never knows who the user is.
_Avoid_: Login, sign-in, account

**Connect**:
To grant the app access through Google's consent popup, starting a session.
_Avoid_: Log in, sign in

**Disconnect**:
To end the session, revoking access where possible and forgetting every roadmap read
under it. With pending edits it asks first: keep them for the next connection, discard
them, or cancel (ADR-012).
_Avoid_: Log out, sign out

**Session**:
The period during which the app holds a valid access token. It ends by disconnecting or by
expiring.

**Expired session**:
A session whose access token has lapsed or was rejected by the data source; the user
reconnects to continue.
_Avoid_: Logged out, timed out

**Reconnect**:
To connect again after an expired session, usually without a fresh consent screen.

**Renew**:
To extend a session before it ends, in one click ("Stay connected"), without a consent
screen. The roadmaps on screen stay; a renewal that fails leaves the session to expire.
_Avoid_: Refresh (the app holds no refresh token), extend

**Session warning**:
The dialog two minutes before a session ends, counting down and offering to renew the
session or disconnect.
_Avoid_: Timeout, logout warning

**Access token**:
The short-lived credential that lets the app read and write the data source during a
session. It lives in memory only and is never stored, logged or put in a URL.
_Avoid_: Session token, key

**Auth-scoped data**:
Anything read under a session, which is cleared when the session is disconnected and
refetched after it is renewed. Pending edits are not auth-scoped data: Disconnect keeps
or discards them as the Product Lead chooses (ADR-012).

### Problems

**Problem kind**:
The category of a failure to read roadmaps (unauthenticated, forbidden, not found, rate
limited, network, invalid response, invalid data, unknown), from which the interface
chooses its message and whether to offer Retry. _Invalid data_ means the data source
answered but its content is not in the agreed format, so the remedy is to fix it, not to
retry (ADR-009).
_Avoid_: Error code, status

**Retryable problem**:
A problem kind that may succeed if tried again: rate limited, network, or a data-source
failure on its side.

**Forbidden**:
The connected account may not read the connected spreadsheet; the remedy is to ask its
owner for access.
_Avoid_: Unauthorised (which means an expired session)

### Languages

**Supported language**:
A language the whole interface is offered in: English (`en`) and Welsh (`cy`).

**Catalogue**:
The complete set of interface copy for one supported language; every catalogue has the
same keys.
_Avoid_: Translation file, strings file

**Endonym**:
A language's name in that language ("English", "Cymraeg"), used by the language switcher.

### Delivery

**Record**:
A backlog item: a story (`STY-<nnn>`), a defect (`DEF-<nnn>`) or a chore (`CHO-<nnn>`),
filed under an epic (`EPC-<nnn>`) or standalone.
_Avoid_: Ticket, issue, task

**Story**:
A record that delivers a user-visible outcome, written as numbered scenarios.

**Defect**:
A record of behaviour that contradicts a written scenario or an ADR.
_Avoid_: Bug report

**Chore**:
A record with no user-facing change, such as a refactor, a dependency or a CI change.

**Epic**:
A group of related records with a shared assessment and sequencing.

**Owner**:
The person who decides product behaviour, accepts ADRs, triages defects and merges PRs.
_Avoid_: Product owner, stakeholder
