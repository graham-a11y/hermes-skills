---
name: fireflies-to-tweets
description: Turn Fireflies meeting transcripts into detailed, high-signal tweet threads using xurl. Extracts quotes, insights, and takeaways with enough depth to stand alone — no vague summaries.
version: 1.0.0
metadata:
  hermes:
    tags: [fireflies, twitter, xurl, content, meeting-notes, threads]
    config:
      - key: fireflies.api_key
        description: "Fireflies GraphQL API key (bearer token)"
        prompt: "Enter your Fireflies API key"
        url: "https://docs.fireflies.ai/fundamentals/authorization"
---

# Fireflies → Tweets

Fetch a Fireflies meeting transcript, pull out the substantive insights, and publish as tweet threads via xurl. Designed for people who want tweets with *actual detail* — direct quotes, concrete takeaways, and specifics, not platitudes.

---

## Prerequisites

- [xurl](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) installed and authenticated (`xurl auth status` shows a valid app)
- Fireflies API key (set via `hermes skills config fireflies-to-tweets` or env var `FIREFLIES_API_KEY`)

---

## Step 1 — Find the Transcript

The user may give you:
- A Fireflies transcript URL (e.g., `https://app.fireflies.ai/view/meeting-name::ID` — extract the ID after `::`)
- A meeting title to search for
- A transcript ID directly

If you need to search, list recent transcripts via the API:

```bash
curl -s -X POST https://api.fireflies.ai/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $FIREFLIES_API_KEY" \
  -d '{"query": "query { transcripts { id title date } }"}'
```

---

## Step 2 — Fetch the Full Transcript

Use the transcript ID to pull the entire transcript with sentences, summary, and analytics:

```bash
curl -s -X POST https://api.fireflies.ai/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $FIREFLIES_API_KEY" \
  -d '{
    "query": "query Transcript($id: String!) {
      transcript(id: $id) {
        title
        date
        duration
        participants
        sentences { index speaker_name text }
        summary {
          keywords
          action_items
          overview
          bullet_gist
          topics_discussed
          transcript_chapters
        }
      }
    }",
    "variables": {"id": "THE_TRANSCRIPT_ID"}
  }'
```

- `sentences` contains every spoken line with speaker attribution
- `summary` contains the AI-generated meeting summary, action items, and topics
- `duration` and `participants` give context for the tweet

**Save the full output to a temp file** so you can work with it:

```bash
curl ... > /tmp/fireflies_transcript.json
```

---

## Step 3 — Extract Content with DEPTH (this is the most important step)

The #1 complaint is tweets being too vague. **You MUST extract at least 5-7 substantive points per transcript.** Do not stop at 2-3 high-level bullets.

### What to pull out:

**A. Direct Quotes (minimum 3)**
- Find the most interesting / controversial / insightful things people actually said
- Include the speaker's name and full quote — at least 2-3 sentences of context
- Pick quotes that make sense without hearing the whole meeting

**B. Concrete Takeaways (minimum 3)**
- Not "we discussed Q3 planning" — that's useless
- Instead: "The team decided to delay the EU launch from July to September because compliance reviews are taking 3x longer than estimated"
- Include numbers, dates, names, specific decisions

**C. Surprising or Counterintuitive Insights**
- Anything that goes against conventional wisdom
- A stat that surprised people in the room
- A decision reversal or pivot

**D. Action Items with owners and deadlines**
- From `summary.action_items` — but flesh them out with context from the sentences
- "Sarah will migrate the auth service by Friday" is good. "Action item: auth migration" is bad.

### Anti-patterns to AVOID:
- ❌ "Great discussion about product strategy" → ✅ "The team is pivoting from enterprise-first to PLG because the last 3 enterprise deals each took 8+ months to close"
- ❌ "Key takeaways from our meeting" → ✅ "We're killing the referral feature. Only 12 users tried it in 4 months and conversion was 0.4%"
- ❌ "Interesting insights on hiring" → ✅ "Jenna argued we should stop doing take-home assignments — candidates spend 6 hours on them but on-site performance has zero correlation"

---

## Step 4 — Write the Tweet Thread

### Format rules:
- **Thread of 4-8 tweets** (not a single tweet — a single tweet forces you to be too vague)
- **Tweet 1: The hook.** The most surprising stat, quote, or decision. Make someone stop scrolling.
- **Tweets 2-5: The substance.** Direct quotes, specific takeaways, concrete decisions. Each tweet should stand alone as interesting.
- **Tweets 6-7: The synthesis.** What this means broadly. The bigger implication.
- **Final tweet: CTA or question.** Invite discussion. "Has anyone else seen this pattern?" / "What would you have done differently?"

### Content rules:
- Every tweet must contain at least ONE specific detail (number, name, date, direct quote, or decision)
- No filler tweets. If a tweet could apply to any meeting, delete it.
- Use the speakers' actual words in quotes where possible
- Add situational framing in tweet 1 (e.g., type of meeting and broad topic)

### Length:
- Each tweet: 200-260 characters (informational density, not fluff)
- Thread: 4-8 tweets total

---

## Step 5 — Review with the User

Before posting, show the thread to the user with a clear preview:

```
Here's the thread draft from [Meeting Title]:

1/ [Tweet text]
2/ [Tweet text]
...

Post this? (yes / edit / cancel)
```

Let them request edits before anything goes live.

---

## Step 6 — Post via xurl

Post tweets one at a time as a reply chain:

```bash
# Post tweet 1
xurl post "Tweet 1 text"
# Save the returned ID → call it $TWEET_1_ID

# Post tweet 2 as a reply to tweet 1
xurl reply $TWEET_1_ID "Tweet 2 text"
# Save $TWEET_2_ID

# Continue the chain...
xurl reply $TWEET_2_ID "Tweet 3 text"
```

**Important:** Never post without explicit user confirmation. Always show the full thread first.

---

## Pitfalls

- **Truncated transcripts:** Long meetings can have 500+ sentences. The `sentences` field may be paginated. If the response looks incomplete, check for pagination cursors in the API response.
- **xurl rate limits:** X rate-limits write endpoints. Space posts ~2 seconds apart. If you get a 429, wait 15 minutes before retrying.
- **API key not found:** If the Fireflies API key is missing, guide the user to configure it with `hermes skills config fireflies-to-tweets`.
- **Transcript ID extraction:** Fireflies URLs use `::` as separator. The ID is everything after the last `::`. Example: `https://app.fireflies.ai/view/Weekly-Sync::abc123` → ID is `abc123`.
- **Private transcripts:** The API key must belong to a user with access to the transcript. If you get an auth error, the transcript may be in a private channel.

---

## Verification

After posting, confirm:
1. `xurl read $TWEET_1_ID` — verify thread start is live
2. Check the thread renders correctly on X (replies nested properly)
3. Confirm the full thread URL with the user: `https://x.com/USERNAME/status/$TWEET_1_ID`
