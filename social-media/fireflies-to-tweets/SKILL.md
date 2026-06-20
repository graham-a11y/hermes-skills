---
name: fireflies-to-tweets
description: Turn Fireflies meeting transcripts into audience-resonant tweets and threads. Uses the 4-System AI Content Engine (Strategy → Research → Performance → Assets) reoriented around reader transformation — AI runs the infrastructure, human approves the output.
version: 3.2.0
metadata:
  hermes:
    tags: [fireflies, twitter, xurl, content, meeting-notes, threads, personal-branding]
    config:
      - key: fireflies.api_key
        description: "Fireflies GraphQL API key (bearer token)"
        prompt: "Enter your Fireflies API key"
        url: "https://docs.fireflies.ai/fundamentals/authorization"
      - key: content_brain
        description: "Your Content Brain — the output from the Strategy Engine self-interview. Paste the full strategy Claude/ChatGPT generated (origin story, positioning, ICP, frameworks, what you're known for, audience psychographics, and 20-50 of your best-performing posts as gold-standard examples)."
        prompt: "Paste your Content Brain strategy"
---

# Fireflies → Tweets (4-System Engine, Audience-First)

Turn meeting transcripts into tweets that resonate — not just tweets that are "on brand." The 4-System framework (Strategy → Research → Performance → Assets) still runs the infrastructure, but **every gate now optimizes for reader transformation first, brand alignment second.**

**Core principle:** If your audience wouldn't feel seen, challenged, helped, or impressed — don't post it. Brand alignment is necessary but insufficient.

**What changed in v3.2:**
- **Interview Panel** — four AI interviewers (Ferriss, Swisher, Stern, Hormozi) push deeper on extracted insights before drafting. Uncovers emotional truth, stakes, and the part nobody said out loud.
- **Writer's Council replaces single-judge scoring** — Shaan Puri, Morgan Housel, Julian Shapiro, and David Perell each review the draft through their lens. Iterate until Council average ≥8/10.
- **Persistent `content-lessons.md`** — rejection/edit learnings saved to a durable file that compounds across sessions and overrides the style guide when it conflicts.
- **Raw interview file** — interview Q&A saved to `/tmp/fireflies_interview.md` as sacred source material.

**What changed in v3.1:**
- **Post-Draft Quality Gate** — the actual draft is scored 0-1 against the 5-criteria rubric before it reaches you. Below 0.7? Auto-regenerated.
- **Gold standard examples** — Content Brain now includes 20-50 of your best-performing posts as ground truth for the judge
- **Rejection learning** — when you edit or reject a draft, the reason feeds back into the quality system
- Quality score displayed in the review step so you can see it as a number, not a feeling

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

## Step 5b — Interview Panel: Go Deeper Before You Draft

**Do not start generating angles yet.** The transcript gave you what people said. Now push deeper on what they *meant* — the emotional truth, the stakes, the part nobody in the room wanted to say out loud.

Four interviewers interrogate the extracted insights. Each asks 2-3 questions from their specific lens. Run them sequentially — each builds on the answers from the previous.

### Tim Ferriss — Systems & Frameworks Lens
> "I don't care about the story unless there's a system inside it."

Ask 2-3 questions like:
- "If you had to teach someone else to do this in 3 steps, what are they?"
- "What's the decision rule or heuristic you use here that most people don't?"
- "Forget the outcome — what was the *process* that led to it?"

**Goal:** Extract a repeatable framework or decision rule the reader can steal.

### Kara Swisher — Bullshit Detector Lens
> "That's the PR version. What really happened?"

Ask 2-3 questions like:
- "What's the part nobody in that room wanted to say out loud?"
- "Who disagreed with this decision and why? What did they actually say?"
- "If this had failed, what would the post-mortem have been?"

**Goal:** Extract the tension, conflict, or unvarnished truth behind the clean narrative.

### Howard Stern — Emotional Honesty Lens
> "Forget the strategy. What did you actually *feel*?"

Ask 2-3 questions like:
- "When that happened — were you scared? Pissed off? Relieved? Give me the real emotion."
- "What was the worst moment? The one where you thought 'this might actually fail'?"
- "Is there a moment you're still not over? Something that still bothers you?"

**Goal:** Extract the emotional anchor — the feeling the reader will recognize in themselves.

### Alex Hormozi — Business Stakes Lens
> "What did this cost? Don't give me theory — give me the number."

Ask 2-3 questions like:
- "What did this cost in dollars? Time? Opportunities you passed on?"
- "What was the upside if this worked? What was the actual downside if it didn't?"
- "If you had to bet your own money on this working again, what odds would you give it?"

**Goal:** Extract concrete stakes — numbers, tradeoffs, real-world consequences.

### How to use the interview output

The answers become additional source material for the draft. They live alongside your extracted signal. The interview often surfaces the *best* hook — the emotional moment Stern extracts or the bullshit Kara exposes is frequently more resonant than anything in the original transcript.

Save the full interview Q&A to `/tmp/fireflies_interview.md`. This is your raw file — sacred, never paraphrased away. All drafts pull from it.

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

## Step 7b — Writer's Council: Multi-Persona Quality Gate (THE EVAL LOOP)

**Do not present the draft to the user until it passes the Council.** A single judge has blind spots. Four reviewers, each with a different lens, catch failure modes a single rubric misses.

The Council reviews the draft in parallel. Each outputs:

```
Score: X/10
What works: [one line]
What breaks: [one line]
Must-fix (editorial): [actionable change the machine can make right now]
Info gap (needs you): [question only the creator can answer; route back to Interview Panel if needed]
```

### Shaan Puri — Shareability & Novelty Lens
> "The hook either stops a scroll or it doesn't. Would anyone DM this to a friend?"

Shaan scores whether the draft is surprising, quotable, or shareable — or just correct. He's ruthless about the hook: if the first tweet doesn't create a "wait, what?" reaction, the draft fails regardless of substance.

### Morgan Housel — Audience Pain & Emotional Truth Lens
> "Does this tell a real story or just make a point? Would a reader feel something or just nod?"

Morgan scores whether the draft reaches an actual human emotion — fear, relief, recognition, anger. If the reader would finish it and feel nothing, Morgan's score tanks. He's the bullshit detector for emotional claims that don't land.

### Julian Shapiro — Voice Fit Lens
> "Would you actually say that sentence out loud? That phrase right there — that's AI. Rewrite it like you're texting."

Julian scores whether every sentence passes the "read it aloud" test. He flags any sentence that sounds like ChatGPT, any phrase from the forbidden list, any moment where the voice slips from human to corporate. He compares against the gold-standard examples in Content Brain.

### David Perell — Specific Proof Lens
> "This paragraph is vibes. Where's the number? Where's the moment? Show me the receipt or cut the claim."

David scores whether claims are backed by concrete evidence from the transcript. He flags every assertion that isn't anchored in a specific number, quote, decision, or moment. "Most people believe X" without a source = instant penalty.

### The Threshold

After all four score, compute the average:

- **Council average ≥ 8/10** → Pass. Present to user with individual scores.
- **Council average 6–7/10** → Flagged. Present WITH scores + Council notes and a warning: *"⚠️ Council scored this [X]/10. [Lowest-scoring reviewer] flagged: [what broke]. Want me to revise against their notes or see it anyway?"*
- **Council average < 6/10** → Hard fail. Do NOT show the user. Read every Council member's "Must-fix (editorial)" notes and revise. Re-submit to Council. Iterate until ≥8/10 or 3 revision rounds — whichever comes first. If 3 rounds and still below 8, surface the best attempt with scores and explain what's stuck.

### Why multi-persona beats single-judge

A single rubric applied by one judge catches what that judge is trained to see. Four judges with competing priorities catch each other's blind spots. Shaan might love a hook that Morgan flags as emotionally hollow. Julian might approve voice that David shreds for lacking proof. The averaging is the signal — a draft that scores high across all four is genuinely solid. A draft with one 9 and three 5s has a problem the 9 didn't see.

### Comparison against gold standard

Before finalizing, each Council member compares the draft against the gold-standard examples in Content Brain (your 20-50 best-performing posts). If the draft would look out of place next to your bangers, that should be reflected in the scores — particularly Julian's and David's. The gold standard is ground truth.

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

📊 Writer's Council: [X.X]/10
   Shaan (Share/Novelty): X/10 | Morgan (Pain/Emotion): X/10
   Julian (Voice): X/10 | David (Proof): X/10

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

### If the user edits or rejects:

When the user edits the draft or says "no, try again," **save the reason as a learning signal.** Ask them what specifically didn't work, then feed that back:
- If they rewrote the hook → the old hook's angle category (pain-first, contrarian, story) scored lower in practice than on paper. Adjust future angle scoring.
- If they cut a tweet → that tweet type (frameworks, behind-the-scenes, etc.) may not resonate. Feed this back into the Research Engine patterns.
- If they said "this sounds generic" → update the Voice constraints with the specific phrases they flagged.
- If they rejected the whole thing → save the transcript + rejected draft as a reference for what NOT to do.

This closes the loop: every rejection makes the system harder to fool next time.

### Persistent lessons file

After each session, save confirmed lessons to `~/.hermes/skills/social-media/fireflies-to-tweets/content-lessons.md`. This file compounds across sessions and overrides the style guide when it conflicts. Every future first draft starts smarter.

Format each lesson as:
```
## Lesson: [what we learned]
**Source:** [session date] — [transcript title]
**Trigger:** [what the user said when editing/rejecting]
**Rule:** [how this changes future behavior]
**Overrides:** [which style guide / voice constraint this modifies]
```

When loading the skill, scan `content-lessons.md` and apply any rules that override the voice constraints or style guide. Lessons are cumulative — if a lesson contradicts an earlier one, the newer lesson wins.

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
- **Skipping the quality gate:** The Writer's Council is not optional. "It feels good" is not a score. If you can't produce individual scores from all four reviewers with specific fix notes, the draft hasn't been evaluated — it's been vibed. Council it or don't ship it.
- **Ignoring the gold standard:** If the draft would look out of place next to the user's 20-50 best posts, that should tank the Voice and Shareability scores. The gold standard exists to prevent exactly this.
- **Skipping the Interview Panel:** The transcript only contains what was said. The Interview Panel extracts what was *meant*. Without it, emotional truth and stakes stay buried. Run the panel even when it feels redundant — it often surfaces the best hook.
- **Treating the Council as optional:** Multi-persona review is the system. A draft that one reviewer loves and three flag is broken in ways the one didn't see. Council average is the real score — not the high-water mark.

---

## Verification

After posting:
1. `xurl read $TWEET_1_ID` — verify the post is live
2. Confirm thread renders correctly (replies nested)
3. Share thread URL: `https://x.com/USERNAME/status/$TWEET_1_ID`
4. **Save the Council scores** — record all four reviewer scores from the gate. This builds your quality baseline over time so you can spot when quality is rising or degrading, and which reviewer is consistently the hardest to please (that's your blind spot).
5. **Post-mortem (7 days later):** Review performance against both hypotheses. Did the reader feel what you predicted? Did the business metric move? Feed learnings back into the Research Engine *and* the gold standard — if a post outperformed your best historical content, it becomes a new gold-standard example. If it underperformed despite scoring high on the rubric, your rubric may have a blind spot.
