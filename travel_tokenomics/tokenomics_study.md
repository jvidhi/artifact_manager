# The Hidden Tokenomics of an AI Travel Agent

*What one AI-planned booking really costs, and how to cut that cost without cutting quality. This is the tokenomics study that accompanies the Substack article "AI Can Plan Your Trip. Can It Get Paid for It?" It follows one group trip to Tuscany from the first chat to the booking and beyond. The full arithmetic, every assumption and every source are in the [research notes](tuscany_tokenomics_research.md); the § references below point to their sections.*

---

In the main article I argued that the hard part of an AI travel app isn't the demo. It's the economics. This study puts numbers on that claim.

Instead of an abstract "cost per token", I followed one realistic trip, four friends planning Tuscany, through every model call, search query and booking. Model prices are public Gemini API list prices (30 Sep 2026). Everything else is a written-down assumption, so you can disagree with any of them and redo the sums.

## The short version

- **A naive AI planning agent, one with no cost engineering, costs about 15 cents per question on a frontier model, or about $12 for an 80-question trip plan.** It isn't one answer per question: the agent calls tools, rereads the whole conversation several times, and pays for every live search.
- **An engineered build brings that to about 2.5 cents per question, or $2.02 per trip.** Switching everything to the cheapest model only gets to about $3.35, and hurts quality on the hard questions.
- **Even then, about 1 in 15 serious planners must book through the app just to break even** (about 1 in 10 once infrastructure, support and errors are counted). The naive agent needs 40–56% of planners to book.
- **The trip itself makes money.** In-trip help costs about $2 over a 4-day trip and earns about $27 in activity and transport commissions.

Token burn is an engineering problem. Conversion is the business problem.

---

## 1. Meet Maya and the Tuscany trip

Four friends in their late 20s want 4 nights in Florence (2 hotel rooms at about €150 a night), day trips to Chianti and Siena, and a neighbourhood with late-night bars. Maya does most of the planning.

Planning isn't one question. It's a series of sessions, each a long, tool-heavy conversation. A **turn** is one question from Maya plus the agent's whole reply, including every model call behind it. I modelled **4 sessions of 20 turns each, 80 turns in total**:

1. **Inspiration:** "Florence or a countryside villa?"
2. **Shortlist:** "Santo Spirito or Santa Croce for late nights?"
3. **Validation:** "Is the Uffizi open on Monday? Can we drive into the centre?"
4. **Pre-booking:** "Compare these 5 hotels for 2 rooms. Split the budget 4 ways."

### What one question costs

Take one turn from session 3: *"Is the Uffizi open on Monday, and can we drive into the centre with our rental car?"*

To answer it, the model reads about **23,500 tokens**:

- its instructions and Maya's profile: 4,000
- the raw tool results for opening hours and the ZTL traffic-zone rules: 6,000
- the 9 earlier turns of this session: 13,500

It writes back about **2,000 tokens**, counting its hidden "thinking", which reasoning models bill as output.

Where does the 6,000 come from? A raw place-details record is about 9,000 characters of JSON, and the top 3 web pages on ZTL rules are about 12,000 characters of text. [Google's token docs](https://ai.google.dev/gemini-api/docs/tokens) put a token at about 4 characters of English; JSON packs fewer, so I assume about 3. That gives 9,000 ÷ 3 + 12,000 ÷ 4 = 6,000 tokens (research notes §1).

On Gemini 3.1 Pro ($2 per million input tokens, $12 per million output, $0.014 per search query):

```
input      23,500 × $2  / 1M = $0.047
output      2,000 × $12 / 1M = $0.024
search      1 query          = $0.014
                     turn    = $0.085
```

**About 8.5 cents for one question, if the model is called once.** Section 3 shows why a real agent pays about 15 cents. There is a second catch: every turn resends the whole conversation so far. Turn 1 sends 10,000 tokens and turn 20 sends 38,500. Each turn grows in a straight line, so the conversation's total cost grows quadratically. Long, indecisive planning chats are your most expensive users.

---

## 2. The number most people stop at: $6.92

Averaged over a session, a turn sends 24,250 tokens and costs **$0.0865**. Over 80 turns, that is **$6.92 per planned trip**, or about 2 million tokens (research notes §2). Call it the **back-of-envelope** figure.

**That's too low for a real agent, and too high for a well-built one.** The back-of-envelope assumes one model call per question and nothing else. That misses how agents actually work, which pushes the cost up to $12.22, the **naive agent** (section 3). It also leaves out the standard engineering that brings the cost down to $2.02, the **engineered build** (section 4).

---

## 3. Four costs the back-of-envelope misses

1. **One turn is several model calls.** An agent picks a tool, reads the result, sometimes calls another tool, then answers. At 2.5 calls per turn (1.5 tool calls on average, then the answer), each resending the context, the trip costs **$13.32**.
2. **Tool results pile up.** Most agent frameworks keep every tool result in the conversation, so each earlier turn leaves 7,500 tokens behind instead of 1,500. Without caching, the trip would cost **$36.12**.
3. **Caching rescues most of it.** Calls within a turn resend almost the same prompt. Gemini caches repeated prefixes and bills them at 10% of the input price. With 85% of input cached, the trip drops to **$11.26**.
4. **Search is billed per query, and maps cost extra.** One grounded prompt can run several searches (assumed 1.5), and direct Maps calls for travel times and place details are a separate bill. The trip lands at **$12.22**.

> **This is the naive agent: a realistic agent loop on a frontier model, with no cost engineering. It costs about 15 cents per question, or $12.22 per planned trip, about 1.8 times the back-of-envelope.** (Step-by-step sums: research notes §3.)

### Why not just use the cheapest model?

Here is the same naive agent on each model, next to the engineered build from section 4:

| Build | Per question | Per trip |
|---|---|---|
| Naive agent, frontier model (Gemini 3.1 Pro) | about 15¢ | $12.22 |
| Naive agent, mid model (Gemini 3.8 Flash) | about 12¢ | $9.38 |
| Naive agent, cheapest model (Gemini 3.1 Flash-Lite) | about 4¢ | $3.35 |
| **Engineered build** (section 4) | **about 2.5¢** | **$2.02** |

Two things stand out:

- **On the cheapest model, data is the bill.** Search and maps cost $2.09 per trip; the model itself costs $1.26.
- **Engineering beats even the cheapest model.** It still sends the hardest 10% of questions to the bigger models, so it keeps quality where it matters. The real savings come from sending fewer tokens and searching less, not from a lower price per token.

---

## 4. Six ways to bring it down, and what each risks

Cutting cost is easy: use the cheapest model for everything. The hard part is cutting cost **while holding quality**, so every lever below comes with its quality risk and the guardrail that contains it.

| # | Lever | Trip cost after | Quality risk → guardrail |
|---|---|---|---|
| 1 | **Summarize the history and trim tool results** to the top 5 | $7.11 | Loses early nuance → keep preferences in structured memory; rank and filter in code before trimming |
| 2 | **Cap thinking and render UI cards** (hotel cards, maps, timetables) instead of writing prose | $6.06 | Weaker answers on hard turns → set thinking budgets per task type |
| 3 | **Route each turn to the cheapest capable model** (70% small, 25% mid, 5% frontier) | $3.34 | Misrouted hard questions → escalate on low confidence; monitor success per tier |
| 4 | **Count the invisible calls** (router, summaries, safety checks, retries: +25%) | $3.65 | Not a saving, an honesty step |
| 5 | **Search live only for time-sensitive facts** | $2.64 | Stale facts → keep live lookups for hours, prices and availability |
| 6 | **Fine-tune a travel model on your own data** so it takes over mid-tier work (90/8/2) | **$2.02** | Needs a solid evaluation set → build it first |

Two things stand out.

- **Summarizing breaks caching.** A running summary changes every turn, so less of the prompt can be cached. In this model the cached share drops from 85% to 50%. The saving is still large, but smaller than it looks on paper.
- **Once models are cheap, data is the bill.** After routing, search and maps calls cost more per turn than the model itself.

Every lever is costed step by step in research notes §4.

---

## 5. Small models and custom training

### Most turns don't need a frontier model

A travel conversation mixes very different tasks, and only a small share needs deep reasoning. That's where the 70/25/5 routing split comes from:

| Task | Examples | Share of turns (assumed) | Right-sized approach |
|---|---|---|---|
| Intent and slot extraction | Dates, budget, group size, "late-night bars" → neighbourhood need | 30% | Small or fine-tuned model |
| Retrieval and summarization | Review digests, "is X open Monday?" | 35% | Small model plus tools (30%); the harder 5% goes to mid; precompute offline |
| Conversational glue | Clarifying questions, confirmations | 10% | Small model |
| Itinerary construction | Day plans, multi-stop routing | 20% | Mid model **plus a deterministic route solver** |
| Hard reasoning | Group compromises, conflicting constraints, disruption | 5% | Frontier model |
| Booking execution | Payment, confirmation | n/a | **Plain code, no LLM** |

Adding up by tier: small 30 + 30 + 10 = **70%**, mid 5 + 20 = **25%** and frontier **5%**.

### What custom training actually buys you

Fine-tuning or distillation means training a small model on your own data: conversation logs, accepted and rejected suggestions, booking outcomes, and curated neighbourhood notes.

**The key insight:** swapping one cheap small model for another saves very little. The value comes when your travel-tuned model is good enough to **absorb work that used to need the mid or frontier tier**. In this example, that shifts routing from 70/25/5 to 90/8/2 and takes the trip from $2.64 to $2.02.

A travel-tuned model also brings:

- **Domain accuracy:** it understands "near the Duomo but quiet at night" without a long prompt.
- **Shorter prompts:** behaviour is trained in, not re-explained every turn.
- **Latency:** it is fast enough for on-the-go, in-trip use.
- **Privacy:** it can run self-hosted or on the device.

**Caveats:**

- Base models improve and get cheaper every few months, so a fine-tune is an ongoing commitment, not a one-off.
- Check the provider's terms before training on another model's outputs.
- Build the evaluation set *before* the model.

---

## 6. The number that matters: cost per booking

**Revenue first.** The group books 2 rooms for 4 nights: €1,200, or about $1,296.

- At a 4.5% affiliate commission, that's $58.32.
- After 20% cancellations, it's $46.66.
- A Chianti wine tour that 4 in 10 groups book adds $10.24 in expected commission.

So one booking is worth $46.66 + $10.24 = **$56.90**. A single room would earn about $29 before cancellations, so group trips matter.

**Then count everyone who chats.** Maya isn't the only user. Her 3 friends ask their own questions, and for every planner, a few visitors chat briefly and leave. Here is what that costs on each build:

| | Engineered build | Naive agent |
|---|---|---|
| Maya's trip (80 turns) | $2.02 | $12.22 |
| 3 friends × 15 turns | $1.13 | $6.88 |
| 4 one-off visitors × 6 turns | $0.60 | $3.67 |
| **AI cost per planner** | **$3.75** | **$22.77** |

**Break-even conversion = cost per planner ÷ revenue per booking:**

| What's counted | Engineered build | Naive agent |
|---|---|---|
| Everyone who chats (headline) | **6.6%** (about 1 in 15) | 40% |
| + bots, infrastructure (+30%), support, booking errors | **9.7%** (about 1 in 10) | 56% |
| + in-trip net margin (section 7) | **6.7%** | 39% |

**In plain terms:** if 1 in 15 planners books, each booking has to pay for the AI chats of 15 planning groups. On the engineered build that's 15 × $3.75 = **$56.25**, about what the booking earns. On the naive agent it's 15 × $22.77 = **$341.55**, for the same $56.90.

I couldn't find a public conversion rate for standalone AI trip planners. At an illustrative 5%, the fully loaded engineered build spends **$109.60 per booking to earn $56.90** (research notes §5). Engineering gets you close to break-even. Conversion decides the rest.

---

## 7. The trip itself makes money

Once the group is in Tuscany, the economics flip. For four travellers, a day of help costs about **$0.49**:

- background weather and closure checks
- 8 group questions on fast, low-latency models
- a few voice exchanges
- live lookups
- +30% infrastructure

It earns about **$6.78** a day from a group activity booked on 1 day in 4, plus the occasional taxi or train ticket. Over 4 days that's 4 × $0.4919 = **$1.97 spent** and 4 × $6.775 = **$27.10 earned** (research notes §6).

**Design for it:**

- Be event-driven: a weather alert or a closure triggers the AI, rather than an LLM polling constantly.
- Use a fast small model, and escalate only when the plan needs rebuilding.
- Consider on-device models for offline use.

---

## 8. Managing cost without sacrificing performance

### Step 1: Define performance before optimizing cost

| Metric | What it measures | Why it matters for travel |
|---|---|---|
| **Cost per successful booking** | Total AI spend ÷ bookings | The north-star metric, not cost per token |
| Task success rate | Did the user get a usable plan or answer? | Measured on a golden set of real travel queries |
| Accuracy on hard facts | Prices, availability, opening hours, transit times | This is where hallucination destroys trust |
| Suggestion acceptance rate | Share of suggestions saved, shortlisted or booked | A proxy for relevance |
| Latency (p95) | Time to first useful response | Critical in-trip: nobody waits on a street corner |
| Conversion by funnel stage | Inspiration → shortlist → booking | Shows where spend is wasted |

The goal is the **cheapest configuration that stays above the quality bar**, measured per task, not per app.

### Step 2: Keep hard facts out of the model

Prices, availability, opening hours and transit times should **always come from tools, never from model memory**. The LLM's job is to *compose and explain*, not to *know*, and code handles routes and bookings. This is the biggest single lever for both quality and cost. Once the facts are supplied, a small model can write the answer, and hallucination on the facts that matter most drops sharply.

### Step 3: Match spend to intent

Not every session is worth the same compute. Cap the AI budget per session by how likely it is to lead to a booking:

```
max spend per session = P(booking | session state) × revenue per booking × allowed share
```

| User state | Likelihood of booking | Model policy |
|---|---|---|
| Browsing ("summer in Europe?") | Low | Small model plus precomputed content |
| Destination chosen, comparing areas | Medium | Small model; mid tier for itinerary drafts |
| Dates fixed, group agreed, viewing hotels | High | Frontier allowed for the final recommendation |
| In-trip disruption (venue closed, rain) | High retention value | Fast small model; escalate only for re-planning |

Estimating P(booking) is itself an ML system: a propensity model trained on funnel data, with a cold-start problem on day one.

### Step 4: Make it a loop, not a one-off

- **Evaluation harness:** a golden set of real queries (Tuscany with friends, late-night neighbourhoods, ZTL rules), scored for correctness, relevance and hard-fact accuracy.
- **Shadow routing:** before moving traffic to a cheaper model, run it in parallel and compare against the quality bar.
- **Cost dashboards by funnel stage:** find sessions that burn tokens without moving toward a booking.
- **Re-benchmark on every price change:** prices move fast. Gemini 3.8 Flash, for example, doubles from its promotional $0.75 / $3.75 to $1.50 / $7.50 on 1 January 2027. Your routing table should follow the price list.

### Step 5: Budget for security

Scraped blogs and reviews are a prompt-injection surface for an agent that can book. Guardrails cost tokens and latency, and booking actions need human confirmation.

---

## 9. What this means for the main article

Token burn is real, but it is largely an **architecture choice**. The naive agent, which puts everything through the best model, needs 40–56% of serious planners to book just to break even. The engineered build (routing, caching, summarization, deterministic tools and a travel-tuned small model) needs about 1 in 15.

Once the engineering is done, the remaining problem is the one the article already names: **conversion and ownership of the transaction.** Cheap tokens don't help if the booking happens somewhere else. In-trip help is where the economics turn positive.

---

## 10. What these numbers don't include, and what to measure

**Not included:**

- **Costs:** salaries. Cloud, networking, hosting, databases and monitoring appear only as one rough placeholder (+30%), in the fuller break-even figure and in the in-trip costs.
- **Infrastructure:** retrieval infrastructure (embeddings, a vector store).
- **Self-hosting:** every model, including the travel-tuned small model, is priced as a managed API. Running your own model on GPUs isn't costed.
- **Scope and evidence:** video research (such as mining YouTube travelogues), other vendors (only Gemini is priced, though the method applies to any price list), proof that quality holds (which needs real evaluation data), and lifetime value from repeat trips.

**Replace my assumptions with real data.** To publish numbers for a real product, measure:

1. Turns per session and sessions per trip
2. Model calls per turn
3. Input, output and thinking tokens per call
4. Cache-hit share
5. Search queries per grounded prompt, and Maps calls per turn
6. Overhead share (router, summaries, guardrails, retries)
7. Conversion from planner to booking, by cohort and funnel stage
8. Attach rate for activities, and the cancellation rate
9. Actual affiliate or merchant terms

Then swap them into the [assumptions register](tuscany_tokenomics_research.md#appendix-a-assumptions-register) and redo the sums, or edit the same values in the [calculator](tuscany_tokenomics_calculator.py) and rerun it.

---

**Bottom line:** a naive AI travel agent loses money unless more than 2 in 5 planners book. An engineered one gets close to break-even, and starts earning once the traveller is on the road. What separates them isn't a cheaper model. It's architecture first, then conversion.

*Prices: Gemini API list prices as of 30 Sep 2026, re-checked 2 Oct 2026 ([pricing](https://ai.google.dev/gemini-api/docs/pricing)). Gemini 3.1 Pro is a Preview model. All other figures are stated assumptions. Full calculations, the assumptions register and sources: [research notes](tuscany_tokenomics_research.md). To rerun every sum: [tuscany_tokenomics_calculator.py](tuscany_tokenomics_calculator.py).*
