# ADR-020: The editor and the API share one origin, behind edge rate limits and strict response headers; the public read has its own host

- Status: Accepted — owner, 2026-11-21; drafted from the owner's answers in the
  identity and authorisation grilling (2026-11-21); the options chosen are marked ✅.
- Date: 2026-11-21

## Context

ADR-018 keeps a person's session in a `__Host-`, `SameSite=Strict` cookie that only the
API reads. That works without credentialed CORS only if the editor's pages and the API
share an origin. Today the editor is on GitHub Pages, whose one origin is shared with
every organisation site, including the public site and its analytics script, and which
cannot set response headers (ADR-016). ADR-016 makes a custom domain a precondition of
switching the deployed editor to the API; ADR-017 opens the public read to every origin
and gave the editor's endpoints a CORS allow-list. Each Cloud Run service has its own
`*.run.app` address, a separate site on the Public Suffix List.

## Decision

- **The editor and the API share one origin in every environment** (Option 1):
  - locally, Vite's dev server proxies `/api` to the API, so the browser sees one
    `localhost` origin;
  - hosted, before the editor has its custom domain, one Cloud Run service per
    environment serves the editor's built files and the API, under one `run.app`
    address;
  - once the domain exists, the load balancer fronts that same service, and its
    `run.app` addresses are disabled.
- **The editor's endpoints send no CORS headers at all**, replacing ADR-017's
  allow-list.
- **The public read has its own host**, with open CORS and no cookies (ADR-017). Before
  the load balancer it is a second Cloud Run service from the same image, started in a
  public-only mode that serves no session or editor route. Behind the load balancer, one
  service may answer on both hosts and routes by host: session and editor routes answer
  only on the editor's host, public routes only on the public host; the load balancer
  has no default backend for a host it does not name. The API reads the `Host` header
  only, never `X-Forwarded-Host`, and its allow-list names exactly the hosts it serves,
  so a service's other addresses (legacy and tag URLs) are refused.
- **A state-changing request needs same-origin proof**: `Sec-Fetch-Site: same-origin`,
  or, where a browser sends no Fetch Metadata, an `Origin` equal to the editor's; else it
  is refused. A body must be `application/json`. The sign-in callback is the one
  state-changing `GET`, bound by its own transaction instead (ADR-018); every other
  `GET` changes nothing (tested). `SameSite=Strict` is a second layer only: a host on the
  same registrable domain is same-site, not same-origin.
- **Rate limits live at the edge** (Option 2): Cloud Armor's per-address limits on the
  sign-in routes and the public read, a CDN for the public read, and a capped instance
  count (EPC-023). The API adds only a cap on invitations created per admin, once
  invitations are emailed; unauthenticated failures go to the log, never the database
  (ADR-018).
- **Environments without the load balancer hold no real data**, since Cloud Armor's
  per-address limits need the load balancer.
- **The API sets the editor's document headers while it serves the editor's files**: a
  strict CSP (no inline script, Trusted Types trialled report-only first),
  `frame-ancestors 'none'`, HSTS, a cross-origin opener policy, a referrer policy and a
  permissions policy.
- **The API's own responses** carry `Cache-Control: no-store` on everything that is not
  public (redirects and refusals included), `nosniff`,
  `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` and a
  same-origin resource policy; a request body limit (middleware, since Starlette sets
  none); validation errors in ADR-017's envelope without the submitted input; and no
  `/docs` or live OpenAPI route in production, where the committed document serves.

## Consequences

- **One deploy carries both apps** in each environment, until and after the load
  balancer: the editor's build is part of the API's image.
- **ADR-007's GitHub Pages deployment of the editor** ends with the switch-over: the ADR
  that switches the data source supersedes it, as ADR-015 _Consequences_ sets for the
  Sheets-era ADRs; until then the deployed Sheets editor stays on GitHub Pages.
- **ADR-017 is amended** (its _ADR-020 amendments_): no CORS for the editor's endpoints; the
  API serves the editor's files and document headers; the response rules above.
- **ADR-016's custom domain** stays a precondition of switching the deployed editor to
  the API; the deployed Sheets editor stays on GitHub Pages until then.
- **EPC-023** provisions the service, the load balancer, the domain and the edge limits.

## Options (owner's choice marked ✅, 2026-11-21)

1. **Where the editor, the API and the public read live** — ✅ the editor and the API on
   one origin, one Cloud Run service before the custom domain, the public read on its
   own host. Lost: separate origins with credentialed CORS (`SameSite=None` cookies,
   preflights); a load balancer and a non-production subdomain from day one (waits on
   DNS, a load balancer per environment); Firebase Hosting rewrites (only a cookie named
   `__session` reaches the API, so no `__Host-` prefix).
2. **Rate limits** — ✅ at the edge, plus an invitation cap once invitations are emailed.
   Lost: API counters in PostgreSQL (database writes from unauthenticated traffic, more
   code, little to brute-force when tokens are 256-bit and there are no passwords).
