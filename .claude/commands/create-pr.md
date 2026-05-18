Create a GitHub pull request for the current branch.

## Steps

1. Run the following in parallel:
   - `git status` — confirm there are no unstaged changes that should be committed first
   - `git log main..HEAD --oneline` — list commits on this branch vs main
   - `git diff main...HEAD --stat` — summarise files changed

2. Analyse the commits and diff to understand what this PR does and why.

3. Draft the PR using the rules below.

4. Run:
   ```
   gh pr create \
     --base main \
     --assignee SerxUp \
     --title "<title>" \
     --body "$(cat <<'EOF'
   <body>
   EOF
   )"
   ```

5. Return the PR URL.

---

## PR title rules

- Imperative mood, present tense ("Add", "Fix", "Refactor" — not "Added" or "Adding")
- ≤ 60 characters
- No trailing period
- No ticket numbers, branch names, or dates
- Must summarise *what* the PR achieves, not how

Good: `Add audio-only download option`
Bad:  `feat/audio-only: added support for audio only downloads (#42)`

## PR body rules

Use exactly this template — no extra sections, no fluff:

```
## What

<1–3 bullet points. Each starts with a verb. State the concrete change.>

## Why

<1–3 sentences. The motivation or problem being solved. Skip if obvious from What.>

## Test plan

<Bulleted checklist of what to verify manually or via tests. Be specific.>

```

### Body style

- Bullets use `-` not `*`
- No bold headers inside bullet text
- No "This PR" phrasing
- Skip the **Why** section only if the motivation is truly self-evident from **What**
- Test plan items must be actionable (e.g. "Run `pytest`", "Open the app and download a URL", "Check the config file is written to the correct path")
- Keep the total body under ~300 words
