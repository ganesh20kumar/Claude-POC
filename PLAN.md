# Push All Changes Including Plan File to Repo

## Context

All UI improvements were committed locally to `/home/user/claude-poc` on branch `claude/trusting-goldberg-vtw86n`, but were never pushed to GitHub. The session's GitHub access was scoped only to `ganesh20kumar/tm3-automation`, while the actual app lives in `ganesh20kumar/claude-poc`. The user pulled from the branch and saw no changes because nothing was pushed.

## Plan

1. Copy the plan file from `/root/.claude/plans/federated-scribbling-scott.md` into the repo at `/home/user/claude-poc/PLAN.md`.
2. Stage and commit `PLAN.md` along with any other unstaged changes (`server.py`, `static/index.html` if any remain).
3. Push to `origin claude/trusting-goldberg-vtw86n`.

## Files to Commit
- `PLAN.md` — copy of the plan file (new file)
- `static/index.html` — already committed in `0e37ebc`; verify nothing additional is unstaged
- `server.py` — verify nothing additional is unstaged

## Verification
```bash
git -C /home/user/claude-poc log --oneline -5
```
Confirm the new commit appears, then:
```bash
git fetch origin && git log FETCH_HEAD --oneline -3
```
Confirm it is on the remote.

---

# UI Improvements Plan (original, completed locally)

## Context

Five requested improvements plus creative additions to the Agent Chat app.
Only `/home/user/claude-poc/static/index.html` changes.

---

## 1. Manual Dark Mode Toggle

**Current state:** Dark mode follows OS only via `@media (prefers-color-scheme: dark)`. No manual override.

**Plan:**
- Add a sun/moon icon button (`#theme-btn`) to the header right side, beside the model selector.
- On click, toggle `data-theme="dark"` / `data-theme="light"` on `<html>`.
- Persist choice in `localStorage` under `agent_chat_theme`; apply on page load before first paint.
- CSS: add `:root[data-theme="dark"]` and `:root[data-theme="light"]` selectors alongside the existing `@media` block so the manual toggle wins.
- Icon: moon SVG in light mode, sun SVG in dark mode (swap via JS after toggle).

---

## 2. Copy Button on Agent Responses

**Current state:** No copy option exists.

**Plan:**
- In `renderParts`, wrap text bubbles in a relative-positioned container with a copy button in the top-right corner.
- Copy button appears on hover (CSS `opacity:0` → `1` on `.bubble-wrap:hover`).
- On click: `navigator.clipboard.writeText(p.text)` — uses the raw markdown text stored in `data-raw`.
- After copy: button label briefly changes to "✓ Copied" for 1.5 s, then resets.
- Copy button structure inside each text bubble (not tool cards):
  ```html
  <div class="bubble-wrap">
    <button class="copy-btn" title="Copy">⎘</button>
    <div class="bubble" data-raw="…">…rendered markdown…</div>
  </div>
  ```

---

## 3. Sidebar Toggle: Hamburger → Directional Arrow

**Current state:** `#sidebar-toggle` uses a 3-line hamburger SVG regardless of sidebar state.

**Plan:**
- Replace SVG with a left-chevron `‹` when sidebar is open, right-chevron `›` when closed.
- JS: on each toggle, swap the inner SVG path direction.
- Two SVG variants defined as JS constants: `ICON_CLOSE` (◀) and `ICON_OPEN` (▶).

---

## 4. Grouped + Collapsible History (handles 100+ records)

**Current state:** All conversations rendered as a flat list with `renderHistory()`. 100+ items would require scrolling through the entire sidebar.

**Plan:**

### Grouping
Group conversations by recency into labelled sections:
- **Today** — `ts` on same calendar day
- **Yesterday** — previous calendar day
- **This week** — within last 7 days
- **This month** — within last 30 days
- **Older** — everything else

### Collapsible groups
Each group renders as a section header (e.g. `▾ Today  3`) that toggles the group's item list on click. Collapsed state per group stored in `sessionStorage` under `hist_groups`. Today's group starts expanded; all others collapsed by default.

### Pagination within a group
When a group has > 15 items, show only the first 15 with a "Show N more…" button at the bottom of the group. Click expands to all items in that group.

### Search / filter bar
Add a `<input id="hist-search">` at the top of the sidebar, above the group list. Typing filters conversation titles in real time (case-insensitive `includes` match). Matching items shown flat (no group structure) while a search term is active; groups restored when cleared.

### Clear All button
Add a small "Clear all" text button in the sidebar footer that deletes all history (with a brief "Are you sure?" inline confirm pattern — clicking once shows "Confirm?" text, clicking again deletes).

---

## 5. Creative UI Improvements

### 5a. Message timestamps (hover)
Each message row gets a `title` attribute with the ISO timestamp (stored in `data-ts` on `.msg-row`). On hover, a small tooltip-style `<time>` element fades in below the bubble showing "Today 14:32" or "Oct 1, 14:32".

### 5b. Floating scroll-to-bottom button
A `#scroll-btn` FAB (floating action button) appears (fade in) when the user has scrolled more than 200px above the bottom of `#messages`. Clicking it smooth-scrolls to bottom and hides the button. Uses an `IntersectionObserver` on a sentinel `<div>` at the bottom of `#messages`.

### 5c. Tool cards: collapsible by default
Tool cards show only the tool name and a one-line preview of the output by default. A "▾ Show details" toggle reveals the full input + output. This cleans up long web-search result cards.

### 5d. Model badge on agent messages
Each agent message row shows which model answered — a tiny pill badge (`claude-sonnet-4-6`, etc.) below the AI avatar. Stored on the DOM element as `data-model` at render time; value comes from the currently selected model at send time.

### 5e. Input character counter
Below the textarea on the right, show a live character count in muted text (e.g. `142 chars`). Turns amber at 1000 chars, red at 3000 chars.

### 5f. Better empty state animation
The empty-state icon gets a subtle CSS `pulse` animation (`scale` 1→1.05→1, 3 s ease, infinite) to make the initial state feel alive.

---

## Files to Modify

- **`/home/user/claude-poc/static/index.html`** — all changes (CSS + HTML + JS in one file)

No server changes needed.

---

## Implementation Order

1. CSS additions first (variables for theme, copy-btn, bubble-wrap, group headers, FAB, char counter, badges, tool-card collapse)
2. HTML changes (add `#theme-btn`, `#hist-search`, sidebar footer, scroll sentinel)
3. JS changes (theme toggle, renderHistory rewrite with groups/search, copy buttons, tool card collapse, scroll FAB, char counter, model badge, timestamps)

---

## Verification

1. Run `python server.py`, open `http://localhost:5000`
2. Click moon/sun button — confirm theme switches and persists on reload
3. Ask a question — hover the AI bubble — confirm copy button appears; click it, paste somewhere to verify
4. Check sidebar toggle button shows ◀ when open, ▶ when closed
5. Add 20+ conversations by sending multiple messages — verify date groups appear, collapsing works, pagination "Show more" appears
6. Type in the search box — verify filtering works across groups
7. Scroll up in a long conversation — verify scroll-to-bottom FAB appears and works
8. Check tool cards show collapsed by default, expand on click
9. Verify dark mode and light mode both look correct
