# One Tuscany Trip, Costed by Hand: The Tokenomics of an AI Travel Agent

*Primary research and calculation document behind [The Hidden Tokenomics of an AI Travel Agent](tokenomics_study.md), the tokenomics study that accompanies the Substack article "AI Can Plan Your Trip. Can It Get Paid for It?" Every number in the study is derived here, and [tuscany_tokenomics_calculator.py](tuscany_tokenomics_calculator.py) reproduces every sum.*

---

In the main article I argued that the hard part of an AI travel app isn't the demo. It's the economics. These notes put numbers on that claim.

Instead of an abstract "cost per token", I followed one realistic trip, four friends planning Tuscany, through every model call, search query and booking. Model prices are public Gemini API list prices (30 Sep 2026). Everything else is a written-down assumption, so you can disagree with any of them and redo the sums.

## The short version

- **A naive AI planning agent, one with no cost engineering, costs about 15 cents per question on a frontier model, or about $12 for an 80-question trip plan.** It isn't one answer per question: the agent calls tools, rereads the whole conversation several times, and pays for every live search.
- Switching everything to the cheapest model only gets to about $3.35, and hurts quality on the hard questions.
- **Even an engineered build needs about 1 in 15 serious planners to book through the app just to break even** (about 1 in 10 once infrastructure, support and errors are counted). The naive agent needs 40–56% of planners to book.
- **The trip itself makes money.** In-trip help costs about $2 over a 4-day trip and could earn about $27 in activity and transport commissions.

Token burn is an engineering problem. Conversion is the business problem.

---

## About the numbers

- **Prices are public.** Model and grounding prices are Gemini API list prices as of 30 September 2026, re-checked on 2 October 2026 ([Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)). The one price I couldn't verify, a direct Maps call, is labelled as an assumption.
- **Everything else is a stated assumption.** That includes turns, tokens per turn, conversion and commissions. Every assumption is collected in the [assumptions register](#appendix-a-assumptions-register), so you can swap in your own.
- **Every sum is shown.** Nothing here comes from a black-box simulator. You can redo each step with a calculator, or run [tuscany_tokenomics_calculator.py](tuscany_tokenomics_calculator.py), which prints every step below.
- **Rounding.** Each line is worked out from the rounded numbers shown above it, so every sum can be redone exactly from what is on the page. Treat the headline figures as "about".
- **One simplification.** Every model call in a turn is counted with that turn's full tool results, even the first call, which runs before any tool has answered. This slightly overstates input from A1 onward, so the figures err on the high side.
- **Not included:** salaries, and cloud, network and hosting costs outside the clearly marked infrastructure placeholder in sections 5 and 6.

**One rule throughout.** Every cost is worked out for one average turn, then multiplied by the number of turns it takes to plan the trip:

```
cost of one average turn × 80 turns = cost of the planned trip
```

**Where the 80 turns come from.** The 80 is an assumption about the example trip in section 1, not a measured figure:

- A **turn** is one question from Maya, the lead planner, plus the agent's whole reply, however many model calls that reply takes.
- She plans in **4 sessions**, one per stage: inspiration, shortlist, validation and pre-booking.
- Each session runs to **20 turns**: her main questions, plus the follow-ups each answer prompts.
- 4 sessions × 20 turns = **80 turns**, for one planner who takes the trip all the way to pre-booking. Her friends and one-off visitors chat too; section 5 adds their turns on top.

Section 1 explains why 4 and why 20, and what changes if you pick other numbers.

The 80 stays fixed. Each step changes only one thing about the "average turn", so every number can be traced to the step before it.

### Prices used ($ per 1M tokens)

| Model | Role here | Input | Output | Cached input |
|---|---|---|---|---|
| Gemini 3.1 Pro (Preview), prompts up to 200k tokens | Frontier | $2.00 | $12.00 | $0.20 |
| Gemini 3.8 Flash (list price from 1 Jan 2027) | Mid tier | $1.50 | $7.50 | $0.15 |
| Gemini 3.1 Flash-Lite | Small | $0.25 | $1.50 | $0.025 |

- **Grounding with Google Search or Maps:** $14 per 1,000 search queries ($0.014 each), billed per query executed. The first 5,000 a month are free across Gemini 3 models. These notes ignore that allowance: it is worth $70 a month in total, which is small next to a real product's search bill.
- **Priority tier:** 1.8× the standard price, for lower latency (for example, Pro input is $3.60 instead of $2.00). Section 6 uses it.
- **Gemini 3.8 Live (voice):** $0.005 per minute of audio in and $0.018 per minute out. Section 6 uses it.
- **Explicit context caching:** an extra storage fee per 1M tokens per hour, from $1.00 on Flash-Lite to $4.50 on Pro.
- **Gemini 3.8 Flash promotion:** $0.75 / $3.75 until 31 December 2026, then the list price above. The list price is used so the numbers don't flatter the build.
- **Preview status:** Gemini 3.1 Pro is a Preview model, so its price can change.

---

## 1. The example: four friends take a trip to Tuscany, Maya plans it

**The trip.** Four friends in their late 20s. Maya, the lead planner, does most of the chatting. They want:

- 4 nights based in Florence, in 2 hotel rooms, at about €150 per room per night
- day trips to Chianti (a wine tour) and Siena
- a neighbourhood with late-night bars that is still easy to walk home from

**The conversation.** Planning a trip isn't one question. It runs over 4 sessions of 20 turns each, so **80 turns**. A turn is one question from Maya plus the agent's whole reply, including every model call behind it:

| Session | What Maya asks (examples) | What the agent does |
|---|---|---|
| 1. Inspiration | "Where should 4 friends base themselves in Tuscany in May?" · "Florence or a countryside villa?" | Compares bases, asks about budget and vibe |
| 2. Shortlist | "Which Florence area is best for late nights: Santo Spirito or Santa Croce?" · "Car or train for Chianti?" | Searches reviews and neighbourhood info, sums up the trade-offs |
| 3. Validation | "Is the Uffizi open on Monday?" · "Can we drive into the centre with a rental car?" · "Trains to Siena?" | Looks up live opening hours, ZTL (restricted traffic zone) rules and timetables |
| 4. Pre-booking | "Compare these 5 hotels for 2 rooms" · "Final 4-day plan" · "Split the budget 4 ways" | Fetches prices, drafts the itinerary, works out the split |

Maya's three friends also open the shared plan and ask their own questions. Section 5 adds them.

**Why 4 sessions of 20 turns.** Both numbers are assumptions, not measurements:

- **4 sessions:** one per stage in the table. A group trip is rarely settled in one sitting. Maya comes back once her friends have weighed in, so sessions can be days apart, and each one starts with a fresh history.
- **20 turns per session:** the table lists only a few example questions per session. Most answers prompt follow-ups ("and the other one?", "anything cheaper?", "what if it rains?"), so a handful of real questions per stage soon becomes about 20 turns.

The two numbers don't work the same way in the sums:

- **Sessions are a straight multiplier.** 2 sessions instead of 4 would halve every per-trip cost.
- **Turns per session count twice.** They multiply the trip cost, and they set how much history each turn resends. Turn 1 of a session resends no earlier turns and turn 20 resends 19, so the average turn resends 9.5 (section 2). Shorter sessions therefore mean fewer turns *and* cheaper ones. From B1 onward, compaction caps the history, so only the multiplier is left.

*How to check it:* log sessions per planned trip and turns per session in a real product (section 9). To try other values, change `SESSIONS` and `TURNS_PER_SESSION` at the top of the [calculator](tuscany_tokenomics_calculator.py) and rerun it.

### One turn, dissected

**Session 3, turn 10.** Maya asks: *"Is the Uffizi open on Monday, and can we drive into the centre with our rental car?"*

What the model receives:

- system prompt and Maya's profile: **4,000** tokens
- tool results (opening hours, ZTL page): **6,000** tokens
- the 9 earlier turns of this session, at 1,500 each: **13,500** tokens
- **total input: 23,500 tokens**

**Where the 6,000 tool tokens come from.** Two tools run, and both return raw text that is pasted straight into the prompt. Google's docs put one Gemini token at about 4 characters of English ([token docs](https://ai.google.dev/gemini-api/docs/tokens)). JSON, full of brackets and field names, packs fewer characters per token; these notes assume about 3.

```
Uffizi place details (raw JSON: address, weekly hours,
  holiday closures, 5 review snippets)  ≈ 9,000 chars ÷ 3 ≈ 3,000 tokens
ZTL rules: the top 3 web results,
  about 4,000 characters of text each   ≈ 12,000 chars ÷ 4 ≈ 3,000 tokens
tool results this turn                                    ≈ 6,000 tokens
```

This is an estimate, and it varies by turn:

- A turn with no tools adds 0.
- A "compare 5 hotels" turn, at about 1,200 tokens per raw hotel record, adds about 6,000.
- A turn that pastes full review pages can exceed 10,000.

So 6,000 is a middle value for a tool-heavy planning chat.

*How to check it:* pass a real tool response to Gemini's `countTokens` endpoint, or log `usage_metadata.prompt_token_count` with and without the tool result. Lever B1 later trims this to 2,500 by sending only the fields the answer needs.

What the model sends back: **2,000** tokens, counting its hidden "thinking". Reasoning models bill thinking tokens as output.

Cost on Gemini 3.1 Pro:

```
input      23,500 × $2  / 1M = $0.047
output      2,000 × $12 / 1M = $0.024
grounding   1 search query   = $0.014
                       turn  = $0.085
```

That is about 8.5 cents for one question, if the model is called once; section 3 shows why a real agent pays about 15 cents. The history is what grows: turn 1 sends 10,000 input tokens, and turn 20 sends 38,500, almost 4 times as many. Each turn grows in a straight line, but because every turn resends everything before it, **the cost of the whole conversation grows quadratically**. Long, indecisive planning chats are the most expensive users you have.

---

## 2. The back-of-envelope number: $6.92 per trip

Each session starts with a fresh history. Across 20 turns, the earlier turns being resent average 9.5 × 1,500 = **14,250** tokens.

```
average turn input  = 4,000 system + 6,000 tools + 14,250 history = 24,250 tokens
average turn output = 2,000 tokens

input      24,250 × $2  / 1M = $0.0485
output      2,000 × $12 / 1M = $0.0240
grounding   1 × $0.014       = $0.0140
average turn                 = $0.0865
× 80 turns                   = $6.92 per planned trip
```

That is 80 × 24,250 = **1.94M input tokens** and 80 × 2,000 = 0.16M output tokens per planned trip.

This is the number most "AI is expensive" takes stop at. **It is too low for a real agent, and too high for a well-built one.** It assumes one model call per question, which misses how agents actually work: section 3 raises it to $12.22, which these notes call the **naive agent**. It also leaves out standard engineering: section 4 lowers it to $2.02, the **engineered build**.

> **Don't compare models on this basis.** The back-of-envelope undercounts both tokens and searches, so it makes cheap models look cheaper than they really are. Section 3 compares the models on the naive agent.

---

## 3. Four costs the back-of-envelope misses

Each step builds on the one before it.

**A1. One turn is several model calls**
An agent doesn't answer in one shot. It decides which tool to call, reads the result, sometimes calls another tool, then writes the answer. Assume **2.5 model calls per turn**: 1.5 tool calls on average, then 1 call that writes the answer. Each call resends the context, and each tool call writes a request plus some thinking, about 400 output tokens.

```
input      24,250 × 2.5 = 60,625 tokens × $2  / 1M     = $0.1213
output     2,000 + 1.5 × 400 = 2,600 tokens × $12 / 1M = $0.0312
grounding  1 × $0.014                                  = $0.0140
average turn  $0.1213 + $0.0312 + $0.0140 = $0.1665  →  × 80 = $13.32 per trip
```

**A2. Tool results stay in the history**
The back-of-envelope adds only the chat text (1,500 tokens) to the history. In most agent frameworks, the tool results stay in the transcript too. Every earlier turn therefore leaves **7,500** tokens behind (1,500 chat + 6,000 tool results), and the average history becomes 9.5 × 7,500 = 71,250 tokens.

```
input per call = 4,000 + 6,000 + 71,250 = 81,250
× 2.5 calls    = 203,125 tokens × $2 / 1M = $0.4063
output (unchanged)                          $0.0312
grounding (unchanged)                       $0.0140
average turn  $0.4063 + $0.0312 + $0.0140 = $0.4515  →  × 80 = $36.12 per trip
```

This number is alarming on its own. It is only realistic for a build with no caching, and caching is now often applied by default. That is the next step.

**A3. Most of that input is cached**
Within a turn, calls 2 and 3 resend almost exactly what call 1 sent. Gemini applies implicit caching to repeated prompt prefixes ([context caching docs](https://ai.google.dev/gemini-api/docs/caching)), and cached input is billed at 10% of the normal input price. Assume **85%** of input is billed at the cached price.

```
effective input price = 15% × $2.00 + 85% × $0.20 = $0.47 per 1M
input   203,125 × $0.47 / 1M = $0.0955
average turn  $0.0955 + $0.0312 output + $0.0140 grounding = $0.1407  →  × 80 = $11.26 per trip
```

**A4. Grounding is billed per search query, and Maps calls cost extra**
Gemini bills grounding per search query executed, and one grounded prompt can run several queries. Assume about **1.5 queries** per grounded prompt, at $0.014 each. Separately, direct Maps Platform calls (travel times, place details) are their own bill. Assume about **0.3 calls per turn**, at roughly $0.017 each (an assumed price I couldn't verify; see [Appendix B](#appendix-b-sources)).

```
data per turn = 1.5 × $0.014 + 0.3 × $0.017 = $0.0210 + $0.0051 = $0.0261
model per turn (from A3) = $0.0955 input + $0.0312 output = $0.1267
average turn  $0.1267 + $0.0261 = $0.1528  →  × 80 = $12.22 per trip
```

> **Result: the naive agent.** A realistic agent loop on a frontier model, with no cost engineering, costs **$12.22 per planned trip, about 15 cents per question**. That is about 1.8 times the $6.92 back-of-envelope figure.

### Model choice for the naive agent

Here is the same naive-agent turn on each model. It sends 203,125 input tokens, 85% of them cached, and 2,600 output tokens, and spends $0.0261 on search and maps. The effective input price is 15% × the full input price + 85% × the cached price.

| Model | Input | Output | Search + maps | Per turn | Per trip (× 80) |
|---|---|---|---|---|---|
| Frontier (3.1 Pro) | 203,125 × $0.47 / 1M = $0.0955 | 2,600 × $12 / 1M = $0.0312 | $0.0261 | $0.1528 | **$12.22** |
| Mid (3.8 Flash) | 203,125 × $0.3525 / 1M = $0.0716 | 2,600 × $7.50 / 1M = $0.0195 | $0.0261 | $0.1172 | **$9.38** |
| Small (3.1 Flash-Lite) | 203,125 × $0.05875 / 1M = $0.0119 | 2,600 × $1.50 / 1M = $0.0039 | $0.0261 | $0.0419 | **$3.35** |

Two lessons:

- **On the cheapest model, data is the bill.** Search and maps cost 80 × $0.0261 = $2.09 per trip, while the model costs 80 × ($0.0119 + $0.0039) = 80 × $0.0158 = $1.26.
- **Switching everything to the cheapest model is not the answer.** It reaches $3.35 and gives up quality on the hard turns. The engineered build in section 4 reaches **$2.02** while still sending the hardest 10% of turns to the mid and frontier models (the 90/8/2 split). The bigger saving comes from sending fewer tokens and searching less, not from a lower price per token.

---

## 4. Six levers that bring it down

Each step builds on A4 ($12.22). Every lever has a quality risk as well as a saving, so each one lists how to keep quality up.

**At a glance.** The trip cost after each step, and the quality risk that comes with it:

| Step | Lever | Trip cost after | Quality risk → guardrail |
|---|---|---|---|
| B1 | **Summarize the history and trim tool results** to the top 5 | $7.11 | Loses early nuance → keep preferences in structured memory; rank and filter in code before trimming |
| B2 | **Cap thinking and render UI cards** (hotel cards, maps, timetables) instead of writing prose | $6.06 | Weaker answers on hard turns → set thinking budgets per task type |
| B3 | **Route each turn to the cheapest capable model** (70% small, 25% mid, 5% frontier) | $3.34 | Misrouted hard questions → escalate on low confidence; monitor success per tier |
| B4 | **Count the invisible calls** (router, summaries, safety checks, retries: +25%) | $3.65 | Not a saving, an honesty step |
| B5 | **Search live only for time-sensitive facts** | $2.64 | Stale facts → keep live lookups for hours, prices and availability |
| B6 | **Fine-tune a travel model on your own data** so it takes over mid-tier work (90/8/2) | **$2.02** | Needs a solid evaluation set → build it first |

**B1. Compaction plus trimmed tool results**
Instead of replaying the full history, each call sends:

- the system prompt: 4,000 tokens
- a running summary of the conversation: 3,000 tokens
- the last couple of turns: 2,000 tokens
- the top 5 results only: 2,500 tokens

That is 11,500 tokens per call, or 28,750 per turn over 2.5 calls.

*The catch:* the summary changes on every turn, so less of the prompt can be cached. The cached share drops from 85% to **50%**. Explicit caches don't solve this either: keeping one alive between sessions that are days apart means paying the hourly storage fee the whole time.

```
effective input price = 50% × $2.00 + 50% × $0.20 = $1.10 per 1M
input   28,750 × $1.10 / 1M = $0.0316
output   2,600 × $12   / 1M = $0.0312
model                         $0.0628
data (unchanged from A4)      $0.0261
average turn  $0.0628 + $0.0261 = $0.0889  →  × 80 = $7.11 per trip
```

*Quality risk:* nuance from early in the chat gets lost, and trimming can hide a relevant option. *Mitigation:* store preferences in structured memory rather than free-text summaries, and rank and filter results in code before trimming.

**B2. Cap thinking, and render instead of generating**
Set a small thinking budget for simple turns. Show hotel cards, maps and timetables as UI elements built from structured data instead of writing them out as prose. This also answers the main article's "cognitive tax of text". Output drops from 2,600 to **1,500** tokens.

```
output  1,500 × $12 / 1M = $0.0180
model   $0.0316 input + $0.0180 output = $0.0496
average turn  $0.0496 + $0.0261 data = $0.0757  →  × 80 = $6.06 per trip
```

*Quality risk:* weaker answers on genuinely hard turns, where thinking tokens vary the most. *Mitigation:* set the thinking budget per task type, not globally.

**B3. Route each turn to the cheapest capable model**
A travel conversation mixes very different tasks, and only a small share needs deep reasoning:

| Task | Examples | Share of turns (assumed) | Tier |
|---|---|---|---|
| Intent and slot extraction | Dates, budget, group size, "late-night bars" → neighbourhood need | 30% | Small |
| Retrieval and summarization | Review digests, "is X open Monday?" | 35% | Small (30%); the harder 5% goes to mid |
| Conversational glue | Clarifying questions, confirmations | 10% | Small |
| Itinerary construction | Day plans, multi-stop routing (with a route solver) | 20% | Mid |
| Hard reasoning | Group compromises, conflicting constraints, disruption | 5% | Frontier |
| Booking execution | Payment, confirmation | n/a | Plain code, no LLM |

Adding up by tier: small 30 + 30 + 10 = **70%**, mid 5 + 20 = **25%** and frontier **5%**, which makes 100%. The blended price for one average turn is:

```
input   70% × $0.25 + 25% × $1.50 + 5% × $2.00  = $0.65 per 1M (cached: $0.065)
output  70% × $1.50 + 25% × $7.50 + 5% × $12.00 = $3.525 per 1M

effective input = 50% × $0.65 + 50% × $0.065 = $0.3575 per 1M
input   28,750 × $0.3575 / 1M = $0.0103
output   1,500 × $3.525  / 1M = $0.0053
model   $0.0103 + $0.0053     = $0.0156
data (unchanged)                $0.0261
average turn  $0.0156 + $0.0261 = $0.0417  →  × 80 = $3.34 per trip
```

Once routing is in place, **the data calls ($0.026) cost more than the model ($0.016)**. Once models are cheap, external data becomes the hidden bill.

*Quality risk:* hard queries get misrouted to a small model. *Mitigation:* escalate when the small model's confidence is low, and monitor task success per tier.

**B4. Add the calls nobody sees**
The router itself, the compaction summaries, safety checks and retries all cost tokens. So does paying twice when a small model fails and the big one reruns the turn. Assume they add about **+25%** to model cost. This applies to the model part only, which is the $0.0156 from B3 ($0.0103 input + $0.0053 output). Data calls are not affected.

```
model   $0.0156 × 1.25 = $0.0195
data (unchanged)         $0.0261
average turn  $0.0195 + $0.0261 = $0.0456  →  × 80 = $3.65 per trip
```

This is the one step that *raises* cost. It is here because leaving it out would make the engineered build look better than it is.

**B5. Ground only when needed**
Use live search only for time-sensitive facts such as hours, prices and availability. Grounded prompts drop from 1 per turn to **0.4** per turn.

*Where 0.4 comes from:* an assumption, built on the task table in B3. Only two kinds of turn need a live fact:

- **retrieval and summarization**, such as "is X open Monday?": 35% of turns
- **hard reasoning**, where disruptions and conflicting constraints depend on current facts: 5% of turns

That is 35% + 5% = 40% of turns, or 0.4 grounded prompts per turn. The other 60% (intent and slot extraction 30%, conversational glue 10% and itinerary construction 20%) work from what Maya has said and what earlier turns already fetched.

```
data    0.4 × 1.5 × $0.014 + 0.3 × $0.017 = $0.0084 + $0.0051 = $0.0135
model (unchanged from B4)                                      $0.0195
average turn  $0.0195 + $0.0135 = $0.0330  →  × 80 = $2.64 per trip
```

*Where each number comes from:*

| Number | What it is | Where it comes from |
|---|---|---|
| 0.4 | Grounded prompts per turn | New in B5, see above. A4 grounded every turn (1). |
| 1.5 | Search queries per grounded prompt | A4 (assumption) |
| $0.014 | Price of one search query | [Prices used](#prices-used--per-1m-tokens): $14 per 1,000 queries |
| 0.3 | Direct Maps calls per turn | A4 (assumption). Unchanged: B5 cuts search grounding, not Maps calls. |
| $0.017 | Price of one Maps call | A4 (assumed; not verified) |
| $0.0195 | Model cost per turn | B4: B3's $0.0156 × 1.25 |

*Quality risk:* stale facts. *Mitigation:* keep live lookups for anything that changes daily.

**B6. A travel-tuned small model takes over most mid-tier work**
Train a small model on your own data: conversation logs, accepted and rejected suggestions, booking outcomes and curated neighbourhood notes. The routing split becomes **90/8/2**. The tuned model is assumed to be served at Flash-Lite prices on a managed platform.

*Where 90/8/2 comes from:* an assumption about how much of B3's 70/25/5 the tuned model can take over, built on the same task table. It takes all of the harder retrieval (5% of turns, from mid), and 3 in 5 of the itinerary and hard-reasoning turns: 12% of turns from mid (3/5 of 20%) and 3% from frontier (3/5 of 5%). The most complex plans and the hardest compromises stay on the bigger models.

```
small     70% + 5% + 12% + 3% = 90%
mid       25% − 5% − 12%      =  8%
frontier   5% − 3%            =  2%
```

The blended price for one average turn is:

```
input   90% × $0.25 + 8% × $1.50 + 2% × $2.00  = $0.385 per 1M (cached: $0.0385)
output  90% × $1.50 + 8% × $7.50 + 2% × $12.00 = $2.19 per 1M

effective input = 50% × $0.385 + 50% × $0.0385 = $0.2118 per 1M
input   28,750 × $0.2118 / 1M = $0.00609
output   1,500 × $2.19   / 1M = $0.00329
model   ($0.00609 + $0.00329) × 1.25 overhead = $0.0117
data (unchanged from B5)                      $0.0135
average turn  $0.0117 + $0.0135 = $0.0252  →  × 80 = $2.02 per trip
```

*Where each number comes from:*

| Number | What it is | Where it comes from |
|---|---|---|
| 90% / 8% / 2% | Share of turns on the small / mid / frontier tier | New in B6, see above |
| $0.25 / $1.50 / $2.00 | Input price per 1M on each tier | [Prices used](#prices-used--per-1m-tokens). The tuned model costs the same as Flash-Lite. |
| $1.50 / $7.50 / $12.00 | Output price per 1M on each tier | [Prices used](#prices-used--per-1m-tokens) |
| $0.0385 | Cached input price for the mix | The same mix of cached prices ($0.025 / $0.15 / $0.20), which comes to 10% of $0.385 |
| 50% | Share of input billed at the cached price | B1 |
| 28,750 | Input tokens per turn | B1: 11,500 per call × 2.5 calls. Kept, although a tuned model needs a shorter prompt; that saving isn't counted. |
| 1,500 | Output tokens per turn | B2 |
| 1.25 | Overhead calls (+25% of model cost) | B4. B6 works out the model cost afresh for the new mix, so B4's +25% goes on top of it. |
| $0.0135 | Search and Maps per turn | B5 |

**The key insight about custom training:** swapping one cheap small model for another saves very little. The value comes from making the small model *good enough to absorb work that used to need the mid or frontier tier*. A travel-tuned model also brings:

- **Domain accuracy:** it understands "near the Duomo but quiet at night" without a long prompt.
- **Shorter prompts:** behaviour is trained in, not re-explained every turn.
- **Latency:** it is fast enough for on-the-go, in-trip use.
- **Privacy:** it can run self-hosted, or even on the device.

*Caveats:*

- Base models improve and get cheaper every few months, so a fine-tune is an ongoing commitment, not a one-off.
- Check the provider's terms before training on another model's outputs (distillation).
- Build the evaluation set *before* the model.

> **Result: the engineered build.** About **2.5 cents per question ($0.0252 per turn), or $2.02 per planned trip**. That is 83% below the naive agent ($12.22): ($12.22 − $2.02) ÷ $12.22 = $10.20 ÷ $12.22 = 83%.

### Summary waterfall

| Step | What changed | Per trip |
|---|---|---|
| Back-of-envelope | Frontier model, one call per turn | $6.92 |
| A1–A4: the naive agent | + agent loop, tool results in history, caching, per-query grounding | **$12.22** |
| B1–B2 | Compaction, trimmed tools, shorter output | $6.06 |
| B3–B4 | Routing 70/25/5 (+ overhead calls) | $3.65 |
| B5 | Ground only when needed | $2.64 |
| B6: the engineered build | Tuned small model, 90/8/2 | **$2.02** |

---

## 5. From one planner to one booking

**Revenue from the Tuscany booking.** A group trip books more than one room, but some bookings get cancelled, and commission is only paid on completed stays.

```
hotel   2 rooms × 4 nights × €150 = €1,200 ≈ $1,296 (at 1.08 $/€)
        × 4.5% affiliate commission = $58.32
        − 20% cancellations         = $46.66
wine tour  4 people × $80 × 8% commission × 40% of groups who add it = $10.24
revenue per booking = $46.66 + $10.24 = $56.90
```

For comparison, a single room for the same 4 nights at the same commission earns about $29 before cancellations: €600 ≈ $648, × 4.5% = $29.16. A merchant model (selling the room directly) would earn more per booking, but it takes on customer service, refunds and payment risk.

**Who else uses the AI before that booking happens.** Maya's 3 friends open the shared plan and ask their own questions, and for every planner a few visitors chat briefly and leave. Each line is turns × the cost of one turn: $0.0252 on the engineered build (B6) and $0.1528 on the naive agent (A4).

| Who or what | How it's counted | Engineered build (B6) | Naive agent (A4) |
|---|---|---|---|
| Maya's planned trip | 80 turns | $2.02 | $12.22 |
| Her 3 friends | 3 × 15 turns | $1.13 | $6.88 |
| 4 one-off visitors who leave | 4 × 6 turns | $0.60 | $3.67 |
| **AI total** | 149 turns | **$3.75** | **$22.77** |
| Bots and scrapers | +5% of the AI total | $0.19 | $1.14 |
| Infrastructure placeholder (cloud, network, hosting, logging) | +30% of the two lines above | $1.18 | $7.17 |
| Support | 5% contact × $6 | $0.30 | $0.30 |
| **Cost per planner** | | **$5.42** | **$31.38** |

**Not every planner books.** Take 5% of planners as an illustrative rate; I couldn't find a public conversion rate for standalone AI trip planners. Add the cost of booking errors (3% of bookings × $40 to fix = $1.20 per booking):

```
cost per booking = $5.42 ÷ 5% + $1.20 = $109.60   vs revenue $56.90
```

**Break-even conversion, built up one layer at a time.** Each layer is cost per planner ÷ revenue. The last two lines subtract the $1.20 error cost from revenue ($56.90 − $1.20 = $55.70), and the last line also adds the in-trip net margin from section 6 ($55.70 + $25.13 = $80.83).

| What's counted | Engineered build (B6) | Naive agent (A4) |
|---|---|---|
| The planner's trip only | $2.02 ÷ $56.90 = **3.6%** | $12.22 ÷ $56.90 = **21%** |
| + friends and one-off visitors (**headline**) | $3.75 ÷ $56.90 = **6.6%** | $22.77 ÷ $56.90 = **40%** |
| + bots, infrastructure, support, errors | $5.42 ÷ $55.70 = **9.7%** | $31.38 ÷ $55.70 = **56%** |
| + in-trip net margin (section 6, +$25.13) | $5.42 ÷ $80.83 = **6.7%** | $31.38 ÷ $80.83 = **39%** |

The headline is the **6.6%** line. It counts the AI cost for everyone who chats before a booking, and it keeps cloud, network and hosting out, as the main article states. The 9.7% line shows what those extra costs add.

**Another way to see it.** If 1 in 15 planners books, each booking has to pay for the AI chats of 15 planning groups (planner, friends and visitors):

```
engineered build  15 × $3.75  = $56.25 of AI cost per booking   vs $56.90 revenue  →  roughly break-even
naive agent       15 × $22.77 = $341.55 of AI cost per booking  vs $56.90 revenue  →  loses about $285
```

> **The honest message:** even the engineered build needs about **1 in 15 serious planners** to book through the app (6.6%). Once infrastructure, support and errors are counted, that rises to about **1 in 10** (9.7%). The naive agent needs 40–56%. Token burn is solvable. Conversion is still the business.

---

## 6. After the booking: the trip itself

Four travellers, per day. The AI does four kinds of work:

- **checks:** 6 background checks for weather and closures on Flash-Lite, each reading 3,000 tokens and writing 200
- **questions:** 8 group questions, each a full turn of 2.5 calls × 12,000 tokens in (half of it cached) and 1,500 tokens out, on an 80/20 small/mid mix at Priority prices (1.8× standard, for low latency)
- **voice:** 3 short voice exchanges of 1 minute each way on Gemini 3.8 Live ($0.005 per minute in, $0.018 per minute out)
- **lookups:** 6 grounded lookups, at 1.5 search queries each

```
checks     6 × (3,000 × $0.25 + 200 × $1.50) / 1M           = $0.0063
questions  8 × 1.8 × (30,000 × $0.275 + 1,500 × $2.70) / 1M = $0.1771
voice      3 × ($0.005 + $0.018)                            = $0.0690
lookups    6 × 1.5 × $0.014                                 = $0.1260
subtotal                                                    = $0.3784
+30% infrastructure   $0.3784 × 1.3                         = $0.4919 per day
```

Where the question prices come from: the 80/20 mix costs 80% × $0.25 + 20% × $1.50 = $0.50 per 1M input tokens, or $0.05 cached. With half the input cached, that is 50% × $0.50 + 50% × $0.05 = $0.275. Output costs 80% × $1.50 + 20% × $7.50 = $2.70 per 1M.

Revenue per day:

- a group activity booked on 1 day in 4: 25% × $320 × 8% = **$6.40**
- a taxi or train ticket booked every other day: 50% × $15 × 5% = **$0.375**
- total: $6.40 + $0.375 = **$6.775 per day**

Over 4 days, that is 4 × $0.4919 = **$1.97 of cost** against 4 × $6.775 = **$27.10 of revenue**, a net margin of $27.10 − $1.97 = **$25.13**. In-trip help *earns* money, because travellers book things on the spot.

**Design notes for in-trip use:**

- Make it event-driven. A weather alert or a closure triggers a call; nothing polls an LLM constantly.
- Use a fast small model, and escalate only when the plan genuinely needs rebuilding.
- Consider on-device small models for offline use and low latency.

---

## 7. Managing cost without sacrificing performance

Cutting cost is easy: use the cheapest model for everything. The hard part is cutting cost **while holding quality**, and that means defining quality first.

### Define performance before optimizing cost

| Metric | What it measures | Why it matters for travel |
|---|---|---|
| **Cost per successful booking** | Total AI spend ÷ bookings | The north-star metric, not cost per token |
| Task success rate | Did the user get a usable plan or answer? | Measured on a golden set of real travel queries |
| Accuracy on hard facts | Prices, availability, opening hours, transit times | This is where hallucination destroys trust |
| Suggestion acceptance rate | Share of suggestions saved, shortlisted or booked | A proxy for relevance |
| Latency (p95) | Time to first useful response | Critical in-trip: nobody waits on a street corner |
| Conversion by funnel stage | Inspiration → shortlist → booking | Shows where spend is wasted |

The goal is the **cheapest configuration that stays above the quality bar**, measured per task, not per app.

### Keep hard facts out of the model

Prices, availability, opening hours and transit times should always come from tools, never from model memory. The LLM's job is to *compose and explain*, not to *know*. This is the biggest lever for both quality and cost. Once the facts are supplied, a small model can write the answer, and hallucination on the facts that matter most drops sharply. Plain code handles routes and bookings.

### Match spend to intent

Not every session is worth the same compute. Cap the AI budget per session by how likely it is to lead to a booking:

```
max spend per session = P(booking | session state) × revenue per booking × allowed share
```

- A browsing session ("summer in Europe?") gets a small model and precomputed content.
- A group with fixed dates viewing hotels can use the frontier model for the final recommendation.

Estimating P(booking) is itself an ML system: a propensity model trained on funnel data, with a cold-start problem on day one.

### Make it a loop, not a one-off

- **Evaluation harness:** a golden set of real queries (Tuscany with friends, late-night neighbourhoods, ZTL rules), scored for correctness, relevance and hard-fact accuracy.
- **Shadow routing:** before moving traffic to a cheaper model, run it in parallel and compare against the quality bar.
- **Cost dashboards by funnel stage:** find sessions that burn tokens without moving toward a booking.
- **Re-benchmark on every price change:** prices move fast. Gemini 3.8 Flash, for example, doubles from its promotional price on 1 January 2027.

### Security costs tokens too

Scraped blogs and reviews are a prompt-injection surface for an agent that can book. Guardrails add tokens and latency, and booking actions need human confirmation. Part of that cost sits inside B4's +25% overhead.

---

## 8. What this analysis leaves out

- **Salaries,** and real cloud, network and hosting bills. Only a +30% placeholder appears: in the fuller break-even line of section 5, and in the in-trip costs of section 6.
- **Ranges.** Every input is an assumption. The biggest swing factors are calls per turn, cached share, queries per grounded prompt and conversion. Change them in the [assumptions register](#appendix-a-assumptions-register) and redo the sums, or edit the same values at the top of the [calculator](tuscany_tokenomics_calculator.py) and rerun it.
- **Retrieval infrastructure:** embeddings and a vector store.
- **Self-hosting.** Every model is priced as a managed API, including B6's tuned small model at Flash-Lite prices. Running your own model on rented or owned GPUs isn't costed.
- **Video research.** Analysing travel videos, such as YouTube travelogues, isn't costed. Video uses far more tokens than text, so it needs its own costing.
- **Other vendors.** Only Gemini is priced here. The method applies unchanged to any provider's price list.
- **Quality.** The levers assume quality holds. Proving that requires real evaluation data.
- **Lifetime value.** Repeat trips, payment lag and attribution windows aren't modelled.

## 9. What to measure in a real product

1. Turns per session and sessions per trip
2. Model calls per turn
3. Input, output and thinking tokens per call
4. Cache-hit share
5. Search queries per grounded prompt, and Maps calls per turn
6. Overhead share (router, summaries, guardrails, retries)
7. Conversion from planner to booking, by cohort and funnel stage
8. Attach rate for activities, and the cancellation rate
9. Actual affiliate or merchant terms

---

## Appendix A: Assumptions register

| Assumption | Value | Used in |
|---|---|---|
| Sessions × turns per trip | 4 × 20 = 80 | All |
| System prompt and profile | 4,000 tokens | All |
| Tool results per turn | 6,000 tokens (2,500 when trimmed) | Section 1, A2, B1 |
| Chat history per earlier turn | 1,500 tokens | Section 2 |
| Output per turn, including thinking | 2,000 (2,600 with tool calls; 1,500 when capped) | Section 2, A1, B2 |
| Model calls per turn | 2.5 (1.5 tool calls + 1 answer) | A1 onward |
| Output per tool call (request plus thinking) | 400 tokens | A1 |
| Cached share of input | 85% (50% with compaction) | A3, B1 |
| Compacted context per call | summary 3,000 + last couple of turns 2,000 tokens | B1 |
| Search queries per grounded prompt | 1.5 | A4 onward |
| Direct Maps calls per turn | 0.3 at ~$0.017 (price not verified) | A4 onward |
| Grounded prompts per turn | 1 → 0.4 | A4, B5 |
| Routing split (small/mid/frontier) | 70/25/5 → 90/8/2 | B3, B6 |
| Overhead calls | +25% of model cost | B4 onward |
| Hotel | 2 rooms × 4 nights × €150; 4.5% commission; 20% cancelled | Section 5 |
| Exchange rate | 1.08 $/€ | Section 5 |
| Wine tour | 4 × $80; 8% commission; 40% attach rate | Section 5 |
| Friends and visitors | 3 × 15 turns; 4 × 6 turns | Section 5 |
| Bots / infrastructure / support | +5% / +30% / 5% × $6 | Section 5 (infrastructure also in section 6) |
| Conversion; booking errors | 5% (illustrative); 3% × $40 | Section 5 |
| In-trip use, per day for 4 travellers | 6 checks (3,000 tokens in, 200 out); 8 questions (2.5 calls × 12,000 tokens in, half cached; 1,500 out); 3 voice exchanges of 1 minute each way; 6 grounded lookups | Section 6 |
| In-trip models | checks on Flash-Lite; questions on an 80/20 small/mid mix at Priority prices; voice on Gemini 3.8 Live | Section 6 |
| In-trip revenue | activity 25% × $320 × 8%; transport 50% × $15 × 5%; 4 days | Section 6 |

## Appendix B: Sources

Prices were taken on 30 September 2026 and re-checked on 2 October 2026. Prices and terms change, so check them before reusing the numbers.

- Gemini API pricing (model prices, cached input, grounding, Priority tier, context-caching storage, Gemini 3.8 Live audio, promotional pricing): https://ai.google.dev/gemini-api/docs/pricing
- Gemini token counting (characters per token, `countTokens`): https://ai.google.dev/gemini-api/docs/tokens
- Gemini context caching (implicit caching, on by default from Gemini 2.5; explicit caching): https://ai.google.dev/gemini-api/docs/caching

**Not verified:** the price of a direct Maps Platform call. The $0.017 used here is an assumption that I couldn't confirm on Google's Maps Platform pricing pages, so check the current price of the Maps calls you actually make.
