---
name: fireflies-to-tweets
description: Turn Fireflies meeting transcripts into audience-resonant tweets and threads. Uses the 4-System AI Content Engine (Strategy → Research → Performance → Assets) reoriented around reader transformation — AI runs the infrastructure, human approves the output.
version: 3.0.0
metadata:
  hermes:
    tags: [fireflies, twitter, xurl, content, meeting-notes, threads, personal-branding]
    config:
      - key: fireflies.api_key
        description: "Fireflies GraphQL API key (bearer token)"
        prompt: "Enter your Fireflies API key"
        url: "https://docs.fireflies.ai/fundamentals/authorization"
      - key: content_brain
        description: "Your Content Brain — the output from the Strategy Engine self-interview. Paste the full strategy Claude/ChatGPT generated (origin story, positioning, ICP, frameworks, what you're known for, and audience psychographics)."
        prompt: "Paste your Content Brain strategy"
---

# Fireflies → Tweets (4-System Engine, Audience-First)

Turn meeting transcripts into tweets that resonate — not just tweets that are "on brand." The 4-System framework (Strategy → Research → Performance → Assets) still runs the infrastructure, but **every gate now optimizes for reader transformation first, brand alignment second.**

**Core principle:** If your audience wouldn't feel seen, challenged, helped, or impressed — don't post it. Brand alignment is necessary but insufficient.

**What changed in v3.0:**
- Mandatory Audience Resonance Brief before drafting
- Research Engine runs BEFORE extraction (not after)
- 3 candidate angles scored against audience criteria — draft only the winner
- Flexible formats: single tweet, thread, or carousel
- Operational voice constraints (forbidden phrases, not vague "don't sound like ChatGPT")
- Audience-centric hypotheses alongside creator-centric ones

---

## Prerequisites

- [xurl](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) installed and authenticated (`xurl auth status` shows a valid app)
- Fireflies API key (set via `hermes skills config fireflies-to-tweets` or env var `FIREFLIES_API_KEY`)
- **Content Brain configured** — run `hermes skills config fireflies-to-tweets` and paste your Content Brain strategy into the `content_brain` field. The Content Brain should now include audience psychographics (fears, desires, status anxieties, decisions they're wrestling with). Without this, the skill cannot run the Audience Resonance Brief.

---

## The 4 Systems (Audience-First)

| System | What it does | Key audience question |
|--------|-------------|----------------------|
| **Strategy Engine** | Filter through Content Brain — brand fit AND audience fit | "Will this make our reader feel something?" |
| **Research Engine** | Pulls live X data BEFORE extraction — directs you to what resonates | "What do they actually engage with?" |
| **Performance Engine** | Every post gets a reader hypothesis AND a business hypothesis | "Why would they share, reply, or remember this?" |
| **Asset Builder** | Visual that strengthens the reader's takeaway | "Does the image help them understand or feel the point?" |

---

## Step 0 — Load the Content Brain (Strategy Engine)

**Before touching any transcript, load the user's Content Brain.** If `content_brain` is not configured, **stop and tell the user to run `hermes skills config fireflies-to-tweets`.** Without it, you're guessing.

The Content Brain now answers both brand AND audience questions:

**Brand axis:**
- Origin Story, Known For, Offer, Frameworks

**Audience axis (NEW — required for Audience Resonance Brief):**
- ICP psychographics: What are they afraid of? What do they secretly believe? What decisions are they putting off?
- What status games do they play?
- What pain are they currently experiencing that they'd pay to solve?
- What conventional wisdom do they suspect is wrong but can't articulate?

**How to use it:** Every extraction must pass TWO filters:
1. Brand: "Does this reinforce what we're known for?"
2. Audience: "Does this touch a real pain, fear, desire, or decision our reader is experiencing?"

If it fails either, skip it.

---

## Step 1 — Find the Transcript

The user may give you:
- A Fireflies transcript URL (e.g., `https://app.fireflies.ai/view/meeting-name::ID` — extract the ID after `::`)
- A meeting title to search for
- A transcript ID directly

Search recent transcripts if needed:

```bash
curl -s -X POST https://api.fireflies.ai/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $FIREFLIES_API_KEY" \
  -d '{"query": "query { transcripts { id title date } }"}'
```

---

## Step 2 — Fetch the Full Transcript

```bash
curl -s -X POST https://api.fireflies.ai/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $FIREFLIES_API_KEY" \
  -d '{
    "query": "query Transcript($id: String!) {
      transcript(id: $id) {
        title date duration participants
        sentences { index speaker_name text }
        summary {
          keywords action_items overview bullet_gist
          topics_discussed transcript_chapters
        }
      }
    }",
    "variables": {"id": "THE_TRANSCRIPT_ID"}
  }' > /tmp/fireflies_transcript.json
```

---

## Step 3 — Research Engine: Pull Performance Data FIRST

**Run BEFORE extraction.** Let data tell you what to hunt for.

### 3A — Get user ID

```bash
xurl whoami | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])"
```

Save as `$USER_ID`.

### 3B — Pull recent tweets (wider sample)

Pull up to 100 tweets (paginate if needed). This gives a meaningful signal, not a noisy 25-tweet sample:

```bash
xurl "/2/users/$USER_ID/tweets?max_results=100&tweet.fields=public_metrics,created_at,entities,attachments&exclude=retweets,replies" > /tmp/recent_tweets.json
```

### 3C — Analyze resonance (not just engagement)

```bash
python3 << 'PYEOF'
import json, re

with open("/tmp/recent_tweets.json") as f:
    data = json.load(f)

tweets = data.get("data", [])
if not tweets:
    print("⚠️ No recent tweets found. Falling back to universal signal principles.")
    exit(0)

# --- Score engagement (weighted composite) ---
scored = []
for t in tweets:
    m = t.get("public_metrics", {})
    score = (
        m.get("like_count", 0) * 1.0 +
        m.get("retweet_count", 0) * 2.0 +
        m.get("reply_count", 0) * 1.5 +
        m.get("quote_count", 0) * 3.0 +
        m.get("impression_count", 0) * 0.001 +
        m.get("bookmark_count", 0) * 2.0  # bookmarks = saved value
    )
    scored.append({"id": t["id"], "text": t["text"], "score": round(score, 1), "metrics": m, "created_at": t.get("created_at", "")})

scored.sort(key=lambda x: x["score"], reverse=True)

# --- TOP / BOTTOM ---
print("🏆 TOP 5 — what resonates:")
for i, t in enumerate(scored[:5], 1):
    print(f"  {i}. [{t['score']}] {t['text'][:140]}")

print("\n📉 BOTTOM 5 — what people scroll past:")
for i, t in enumerate(scored[-5:], 1):
    print(f"  {i}. [{t['score']}] {t['text'][:140]}")

# --- Richer pattern detection (categories, not just keywords) ---
top_texts = " ".join(t["text"] for t in scored[:10])
bottom_texts = " ".join(t["text"] for t in scored[-10:])

print("\n🔍 RESONANCE PATTERNS:")

patterns = {
    "Decisions/reversals/pivots": ["we decided", "we're killing", "we're stopping", "we're pivoting", "we shut down", "no longer"],
    "Questions/engagement hooks": ["agree or disagree", "what do you", "what's your", "am i wrong", "hot take"],
    "Numbers/metrics/specifics": ["$", "%", "0", "x", "months", "weeks", "years"],
    "Vulnerability/mistakes/lessons": ["mistake", "failed", "wrong", "learned", "embarrassing", "i was wrong", "confession"],
    "Contrarian/against-the-grain": ["unpopular opinion", "most people", "everyone says", "the truth is", "nobody talks about"],
    "Frameworks/how-to": ["how to", "framework", "system", "process", "method", "playbook"],
    "Stories/behind-the-scenes": ["today i", "this morning", "a client", "we just", "behind the", "how we"],
}

for label, keywords in patterns.items():
    if any(w in top_texts.lower() for w in keywords):
        print(f"  ✅ {label} — RESONATES (overrepresented in top performers)")
    elif any(w in bottom_texts.lower() for w in keywords):
        print(f"  ⚠️ {label} — FALLS FLAT (overrepresented in bottom performers)")

# --- Hook format detection ---
print("\n🎣 HOOK FORMAT ANALYSIS:")
hook_categories = {
    "Number-led": re.findall(r'^\d', top_texts, re.MULTILINE),
    "Question-led": re.findall(r'^["\']?(what|how|why|when|who|is|are|does|can|should|would|do)', top_texts, re.MULTILINE | re.IGNORECASE),
    "Contrarian statement": re.findall(r'(most people|everyone|nobody|unpopular|hot take|i don.t care)', top_texts, re.IGNORECASE),
    "Story opener": re.findall(r'(today|yesterday|this week|last month|a client|we just|i just)', top_texts, re.IGNORECASE),
}
for fmt, matches in hook_categories.items():
    if matches:
        print(f"  ✅ {fmt}: {len(matches)} top-performing hooks")

# --- Topic clusters ---
print("\n📊 TOPIC CLUSTERS (top 10 tweets):")
topic_keywords = {
    "pricing/money/revenue": ["$", "revenue", "price", "pricing", "money", "cost", "profit", "margin"],
    "hiring/team/people": ["hire", "hiring", "team", "fired", "employee", "talent", "culture"],
    "product/engineering": ["product", "build", "ship", "feature", "code", "engineer", "launch"],
    "sales/marketing/growth": ["sales", "marketing", "growth", "customer", "pipeline", "lead", "conversion"],
    "strategy/decisions": ["decided", "strategy", "pivot", "kill", "focus", "priority"],
}
for topic, keywords in topic_keywords.items():
    count = sum(1 for kw in keywords if kw in top_texts.lower())
    if count >= 2:
        print(f"  ✅ {topic}: strongly present in top performers")

print("\n💡 DIRECTIVE: Hunt the patterns that won. Avoid the patterns that flopped.")
PYEOF
```

### 3D — Apply the patterns to your extraction plan

Before reading the transcript, summarize what the data tells you in 2-3 sentences. Example: *"My top tweets are number-led contrarian takes about pricing. Bottom tweets are abstract strategy posts without specifics. I'll hunt for pricing data, reversals, and controversial decisions — and skip anything that sounds like 'we discussed Q3 planning.'"*

---

## Step 4 — Audience Resonance Brief (REQUIRED GATE)

**Do not skip this. Do not extract a single insight until this is written.**

Using the Content Brain (audience psychographics) + Research Engine findings, write a 5-line brief:

```
Audience segment:
Their current pain or tension:
The belief this post challenges:
The useful reframe or emotional payoff:
Why they would share, reply, or remember it:
```

Then apply the **hard gate** — state the core idea in this format:

```
"For [audience], this matters because [specific pain/stakes].
Most of them believe [old belief].
This transcript reveals [new belief]."
```

**If you cannot fill every field in both the brief AND the hard gate with specificity, do not proceed.** A vague brief produces vague content. Go back to the transcript and Content Brain until you have sharp answers.

---

## Step 5 — Extract Signal (Strategy + Audience Lens)

Now read the transcript. You have your Content Brain, your research patterns, and your Audience Resonance Brief. Extract with all three lenses active.

### What to extract (minimum 5-7 points):

**A. Moments that touch audience pain/fear/desire (≥2)**
- Not "what happened in the meeting" — "what in this meeting would make our reader feel seen"
- A client's objection reveals a fear the ICP shares
- A decision reversal that challenges a belief the ICP secretly holds
- A framework that solves a problem the ICP is currently googling at 11pm

**B. Concrete specifics that serve the reader (≥2)**
- Numbers, dates, names, decisions — but only when they illuminate a pattern the reader can use
- "Sarah owns auth migration by Friday" → skip (unless the *process* of how they migrate teaches something)
- "The team killed the referral feature after 0.4% conversion over 4 months" → keep (it's a decision with a lesson)

**C. Contrarian or surprising insights (≥1)**
- Anything that goes against conventional wisdom
- Stats that surprised people in the room
- Decisions that looked wrong but worked (or looked right but failed)

**D. Emotional truth, not just information (≥1)**
- Moments of tension, relief, frustration, excitement
- "Jenna was visibly frustrated when she said..." is more resonant than "Jenna noted that..."
- The *feeling* in the room is often the most relatable part

### Anti-patterns:

- ❌ Meeting notes disguised as tweets → "We discussed Q3 priorities and aligned on timeline"
- ❌ Internal-only details → "Mike from ops will handle the migration by Thursday"
- ❌ Generic takeaways → "Key insight: alignment matters"
- ❌ Anything that passes brand filter but fails audience filter → delete it

### Golden rule of extraction:

> **Would a stranger who wasn't in this meeting feel something reading this?**

If the answer is "maybe they'd find it informative," that's not enough. Aim for: "they'd feel called out," "they'd feel relieved they're not alone," "they'd feel like they just learned a secret," or "they'd feel angry enough to reply."

---

## Step 6 — Generate 3 Candidate Angles

**Do not draft yet.** Generate 3 angles, each optimized for a different reader entry point:

1. **Pain-first:** Lead with the reader's pain/fear/tension. "You know that feeling when..." or "Most [ICP] are secretly terrified that..."

2. **Contrarian/Reframe:** Lead by challenging a belief. "Everyone says X. Here's what actually happened when we tried it."

3. **Story/Behind-the-scenes:** Lead with the specific moment. "We sat in a room for 3 hours and made one decision that will..."

### Score each angle 1-5 on:

| Criteria | Angle 1 | Angle 2 | Angle 3 |
|----------|---------|---------|---------|
| **Audience pain resonance** — how deeply does this touch a real pain/fear? | | | |
| **Novelty** — is this surprising, contrarian, or counterintuitive? | | | |
| **Specific proof** — is there concrete evidence from the transcript? | | | |
| **Voice fit** — does this sound like the user (not ChatGPT)? | | | |
| **Shareability** — would someone DM this to a colleague or quote-tweet it? | | | |

**Draft only the winner.** If two angles tie, draft the one with higher Audience Pain + Novelty.

---

## Step 7 — Draft the Winner

### Format decision

Let content dictate format — don't force a thread:

| Content shape | Best format |
|--------------|-------------|
| One sharp, self-contained insight | **Single tweet** (200-260 chars) |
| A layered argument, story, or framework | **Thread (2-8 tweets)** |
| A comparison, timeline, or before/after | **Thread + visual** |

**A single tweet does not force vagueness.** A sharp single tweet often outperforms a diluted thread. If the idea can be stated powerfully in one tweet, do that.

### Voice constraints (operational, not vague)

**Forbidden phrases:**
- "In today's fast-paced world..."
- "It's important to note that..."
- "At the end of the day..."
- "Let that sink in."
- "Here's the thing..."
- "The key takeaway is..."
- "This. So much this."
- Any sentence starting with "As a [role]..."
- "Thread 🧵" or emoji-only hooks

**Voice guidelines:**
- Sentence fragments are allowed. Write like you talk.
- Vary sentence length. Short punch. Then a longer sentence that explains why it matters. Then short again.
- Concrete over abstract. "We lost $40k" hits harder than "The cost of inaction is high."
- Bluntness is allowed when it serves the point. "This was a stupid decision and here's why" > "This decision had unexpected consequences."
- Humor is allowed but not required. Don't force jokes.
- Second person ("you") is powerful when accurate. Don't use it if you're guessing.

### Structure (for threads):

- **Tweet 1 (Hook):** The most resonant piece — a stat, a reversal, a moment. Make someone stop scrolling. Must connect to the Audience Resonance Brief.
- **Body tweets (2-6):** The substance. Each tweet should be interesting standing alone. Use the speaker's actual words where powerful.
- **Final tweet:** CTA aligned with the reader hypothesis. "Has anyone else seen this?" / "What would you have done?" / "Am I wrong about this?" — NOT "DM me for the template" unless that genuinely serves the reader.

### Content rules:

- Ground in transcript specifics, but only when they serve the reader's takeaway
- If a tweet could apply to any meeting → delete it
- Let the speakers' voices bleed through — actual quotes > paraphrasing
- The reader should feel like they overheard something they weren't supposed to hear

---

## Step 8 — Hypothesis Tagging (Performance Engine)

Every post gets two hypotheses:

**Reader hypothesis (NEW — required):**
> "The reader will [feel/think/do something] because [specific insight] touches [specific pain/belief]."

Example: *"The reader will feel relief that they're not the only one losing enterprise deals to slow compliance — and will re-examine their own deal qualification process because this transcript shows a concrete alternative."*

**Business hypothesis (from original framework):**
- **Growth** — drives new followers via novelty/contrarian takes
- **Lead Flow** — generates inbound interest via demonstrated expertise
- **Trust** — deepens credibility via vulnerability or behind-the-scenes

State both before presenting the draft.

---

## Step 9 — Generate Visual Asset (Asset Builder)

Generate a visual only if it strengthens the reader's takeaway. Skip if it's decorative.

| Content has... | Generate... |
|---------------|-------------|
| A process or workflow | Diagram / flowchart |
| A framework or mental model | Framework visual (boxes, arrows, layers) |
| A comparison or trade-off | Side-by-side — "Most people vs. what we learned" |
| A surprising stat | Concept image or bold stat card |
| A powerful quote | Quote card (speaker name + quote, minimal) |
| A decision or pivot | Timeline: old path → new path |

**Default:** Framework visual explaining the core insight as 3-5 steps.

**Max 2-3 attempts.** If generation fails, present without visuals. Content > visuals.

---

## Step 10 — Review with the User

Present the full package:

```
🧵 Draft from [Meeting Title]

👤 Reader hypothesis: [why they'd feel something]
📈 Business hypothesis: [Growth/Lead Flow/Trust]

📋 Audience Resonance Brief:
   Segment: [who]
   Pain: [what they're struggling with]
   Belief challenged: [old belief → new belief]

[1/ Tweet text]
[2/ Tweet text]
...

🖼️ Asset: [visual description or "none"]

Post this? (yes / edit / cancel)
```

**Never post without explicit user confirmation.**

---

## Step 11 — Post via xurl

```bash
# Single tweet:
xurl post "Tweet text"

# Thread — post tweet 1, then reply chain:
xurl post "Tweet 1 text"
# Save ID → $TWEET_1_ID
xurl reply $TWEET_1_ID "Tweet 2 text"
# Save $TWEET_2_ID, continue chain...
```

Space posts ~2 seconds apart. If you get a 429, wait 15 minutes.

---

## Pitfalls

- **Missing Content Brain:** If `content_brain` is not configured, STOP. *"I need your Content Brain to run the Audience Resonance Brief. Run `hermes skills config fireflies-to-tweets` and paste your strategy. Without it, I can't know who we're writing for."*
- **Vague Audience Resonance Brief:** If the brief has generic answers ("they want to grow their business"), go back to the Content Brain and transcript. Specificity is non-negotiable.
- **AI-sounding drafts:** If the draft uses any forbidden phrase or sounds like generic LinkedIn content, rewrite it. Use the voice constraints. The AI extracts and structures — the user's voice must survive.
- **Transcript specifics that don't serve the reader:** "Sarah will migrate auth by Friday" means nothing to readers. Only use specifics that illustrate a broader pattern, lesson, or emotional truth.
- **Forcing threads:** If the idea works as one sharp tweet, post one tweet. Threads are for layered arguments, not a default.
- **Truncated transcripts:** Long meetings (500+ sentences) may paginate. Check for cursors in the API response.
- **xurl rate limits:** Space posts. 429 = wait 15 minutes.
- **API key not found:** Guide user to `hermes skills config fireflies-to-tweets`.
- **Private transcripts:** API key must belong to a user with access.
- **Asset generation fails:** Skip visuals after 2-3 attempts. Content is the priority.
- **No hypothesis clarity:** If you can't state BOTH the reader hypothesis and business hypothesis with specificity, the draft isn't ready.

---

## Verification

After posting:
1. `xurl read $TWEET_1_ID` — verify the post is live
2. Confirm thread renders correctly (replies nested)
3. Share thread URL: `https://x.com/USERNAME/status/$TWEET_1_ID`
4. **Post-mortem (7 days later):** Review performance against both hypotheses. Did the reader feel what you predicted? Did the business metric move? Feed learnings back into the Research Engine.
