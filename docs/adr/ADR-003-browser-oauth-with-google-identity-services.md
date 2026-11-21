# ADR-003: Browser OAuth with Google Identity Services token model

- Status: Superseded by ADR-018 for the API data source; stands for the Sheets adapter
  until the deployed editor switches to the API (owner, 2026-11-21)
- Date: 2026-11-10 (amended in STY-003: port in `domain/auth/`, codes split, prompt policy;
  in STY-017: renewal from `connected`, the clock check on returning to the tab)

## Context

The app is static (no backend), so it cannot hold a client secret or refresh tokens. It
needs an OAuth access token with scope `https://www.googleapis.com/auth/spreadsheets`
(full scope chosen deliberately for future editing/duplication).

## Decision

- Use the GIS **token model** (`google.accounts.oauth2.initTokenClient`) loaded from
  `https://accounts.google.com/gsi/client`. Types from `@types/google.accounts`.
- `infrastructure/google-identity/`:
  - `load-gis-script.ts` — idempotent, promise-memoised script loader with timeout and
    clean failure (retry possible after failure).
  - `google-auth-client.ts` — implements the app-level `AuthClient` interface on top of GIS.
    It loads GIS on creation. Each `connect()` then creates a token client for that
    attempt and calls `requestAccessToken()` on it, both synchronously inside the click
    (`initTokenClient` is synchronous). A client per attempt binds Google's callbacks to
    that attempt, so a late response from an abandoned attempt cannot complete a newer one.
  - Only this folder may use the `google` global (ESLint `no-restricted-globals`).
- `domain/auth/auth-client.ts` owns the app-level port, like `RoadmapRepository`
  (STY-003 amendment: infrastructure implements it and must not import `features/`, ADR-002):
  - `AuthClient` interface: `getSnapshot()`, `subscribe()`, `connect()`, `disconnect()`,
    `getAccessToken()`, `reportUnauthenticated()` (called when an API returns 401). Members
    are standalone functions, safe to pass detached.
  - `AuthState` discriminated union: `initializing` | `ready` (not connected) |
    `connecting` | `connected` (with `expiresAt`) | `expired` | `error`. Errors are typed
    **codes**, never English prose — copy is chosen by the UI via i18n (ADR-008):
    - `error` carries a failure code: `script-load-failed`, `access-denied`,
      `scope-not-granted` or `unknown`.
    - `ready` and `expired` may carry a `lastError` cancellation code (`popup-closed`,
      `popup-blocked`) from an abandoned attempt.
      The token itself is **not** part of the snapshot exposed to React.
- `features/auth/` bridges it to React: `AuthProvider` + `useAuth()` via
  `useSyncExternalStore`, plus a fake client for component tests.
- `connect()` is only ever invoked from a user gesture (button click), so the popup is not
  blocked. Prompt policy: `prompt: ''` when reconnecting from `expired`; `prompt: 'consent'`
  after `scope-not-granted` (re-asking for an unticked scope needs it); otherwise GIS's
  default (`select_account`). If GIS failed to load, `connect()` retries the load instead
  and the user clicks again once `ready` (an async load would lose the user gesture).
- Token held in a closure/private field in memory. Never persisted, never logged.
- Expiry: schedule a transition to `expired` 60 s before Google's expiry (`expiresAt`
  already includes this skew; a grant no longer than the skew fails as `unknown`);
  `getAccessToken()` also checks the clock, because timers are throttled in background tabs. Also transition on API 401 via `reportUnauthenticated()`. The UI offers "Reconnect". No
  refresh tokens, no silent background re-auth loops.
- Popup closed / failed to open (`error_callback`) -> back to `expired` (when reconnecting)
  or `ready`, with a `lastError` code; other `error_callback` types and OAuth `error`
  responses -> `error` state (`access_denied` -> `access-denied`, others -> `unknown`).
  Token responses are untrusted and parsed with Zod (`expires_in` is a number at runtime but
  a string in the typings). Also verify the granted scope with
  `google.accounts.oauth2.hasGrantedAllScopes`. Each attempt settles once; callbacks for any
  other attempt (after a cancel, disconnect or dispose) are ignored, and a stale token is not
  revoked, because revocation would also end a newer grant for the same account.
- `disconnect()` revokes the token (`google.accounts.oauth2.revoke`) if one is still held,
  clears memory, and the app removes all auth-scoped query data
  (`queryClient.removeQueries`, wired through the client's `onDisconnect` option).
- We never claim to know who the user is: the token proves authorisation, not identity.
  The header says "Google connected" to a screen reader only (STY-056 D3), never a name
  or email.

### STY-017 amendments

- **Renewal.** `connect()` is also accepted from `connected`, as a `connected → connected`
  transition, so no consumer of `AuthState` handles a new state (STY-017 D2):
  - It asks with `prompt: ''`. STY-017's spike against the real Google (D3) showed this
    renews a still-valid token in one click: a popup flashes and closes itself, with no
    consent screen for an account that has consented.
  - The session stays `connected`, token and timer included, while Google answers; there
    is no `connecting` state, so the page never flashes or reloads.
  - Success replaces the token and the expiry timer and publishes a new `connected` with a
    later `expiresAt`. The old token is not revoked: that would end the new grant too.
  - Any failure or cancellation keeps the session until its `expiresAt` and records an
    optional `lastError` (an `AuthErrorCode`) on `connected`.
  - Only one renewal runs at a time. Expiry, a 401 or `disconnect()` abandons a renewal
    still in progress, and its late callbacks are ignored.
  - It is still only ever started from a click ("Stay connected" in the session warning),
    so the "no silent background re-auth" rule above stands.
- **Returning to the tab.** The client also re-checks the clock on `visibilitychange` and
  expires a session whose `expiresAt` has passed. Timers are throttled in background tabs
  and paused while the device sleeps, so the expiry timer can fire late.

### STY-023 amendments

- **A late 401 from a write.** A write is never cancelled when its session ends, unlike
  a read, so its 401 can arrive after a reconnect or renewal. It expires the session only
  while the session it was sent in is still current: the query client remembers each
  mutation's session (`currentSession`, the connected `expiresAt`) and ignores the 401
  otherwise.

## Consequences

- Users renew roughly hourly, in one click, from the warning two minutes before the
  session ends (STY-017); otherwise they reconnect after it ends. Both are acceptable for
  this phase.
- The full spreadsheets scope is sensitive and may require Google OAuth verification for
  external, published apps (documented in README).
