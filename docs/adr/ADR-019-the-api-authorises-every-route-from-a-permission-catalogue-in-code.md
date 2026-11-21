# ADR-019: The API authorises every route by a declared policy, from a permission catalogue in code and three shipped roles

- Status: Accepted — owner, 2026-11-21; drafted from the owner's answers in the
  identity and authorisation grilling (2026-11-21) and their answers to its review;
  the options chosen are marked ✅.
- Date: 2026-11-21

## Context

ADR-015 holds who may do what in the database and has the API check it on every
request, while row-level security isolates tenants (ADR-015 Option 20). It fixes the
outline: a fixed permission catalogue in the application, bundled into roles each tenant
defines, with room for a direct grant later (ADR-015 Option 19); editing a roadmap needs
an assignment to it (ADR-015 Option 13), except for admins, who edit every roadmap
(ADR-015 Option 23); an admin assigns leads, or an assigned lead adds co-leads (ADR-015
Option 16); any Product Lead adds a roadmap and is assigned to it (ADR-015 Option 17);
the Product Lead role holds `roadmaps:create` and `tags:edit`, and every other
permission is admin-only by default (ADR-015 Option 22); platform operators create
tenants (ADR-015 Option 21). It left the catalogue, the roles and how the API enforces
them to this ADR (ADR-015 Option 35). Who a person is, and their session, are ADR-018's.
The analysis behind both is
[identity and authorisation](../analysis/identity-and-authorisation.md).

## Decision

### The catalogue and the shipped roles

- **The permission catalogue is a typed enumeration in the API's code.** A tenant's
  roles name permissions, validated against the catalogue when written and at start-up;
  an unknown name fails closed and is logged, never silently ignored.

  | Permission           | Allows                                                                 |
  | -------------------- | ---------------------------------------------------------------------- |
  | `roadmaps:create`    | adding a roadmap; an adder holding `roadmaps:edit` is assigned to it   |
  | `roadmaps:edit`      | editing, retiring and reinstating a roadmap the holder is assigned to  |
  | `roadmaps:edit-any`  | the same on every roadmap, without an assignment                       |
  | `roadmaps:publish`   | publishing and unpublishing a roadmap the holder may edit              |
  | `tags:edit`          | adding a tag and renaming one                                          |
  | `lists:edit`         | families, categories and organisations; retiring and reinstating a tag |
  | `members:manage`     | inviting, ending a membership, changing roles, the access review       |
  | `assignments:manage` | assigning and unassigning anyone on any roadmap                        |
  | `content:redact`     | redaction (ADR-015 Options 9, 34; the database checks it too)          |
  | `tenant:settings`    | the tenant's name and public address                                   |

- **Three shipped roles** (Options 4, 5, 15):
  - **Admin**: every permission except `roadmaps:edit`, which `roadmaps:edit-any`
    covers.
  - **Product Lead**: `roadmaps:create`, `roadmaps:edit`, `roadmaps:publish` and
    `tags:edit`.
  - **Viewer**: no permission.
- **Tenants cannot edit roles yet** (Option 3): every tenant gets the shipped roles; the
  schema already holds roles as rows naming permissions, so a role editor (and a
  `roles:manage` permission) arrives when a tenant needs one, as ADR-015 Option 19
  allows.

### What members and assigned leads may do

- **Every member reads their tenant's current roadmaps** (Option 1): each roadmap's
  published version, its shared draft and its history, read-only. Retired roadmaps are
  the exception, seen by their assigned leads and by holders of `roadmaps:edit-any`
  (ADR-015 Option 33). A scratch stays its owner's alone (ADR-015).
- **Editing a roadmap** (its scratch, saving, discarding, restoring a past version,
  retiring and reinstating it; Options 6, 15) needs `roadmaps:edit` and an assignment to
  it, or `roadmaps:edit-any`. **An assigned lead**, everywhere in this ADR, is a member
  with an assignment to the roadmap who holds `roadmaps:edit` now: a member demoted to
  Viewer keeps their assignment rows but is no longer an assigned lead, so cannot edit,
  see the roadmap once retired, or add co-leads. An admin adding a roadmap is not
  assigned to it, since `roadmaps:edit-any` already covers it.
- **Publishing and unpublishing need `roadmaps:publish` and the right to edit that
  roadmap** (Option 2): any assigned Product Lead publishes, as today. Publishing stays
  its own permission and its own change set, so a later approval step (a second person
  approving a publish) is a role change and a new rule, not a rework.
- **Assignments** (Options 7, 16): only a member holding `roadmaps:edit` can be
  assigned. Holders of `assignments:manage` assign and unassign anyone; an assigned lead
  adds a co-lead from those members (ADR-015 Option 16) and may unassign themselves,
  even as the last lead, after which only holders of `roadmaps:edit-any` edit that
  roadmap; a lead cannot unassign another lead.
- **Lists are the admins'** (Option 8): families, categories and organisations need
  `lists:edit`, as does retiring or reinstating a tag; a Product Lead adds and renames
  tags (`tags:edit`) and chooses a roadmap's family and category. On the API, the
  Families page is read-only for a Product Lead.
- **Members** (Option 9): every member sees the members' names, their roles and who
  leads which roadmap; email addresses, last sign-in, invitations and the access review
  need `members:manage`.

### Keeping access current

- **A tenant keeps at least one admin** (Option 10): the API refuses to end the last
  admin's membership or remove their role, checked under the access scope's lock. If the
  only admin's account is gone, a platform job invites the replacement the tenant names
  (ADR-018). Tenants are advised to keep two.
- **An access review every six months** (Option 11): the members page shows each
  member's last sign-in; admins are prompted to confirm or remove each member, and each
  confirmation is an access change set. People who move between NHS Wales organisations
  keep their Entra account, so nothing else ends an old membership.

### Platform operators

- **Platform operations are CLI commands run as Cloud Run jobs that only named Google
  Cloud principals may start** (Option 12): creating a tenant and inviting its first
  admin, inviting a replacement admin, disabling a person (sign-in refused and sessions
  revoked across every tenant), removing an identity (ADR-018) and redaction
  escalations.
- **Each job is one command**: its entrypoint is that command, so overriding its
  arguments at run time cannot run another; it validates its arguments, and writes them
  with its execution ID to the platform audit log. Run-time overrides also cover
  environment variables, so a job takes no security-relevant setting from its
  environment (configuration is baked into the image or mounted as a secret) and refuses
  to start when an unexpected variable is set. Operators hold only the role that runs a
  job with overrides, on each job, never one that can change a job's image or command;
  whoever can deploy is in effect a platform operator, and a change to a job raises an
  alert (EPC-023). Platform jobs run under their own
  service account and database role, separate from the API's and the purge jobs', and
  write only through platform definer procedures.
- **Who ran a job is taken from Cloud Audit Logs**, not typed on the command line:
  starting a Cloud Run job is logged as a Data Access write, so those logs are enabled
  and exported to a retention-locked bucket (EPC-023), where the execution ID joins to
  the principal. An access change a job makes (an invitation) is an access change set by
  a platform actor named for the job's execution.
- **No operator web surface and no impersonation**, not even read-only: support works
  from what the person shares on screen. An operator holds no tenant access unless
  invited like anyone else.

### Enforcement

- **Every route declares exactly one policy** (Option 13): public; signed in (a person,
  no tenant); a member of the named tenant; or a named permission in the named tenant.
  Object checks (an assignment, a retired roadmap) sit in services on top. A custom
  route class refuses to register an API route without a policy, so the app refuses to
  start; a test walks every route the app holds, of every type (mounted static files
  included), and fails on one it cannot classify. The public routes are a reviewed list
  in code.
- **Every tenant route names its tenant** in the request (Option 14): the editor's
  address carries it, and one dependency checks it against the person's membership and
  sets it for the transaction (ADR-017). A non-member naming a tenant gets 404, as an ID
  from another tenant does, so a tenant's existence does not leak. A tenant held in the
  session is rejected: a switch in one tab would silently retarget another, and new
  items could land in the wrong tenant.
- **Row-level security isolates tenants** beneath the repositories' tenant filter.
- **Tests prove it**:
  - every route has a policy, and the public list matches the reviewed list;
  - a role-by-route matrix, generated from the catalogue and the shipped roles: Admin,
    Product Lead, Viewer, a member with no role, a non-member and an anonymous caller,
    against every route's expected answer;
  - a cross-tenant sweep: every tenant route called with another tenant's IDs answers
    404 and changes nothing;
  - an unassigned Product Lead is refused every edit route, a Viewer every write, and a
    Viewer can never be assigned;
  - the last admin cannot be removed;
  - every table has row-level security enabled and forced, with a policy; the
    application's role does not bypass it, owns nothing, and cannot change the platform
    audit log or history.
- **Lint**: permission names are referenced only through the enumeration, never as
  string literals outside it (a test over the API's source, beside ADR-017's ruff and
  import-linter).

## Consequences

- **The Families page changes for Product Leads** when the editor switches to the API:
  today any connected lead manages families and categories; then it is read-only for
  them, and admins manage the lists.
- **A Viewer is a new kind of user** the editor has not had: everything is read-only
  for them, and the editor's switch-over epic designs that.
- **The editor's interface shows permissions as hints only**; the API decides.
- **ADR-015 is amended** (its _ADR-018 and ADR-019 amendments_):
  - ADR-015 Option 22: the Product Lead role also holds `roadmaps:edit` and `roadmaps:publish`;
    an admin's right to edit every roadmap (ADR-015 Option 23) is the `roadmaps:edit-any`
    permission.
  - ADR-015 Option 16: a co-lead must hold `roadmaps:edit`; a lead may unassign themselves, even
    as the last lead.
  - ADR-015 Option 33: retired roadmaps are seen by their assigned leads and holders of
    `roadmaps:edit-any`, and retired or reinstated by holders of `roadmaps:edit`
    assigned to them and by holders of `roadmaps:edit-any`.
  - _People, access and permissions_: the last-admin rule and the access review.
  - _Roles, operation and data protection_: a platform role and service account for
    platform jobs.
  - _Tenancy_: beside the existing tenant procedure, the closed list of definer
    functions gains the platform procedures (issue an operator invitation, disable a
    person and revoke their sessions, remove an identity).
- **Follow-on work**: EPC-022's schema story for people, memberships, roles and
  assignments with the enforcement suite above; the editor's new editing model (a later
  epic) builds the screens for members, assignments, the access review and the Viewer.

## Options (owner's choice marked ✅, 2026-11-21)

1. **Who reads** — ✅ every member reads every current roadmap, draft and history.
   Lost: drafts to assignees only (harder co-ordination across products); assigned
   roadmaps only.
2. **Publishing** — ✅ any assigned lead, as today, keeping room for a second person to
   approve later. Lost: an admin-only publish permission; a two-person rule now.
3. **Editable roles** — ✅ the shipped roles only at first. Lost: a role editor before
   anyone needs one.
4. **A read-only role** — ✅ Viewer. Lost: making onlookers Product Leads.
5. **Product Lead** — ✅ `roadmaps:create` and `tags:edit` (ADR-015 Option 22), plus
   `roadmaps:publish` (Option 2) and `roadmaps:edit` (Option 15).
6. **Retiring a roadmap** — ✅ assigned leads and admins. Lost: admins only; leads
   retire and admins reinstate.
7. **Unassigning** — ✅ a lead unassigns themselves, even as the last; an admin
   unassigns anyone. Lost: any lead removing any co-lead (a lead could lock a co-lead
   out); admins only.
8. **Lists** — ✅ admin-only, the Families page read-only for leads (ADR-015 Option
   22); `tags:edit` adds and renames, retiring a tag is an admin's. Lost: leads editing
   families and categories, as today; leads retiring tags; leads only adding tags.
9. **The member list** — ✅ names and roles to all, the rest to admins. Lost: admins
   only, with leads picking co-leads by exact search.
10. **The last admin** — ✅ a guard, and an operator job invites a replacement. Lost:
    requiring two admins.
11. **Movers** — ✅ last sign-in shown and a six-monthly review. Lost: memberships
    lapsing when unused (surprises occasional editors); last sign-in only.
12. **Platform operators** — ✅ IAM-gated jobs, no web surface, no impersonation. Lost:
    an operator website (a public route to the most privileged actions); a read-only
    "view as" (breaks need-to-know).
13. **Proving every route is authorised** — ✅ fail-closed route declarations and
    generated tests. Lost: per-route guards and spot tests.
14. **Which tenant a request is for** — ✅ every request names it. Lost: held in the
    session.
15. **Editing as a permission** — ✅ `roadmaps:edit` with an assignment, and
    `roadmaps:edit-any` for admins (review answer). Lost: a role change ending
    assignments, with admins' edit-all a rule on the role's name (breaks when roles
    become editable).
16. **Co-leads** — ✅ an assigned lead adds co-leads, from members holding
    `roadmaps:edit` only (review answer). Lost: admins only (amends ADR-015 Option 16).
