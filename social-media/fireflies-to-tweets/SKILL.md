---
name: fireflies-to-tweets
description: Turn Fireflies meeting transcripts into strategic, hypothesis-driven tweet threads. Uses the 4-System AI Content Engine (Strategy → Research → Performance → Assets) to extract signal, map to brand strategy, and generate visuals — AI runs the infrastructure, human approves the output.
version: 2.0.0
metadata:
  hermes:
    tags: [fireflies, twitter, xurl, content, meeting-notes, threads, personal-branding]
    config:
      - key: fireflies.api_key
        description: "Fireflies GraphQL API key (bearer token)"
        prompt: "Enter your Fireflies API key"
        url: "https://docs.fireflies.ai/fundamentals/authorization"
      - key: content_brain
        description: "Your Content Brain — the output from the Strategy Engine self-interview. Paste the full strategy Claude/ChatGPT generated (origin story, positioning, ICP, frameworks, what you're known for)."
        prompt: "Paste your Content Brain strategy"
---

# Fireflies → Tweets (4-System Engine)

Turn meeting transcripts into strategic tweet threads using the 4-System AI Content Engine framework by @WizOfEcom. AI runs the infrastructure — **you stay human on the final output.**

The framework: **Strategy Engine** (filter through your Content Brain) → **Research Engine** (leverage what's already working) → **Performance Engine** (every thread tests a hypothesis) → **Asset Builder** (visuals that strengthen the message).

**Core principle:** AI extracts, structures, and maps. The human voice, opinions, and final approval are yours.

---

## Prerequisites

- [xurl](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) installed and authenticated (`xurl auth status` shows a valid app)
- Fireflies API key (set via `hermes skills config fireflies-to-tweets` or env var `FIREFLIES_API_KEY`)
- **Content Brain configured** — run `hermes skills config fireflies-to-tweets` and paste your Content Brain strategy into the `content_brain` field. Without this, the skill falls back to generic extraction (defeats the purpose).

---

## The 4 Systems at a Glance

| System | What it does | Where it fits |
|--------|-------------|---------------|
| **Strategy Engine** | Filter every extraction through your Content Brain. If a quote doesn't reinforce what you're known for, skip it. | Step 0 |
| **Research Engine** | If you have past tweet performance data, feed it in. Otherwise, apply universal signal principles (specifics, contrarian takes, decisions). | Step 3 |
| **Performance Engine** | Every thread gets a hypothesis tag: Growth, Lead Flow, or Trust. You know what this content is *supposed* to do. | Step 4 |
| **Asset Builder** | Generate a visual asset for the thread — diagram, framework, or concept image that strengthens the message. | Step 5 |

---

## Step 0 — Load the Content Brain (Strategy Engine)

**Before touching any transcript, load the user's Content Brain.** This is the strategic filter. If `content_brain` is configured, use it. If not, **stop and tell the user to run `hermes skills config fireflies-to-tweets` to set it up.** Without it, you're guessing what matters.

The Content Brain answers:
- **Origin Story:** What moment shaped their expertise?
- **Known For:** What category do they want to own in people's minds?
- **Their Offer:** What do they actually sell/deliver?
- **ICP:** Who are they speaking to? (revenue level, problems, language)
- **Frameworks:** What unique beliefs, systems, and perspectives do they bring?

**How to use it:** Every quote, insight, or takeaway you extract from the transcript must pass this filter: *"Does this reinforce what they're known for? Does it speak to their ICP? Does it reflect their frameworks?"* If no, skip it — even if it's interesting.

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

## Step 3 — Extract Through the Strategy + Research Lens

This step combines the Strategy Engine (filter) and Research Engine (signal detection).

### Phase A: Strategic Filtering

**Load the Content Brain. Read every sentence through it.** Ask these questions for each quote/insight:

1. **Does this connect to their origin story or what they're known for?** → High signal.
2. **Does this speak directly to their ICP's problems or language?** → High signal.
3. **Does this demonstrate their frameworks or unique perspective?** → High signal.
4. **Is this a concrete decision, number, or reversal?** → Universal signal (works even without brand alignment).
5. **Is this just interesting but irrelevant to their positioning?** → Skip it. Discipline > volume.

### Phase B: Depth Extraction (minimum 5-7 points that survive the filter)

**A. Direct Quotes (minimum 3)**
- Find the most interesting / controversial / insightful things people actually said — **that align with the Content Brain**
- Include the speaker's name and full quote — at least 2-3 sentences of context
- Pick quotes that make sense without hearing the whole meeting

**B. Concrete Takeaways (minimum 3)**
- Not "we discussed Q3 planning" — that's useless
- Instead: "The team decided to delay the EU launch from July to September because compliance reviews are taking 3x longer than estimated"
- Include numbers, dates, names, specific decisions
- **Must relate to the ICP's world** — a takeaway about internal HR policy means nothing if their ICP is founders

**C. Surprising or Counterintuitive Insights**
- Anything that goes against conventional wisdom
- A stat that surprised people in the room
- A decision reversal or pivot
- **These are universal high-signal — they work even if loosely tied to brand**

**D. Action Items with owners and deadlines**
- From `summary.action_items` — flesh them out with context from the sentences
- "Sarah will migrate the auth service by Friday" is good. "Action item: auth migration" is bad.
- **Only include if the action item reveals something about HOW they operate** (their frameworks in action)

### Phase C: Research Engine Check

If the user has past tweet performance data (analytics, top/worst performers from the last 7 days), ask for it. Feed it in to identify:
- What formats are currently winning for them
- What topics their audience is responding to
- What to avoid

If no data is available, default to these universal signal principles:
- Specifics > generalizations
- Decisions > discussions
- Contrarian takes > consensus
- Frameworks > tips
- Numbers > adjectives

### Anti-patterns to AVOID:

- ❌ "Great discussion about product strategy" → ✅ "The team is pivoting from enterprise-first to PLG because the last 3 enterprise deals each took 8+ months to close"
- ❌ "Key takeaways from our meeting" → ✅ "We're killing the referral feature. Only 12 users tried it in 4 months and conversion was 0.4%"
- ❌ "Interesting insights on hiring" → ✅ "Jenna argued we should stop doing take-home assignments — candidates spend 6 hours on them but on-site performance has zero correlation"
- ❌ Any extraction that doesn't pass the Content Brain filter → **Delete it, even if it's a great quote**

---

## Step 4 — Map to Hypotheses & Write the Thread (Performance Engine)

### Hypothesis Mapping

**Every thread must be tagged with one primary hypothesis.** This forces intentionality. Before writing, decide:

| Hypothesis | Goal | What it looks like |
|-----------|------|-------------------|
| **Growth** | Drive new followers | New format, bold hooks, contrarian takes, shareable frameworks |
| **Lead Flow** | Generate inbound leads | CTA placement, case study format, problem-awareness content |
| **Trust** | Deepen credibility | Vulnerability, behind-the-scenes, personal stories, unpopular opinions |

**Map the transcript's content to the right hypothesis:**
- Client meeting where you solved a hard problem → **Lead Flow** (case study)
- Internal strategy session with controversial decisions → **Growth** (contrarian hook)
- Post-mortem or lessons learned → **Trust** (vulnerability + frameworks)
- Sales call with objections handled → **Lead Flow** (objection framework)

State the hypothesis explicitly before drafting: *"This thread tests [Growth/Lead Flow/Trust] — I hypothesize that [specific content angle] will drive [specific result] because [data or reasoning]."*

### Format Rules

- **Thread of 4-8 tweets** — a single tweet forces vagueness
- **Tweet 1: The hook.** The most surprising stat, quote, or decision. Make someone stop scrolling. Must connect to the Content Brain.
- **Tweets 2-5: The substance.** Direct quotes, specific takeaways, concrete decisions. Each tweet must stand alone as interesting.
- **Tweets 6-7: The synthesis.** What this means broadly. The bigger implication for the ICP.
- **Final tweet: CTA or question aligned with the hypothesis.** 
  - Growth → "Agree or disagree?" / "What's your take?"
  - Lead Flow → "DM me 'framework' and I'll send you the template" / "We do this for clients — link in bio"
  - Trust → "Has anyone else seen this pattern?" / "What would you have done differently?"

### Content Rules

- Every tweet must contain at least ONE specific detail (number, name, date, direct quote, or decision)
- No filler tweets. If a tweet could apply to any meeting, delete it.
- Use the speakers' actual words in quotes where possible
- Add situational framing in tweet 1 (e.g., type of meeting and broad topic)
- **The AI structures and maps — but the user's voice must survive.** Never let the thread sound like ChatGPT wrote it. Keep sentence fragments, colloquial language, and personality.

### Length

- Each tweet: 200-260 characters (informational density, not fluff)
- Thread: 4-8 tweets total

---

## Step 5 — Generate Visual Assets (Asset Builder)

Every thread gets at least one visual asset. Choose based on the content type:

### Asset Types

| Content has... | Generate... | Tool |
|---------------|-------------|------|
| A process or workflow | **Diagram / flowchart** — steps, decision points, before/after | Claude → SVG or Excalidraw |
| A framework or mental model | **Framework visual** — boxes, arrows, layers | Claude → SVG |
| A comparison or trade-off | **Side-by-side comparison** — "Most people vs. you" format | Claude → SVG |
| A surprising stat | **Concept image** — visual metaphor for the stat | ChatGPT / image_generate |
| A quote from the meeting | **Quote card** — speaker name + quote + subtle branding | Claude → SVG |
| A decision or pivot | **Timeline visual** — old path vs. new path | Claude → SVG |

**Default:** If unsure, generate a framework visual that explains the core insight from the thread as a 3-5 step diagram. This positions the user as a category owner.

### Asset Prompt Template

```
Create a [type of visual] that illustrates [core insight from thread].
- Style: [clean minimal/professional/dark mode]
- Must include: [key elements — names, numbers, steps, arrows]
- Brand colors: [from Content Brain or default to dark theme]
- Designed to stand alone on X/Twitter feed — no tiny text
```

**Do NOT spend more than 2-3 attempts on the asset.** If generation fails, present the thread without visuals. The content is the priority.

---

## Step 6 — Review with the User

Before posting, show the full package with a clear preview:

```
🧵 Thread draft from [Meeting Title]
🎯 Hypothesis: [Growth/Lead Flow/Trust] — [brief reasoning]

1/ [Tweet text]
2/ [Tweet text]
...

🖼️ Asset: [description of visual generated]

Post this? (yes / edit / cancel)
```

**The user must approve before anything goes live.** Let them request edits to the text, hypothesis, or visuals.

---

## Step 7 — Post via xurl

Post tweets one at a time as a reply chain:

```bash
# Post tweet 1 (can attach image if asset is ready)
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

- **Missing Content Brain:** If `content_brain` is not configured, STOP. Tell the user: *"I need your Content Brain to filter strategically. Run `hermes skills config fireflies-to-tweets` and paste the output from your Strategy Engine self-interview. Without it, I'm just extracting random quotes."*
- **AI-sounding threads:** If the draft sounds like ChatGPT wrote it, rewrite it. The framework says: *"Never use AI for the actual writing."* The AI extracts and structures. The voice is the user's.
- **Truncated transcripts:** Long meetings can have 500+ sentences. The `sentences` field may be paginated. If the response looks incomplete, check for pagination cursors in the API response.
- **xurl rate limits:** X rate-limits write endpoints. Space posts ~2 seconds apart. If you get a 429, wait 15 minutes before retrying.
- **API key not found:** If the Fireflies API key is missing, guide the user to configure it with `hermes skills config fireflies-to-tweets`.
- **Transcript ID extraction:** Fireflies URLs use `::` as separator. The ID is everything after the last `::`. Example: `https://app.fireflies.ai/view/Weekly-Sync::abc123` → ID is `abc123`.
- **Private transcripts:** The API key must belong to a user with access to the transcript. If you get an auth error, the transcript may be in a private channel.
- **Asset generation fails:** Don't block on visuals. If generation fails after 2-3 attempts, present the thread without assets. Content > visuals.
- **No hypothesis clarity:** If you can't clearly state what hypothesis a thread is testing, the thread isn't ready. Every thread must earn its hypothesis tag.

---

## Verification

After posting, confirm:
1. `xurl read $TWEET_1_ID` — verify thread start is live
2. Check the thread renders correctly on X (replies nested properly)
3. Confirm the full thread URL with the user: `https://x.com/USERNAME/status/$TWEET_1_ID`
4. **Post-mortem (optional but recommended):** After 7 days, offer to review the thread's performance against its hypothesis. This closes the Research Engine loop.
