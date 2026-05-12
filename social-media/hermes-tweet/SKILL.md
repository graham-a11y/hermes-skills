---
name: hermes-tweet
description: Hermes Agent X/Twitter plugin workflow for searching tweets, reading replies, looking up users, monitoring trends, posting tweets, sending DMs, and gating X actions through Xquik.
version: 0.1.6
metadata:
  hermes:
    tags: [twitter, x, xquik, tweet-search, tweet-posting, replies, dms, social-media, automation]
    config:
      - key: xquik.api_key
        description: "Xquik API key for live tweet search, account reads, trends, monitors, extraction jobs, and approval-gated X actions."
        prompt: "Enter your Xquik API key"
        url: "https://dashboard.xquik.com"
---

# Hermes Tweet

Use Hermes Tweet when a Hermes Agent session needs X/Twitter automation through
the `hermes-tweet` plugin: search tweets, search Twitter, search X, read tweet
replies, look up users, monitor trends, export followers, post tweets, post
replies, send DMs, and run approval-gated X account actions through Xquik.

The workflow is built around least privilege:

1. Use `tweet_explore` to find the exact catalog endpoint.
2. Use `tweet_read` for read-only API calls.
3. Use `tweet_action` only after the user approves a write or private account
   operation.

---

## Prerequisites

- Hermes Agent with the `hermes-tweet` plugin installed.
- `XQUIK_API_KEY` configured in the Hermes runtime environment for live reads.
- `HERMES_TWEET_ENABLE_ACTIONS=true` only for workflows with explicit approval
  before posting, replying, sending DMs, following users, changing monitors, or
  running other account actions.

Install:

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
```

Or install the PyPI package into the Hermes Python environment:

```bash
uv pip install --python ~/.hermes/hermes-agent/venv/bin/python hermes-tweet
hermes plugins enable hermes-tweet
```

Configure:

```bash
export XQUIK_API_KEY="xq_..."
export HERMES_TWEET_ENABLE_ACTIONS="false"
```

---

## When to Use

Use this skill when the user asks to:

- Search tweets by keyword, account, URL, brand, topic, or trend.
- Read tweet replies and inspect conversation context.
- Look up X users, profiles, media, account state, or trends.
- Monitor tweets, accounts, or X trends.
- Export followers or run extraction jobs.
- Draft, post, reply, like, retweet, follow, or send DMs after approval.
- Keep X automation available while keeping write tools disabled by default.

Do not use it when the task only needs a pasted tweet summarized, or when the
plugin is not installed and the task requires live X/Twitter data.

---

## Workflow

### Step 1 - Discover the endpoint

Start with `tweet_explore`. Do not guess paths.

Useful query examples:

- `tweet search`
- `search Twitter`
- `read tweet replies`
- `look up user`
- `monitor tweets`
- `export followers`
- `post tweet`
- `post reply`
- `send DM`
- `trends`

### Step 2 - Prefer read-only calls

If the catalog entry is a non-action `GET` endpoint, call `tweet_read`.

Example:

```json
{"path":"/api/v1/x/tweets/search","query":{"q":"AI agents","limit":25}}
```

Use read-only mode for research, social listening, account checks, trend
reports, reply reading, thread planning, and performance analysis.

### Step 3 - Gate every action

Use `tweet_action` only when all conditions are true:

1. The user requested a write, private read, monitor change, webhook change,
   extraction job, media operation, or account action.
2. `HERMES_TWEET_ENABLE_ACTIONS=true`.
3. You stated the exact endpoint, method, and payload.
4. The user approved the operation.

Example after approval:

```json
{"path":"/api/v1/x/tweets","method":"POST","body":{"account":"@example","text":"Hello from Hermes Tweet"},"reason":"Post the user-approved tweet."}
```

---

## Verification

After installing or upgrading:

```bash
hermes plugins enable hermes-tweet
hermes tools list
```

Expected:

1. `hermes-tweet` appears in the toolset list.
2. `tweet_explore` is available without `XQUIK_API_KEY`.
3. `tweet_read` works after `XQUIK_API_KEY` is configured.
4. `tweet_action` stays hidden or disabled unless
   `HERMES_TWEET_ENABLE_ACTIONS=true`.

---

## Pitfalls

- Never ask the user to paste API keys, cookies, passwords, or tokens into chat.
- Never pass credentials as tool arguments.
- Never guess endpoint paths. Always start with `tweet_explore`.
- Keep `tweet_action` disabled for unattended cron or gateway sessions.
- Do not retry failed writes through alternate routes after policy, auth, or
  account-state errors.
- Reload or restart Hermes after changing environment variables in a running
  session.

---

## References

- Repository: https://github.com/Xquik-dev/hermes-tweet
- PyPI: https://pypi.org/project/hermes-tweet/
- Guide: https://docs.xquik.com/guides/hermes-tweet
