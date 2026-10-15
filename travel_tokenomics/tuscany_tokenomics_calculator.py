#!/usr/bin/env python3
"""Tuscany tokenomics calculator.

Reproduces every number in tuscany_tokenomics_research.md, section by section.
It uses the same assumptions (Appendix A of the research notes) and the same
rounding rule: each line is worked out from the rounded numbers shown above it,
so every printed line matches the notes exactly.

    python3 tuscany_tokenomics_calculator.py                        # print every step
    python3 tuscany_tokenomics_calculator.py --set CONVERSION=0.08  # change an assumption for one run
    python3 tuscany_tokenomics_calculator.py --list                 # the assumptions --set can change
    python3 -m unittest                                             # check the figures and the docs

Standard library only. --set changes a number for one run and leaves this file
alone. To try other prices or mixes (PRO, ROUTING and so on), edit the
constants below and rerun. The tests pin the published figures, so they will
then fail; that is expected.
"""

import argparse
import sys
from contextlib import contextmanager
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

D = Decimal
MILLION = D(1_000_000)

# --- Prices: $ per 1M tokens unless stated ----------------------------------
# Gemini API list prices, https://ai.google.dev/gemini-api/docs/pricing
# (accessed 30 Sep 2026, re-checked 2 Oct 2026).
PRO = {"in": D("2.00"), "out": D("12.00"), "cached": D("0.20")}     # Gemini 3.1 Pro Preview, prompts up to 200k tokens
MID = {"in": D("1.50"), "out": D("7.50"), "cached": D("0.15")}     # Gemini 3.8 Flash, list price from 1 Jan 2027
SMALL = {"in": D("0.25"), "out": D("1.50"), "cached": D("0.025")}  # Gemini 3.1 Flash-Lite
PRIORITY_MULTIPLIER = D("1.8")          # Priority tier: 1.8x the standard price
SEARCH_QUERY = D("0.014")               # grounding: $14 per 1,000 search queries (5,000 free a month ignored)
LIVE_AUDIO_IN_PER_MINUTE = D("0.005")   # Gemini Live, audio in
LIVE_AUDIO_OUT_PER_MINUTE = D("0.018")  # Gemini Live, audio out

# --- Assumptions (Appendix A of the research notes) -------------------------
SESSIONS, TURNS_PER_SESSION = 4, 20
TURNS = SESSIONS * TURNS_PER_SESSION    # 80 turns per planned trip
SYSTEM_TOKENS = 4_000                   # system prompt and profile
TOOL_TOKENS = 6_000                     # raw tool results per turn
CHAT_TOKENS = 1_500                     # chat text each earlier turn leaves in the history
OUTPUT_TOKENS = 2_000                   # the answer, including thinking
CALLS_PER_TURN = D("2.5")               # 1.5 tool calls + 1 answer
OUTPUT_PER_TOOL_CALL = 400              # tool request plus some thinking
CACHED_SHARE = D("0.85")
QUERIES_PER_GROUNDED_PROMPT = D("1.5")
MAPS_CALLS_PER_TURN = D("0.3")
MAPS_CALL = D("0.017")                  # assumed; not checked against Maps Platform pricing

# Section 4: the engineering levers
SUMMARY_TOKENS, RECENT_TOKENS, TRIMMED_TOOL_TOKENS = 3_000, 2_000, 2_500
CACHED_SHARE_COMPACTED = D("0.50")
CAPPED_OUTPUT_TOKENS = 1_500
TASK_SHARES = {  # % of turns per task, split by tier (B3)
    "intent and slot extraction": {"small": 30},
    "retrieval and summarization": {"small": 30, "mid": 5},
    "conversational glue": {"small": 10},
    "itinerary construction": {"mid": 20},
    "hard reasoning": {"frontier": 5},
}
ROUTING = {"small": D("0.70"), "mid": D("0.25"), "frontier": D("0.05")}
ROUTING_TUNED = {"small": D("0.90"), "mid": D("0.08"), "frontier": D("0.02")}
OVERHEAD = D("0.25")
GROUNDED_PROMPTS_SELECTIVE = D("0.4")   # B5

# Section 5: from one planner to one booking
ROOMS, NIGHTS, EUR_PER_ROOM_NIGHT = 2, 4, 150
USD_PER_EUR = D("1.08")
HOTEL_COMMISSION, CANCELLATIONS = D("0.045"), D("0.20")
TOUR_PEOPLE, TOUR_PRICE, TOUR_COMMISSION, TOUR_ATTACH = 4, D("80"), D("0.08"), D("0.40")
FRIENDS, FRIEND_TURNS = 3, 15
VISITORS, VISITOR_TURNS = 4, 6
BOTS, INFRASTRUCTURE = D("0.05"), D("0.30")
SUPPORT_CONTACT, SUPPORT_COST = D("0.05"), D("6")
CONVERSION = D("0.05")                  # illustrative
ERROR_RATE, ERROR_COST = D("0.03"), D("40")
PLANNING_GROUPS_PER_BOOKING = 15        # "if 1 in 15 planners books"

# Section 6: in-trip help, per day for 4 travellers
CHECKS, CHECK_IN, CHECK_OUT = 6, 3_000, 200
QUESTIONS, QUESTION_IN_PER_CALL, QUESTION_OUT = 8, 12_000, 1_500
QUESTION_CACHED_SHARE = D("0.50")
IN_TRIP_MIX = {"small": D("0.80"), "mid": D("0.20")}
VOICE_EXCHANGES, VOICE_MINUTES_EACH_WAY = 3, 1
LOOKUPS = 6
ACTIVITY_DAY_SHARE, ACTIVITY_PRICE, ACTIVITY_COMMISSION = D("0.25"), D("320"), D("0.08")
TRANSPORT_DAY_SHARE, TRANSPORT_PRICE, TRANSPORT_COMMISSION = D("0.50"), D("15"), D("0.05")
TRIP_DAYS = 4


# --- Helpers ----------------------------------------------------------------
def rnd(x, places):
    """Round half-up to a fixed number of decimal places, as the notes do."""
    return D(x).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)


def usd(x, places=2):
    return f"${x:,.{places}f}"


def price(x):
    """A per-1M price with at least 2 decimals: $2.00, $0.47, $0.05875."""
    digits = f"{x.normalize():f}"
    whole, _, frac = digits.partition(".")
    return f"${whole}.{frac.ljust(2, '0')}"


def rate(x):
    """A price as the sums in the notes write it, without trailing zeros: $2, $12, $0.014."""
    return f"${x.normalize():f}"


def share(x):
    """A share as a percentage without trailing zeros: 0.85 -> '85%', 0.045 -> '4.5%'."""
    return f"{(D(x) * 100).normalize():f}%"


def split(mix):
    """A routing mix as the notes write it: '90/8/2'."""
    return "/".join(f"{(v * 100).normalize():f}" for v in mix.values())


def tok(n):
    return f"{D(n):,.0f}"


def pct(ratio, places):
    return rnd(ratio * 100, places)


def tier_prices():
    """Prices per tier, looked up when called, so changed prices are always picked up."""
    return {"small": SMALL, "mid": MID, "frontier": PRO}


def blend(mix):
    """Price of an average turn spread across tiers."""
    tiers = tier_prices()
    return {k: sum(weight * tiers[tier][k] for tier, weight in mix.items())
            for k in ("in", "out", "cached")}


def effective_input(p, cached_share):
    return (1 - cached_share) * p["in"] + cached_share * p["cached"]


def cached_working(p, cached_share):
    """The effective-input sum as the notes write it: '15% × $2.00 + 85% × $0.20'."""
    return f"{share(1 - cached_share)} × {price(p['in'])} + {share(cached_share)} × {price(p['cached'])}"


def title(out, text):
    out += ["", text, "-" * len(text)]


def line(out, label, working, value):
    out.append(f"  {label:<10} {working:<52} = {value}")


def per_trip(turn):
    return rnd(turn * TURNS, 2)


def result(out, parts, turn, trip):
    out.append(f"  average turn  {' + '.join(usd(p, 4) for p in parts)} = {usd(turn, 4)}"
               f"  →  × {TURNS} = {usd(trip)} per trip")


# --- Changing assumptions ---------------------------------------------------
DERIVED = ("TURNS", "MILLION")          # worked out from other values, so never set directly
SHARES = ("CACHED_SHARE", "CACHED_SHARE_COMPACTED", "QUESTION_CACHED_SHARE", "HOTEL_COMMISSION",
          "CANCELLATIONS", "TOUR_COMMISSION", "TOUR_ATTACH", "SUPPORT_CONTACT", "CONVERSION",
          "ERROR_RATE", "ACTIVITY_DAY_SHARE", "ACTIVITY_COMMISSION", "TRANSPORT_DAY_SHARE",
          "TRANSPORT_COMMISSION")
MIXES = ("ROUTING", "ROUTING_TUNED", "IN_TRIP_MIX")


def settable():
    """The assumptions --set can change: every whole-number or decimal constant above."""
    return {name: value for name, value in globals().items()
            if name.isupper() and name not in DERIVED
            and isinstance(value, (int, Decimal)) and not isinstance(value, bool)}


@contextmanager
def assumptions(**changes):
    """Change some assumptions for a while, then put them back.

        with assumptions(SESSIONS=2, CONVERSION=D("0.08")):
            figures, report = calculate()

    Prices and mixes (PRO, ROUTING, ...) can be changed here too, as dicts.
    TURNS is worked out again from SESSIONS × TURNS_PER_SESSION.
    """
    g = globals()
    unknown = [name for name in changes
               if name in DERIVED or not name.isupper()
               or not isinstance(g.get(name), (int, Decimal, dict))]
    if unknown:
        raise ValueError(f"not an assumption you can change: {', '.join(unknown)}")
    saved = {name: g[name] for name in changes}
    try:
        g.update(changes)
        g["TURNS"] = g["SESSIONS"] * g["TURNS_PER_SESSION"]
        yield
    finally:
        g.update(saved)
        g["TURNS"] = g["SESSIONS"] * g["TURNS_PER_SESSION"]


def check():
    """Stop with a clear message if an assumption can't be right, rather than print nonsense."""
    g = globals()
    problems = [f"{name} can't be negative" for name, value in settable().items() if value < 0]
    problems += [f"{name} must be at least 1" for name in ("SESSIONS", "TURNS_PER_SESSION", "CALLS_PER_TURN")
                 if g[name] < 1]
    problems += [f"{name} is a share, so it must be between 0 and 1" for name in SHARES if not 0 <= g[name] <= 1]
    problems += ["CONVERSION must be above 0"] if CONVERSION == 0 else []
    problems += [f"{name} must add up to 1, not {sum(g[name].values())}" for name in MIXES
                 if sum(g[name].values()) != 1]
    problems += [f"{name} prices can't be negative" for name in ("PRO", "MID", "SMALL")
                 if any(v < 0 for v in g[name].values())]
    if problems:
        raise ValueError("; ".join(problems))


# --- Section 1 ----------------------------------------------------------------
def section_1(f, out):
    example = min(10, TURNS_PER_SESSION)  # the turn the notes dissect: session 3, turn 10
    title(out, f"1. One turn, dissected (session 3, turn {example})")
    tokens_in = SYSTEM_TOKENS + TOOL_TOKENS + (example - 1) * CHAT_TOKENS
    i = rnd(tokens_in * PRO["in"] / MILLION, 3)
    o = rnd(OUTPUT_TOKENS * PRO["out"] / MILLION, 3)
    g = rnd(SEARCH_QUERY, 3)
    turn = i + o + g
    line(out, "input", f"{tok(tokens_in)} × {rate(PRO['in'])} / 1M", usd(i, 3))
    line(out, "output", f"{tok(OUTPUT_TOKENS)} × {rate(PRO['out'])} / 1M", usd(o, 3))
    line(out, "grounding", "1 query", usd(g, 3))
    line(out, "turn", "", usd(turn, 3))
    first = SYSTEM_TOKENS + TOOL_TOKENS
    last = first + (TURNS_PER_SESSION - 1) * CHAT_TOKENS
    out.append(f"  The history grows: turn 1 sends {tok(first)} input tokens,"
               f" turn {TURNS_PER_SESSION} sends {tok(last)}.")
    f.update(one_turn_input=D(tokens_in), one_turn=turn)


# --- Section 2 ----------------------------------------------------------------
def section_2(f, out):
    title(out, "2. The back-of-envelope number")
    earlier = D(TURNS_PER_SESSION - 1) / 2
    history = earlier * CHAT_TOKENS
    tokens_in = SYSTEM_TOKENS + TOOL_TOKENS + history
    i = rnd(tokens_in * PRO["in"] / MILLION, 4)
    o = rnd(OUTPUT_TOKENS * PRO["out"] / MILLION, 4)
    g = rnd(SEARCH_QUERY, 4)
    turn = i + o + g
    trip = per_trip(turn)
    out.append(f"  average history = {earlier} × {tok(CHAT_TOKENS)} = {tok(history)} tokens")
    out.append(f"  average turn input = {tok(SYSTEM_TOKENS)} system + {tok(TOOL_TOKENS)} tools"
               f" + {tok(history)} history = {tok(tokens_in)} tokens")
    line(out, "input", f"{tok(tokens_in)} × {rate(PRO['in'])} / 1M", usd(i, 4))
    line(out, "output", f"{tok(OUTPUT_TOKENS)} × {rate(PRO['out'])} / 1M", usd(o, 4))
    line(out, "grounding", f"1 × {rate(SEARCH_QUERY)}", usd(g, 4))
    line(out, "turn", "", usd(turn, 4))
    line(out, f"× {TURNS}", "turns", f"{usd(trip)} per planned trip")
    out.append(f"  per trip: {TURNS * tokens_in / MILLION:.2f}M input tokens, "
               f"{D(TURNS * OUTPUT_TOKENS) / MILLION:.2f}M output tokens")
    f.update(s0_input=tokens_in, s0_turn=turn, s0_trip=trip)


# --- Section 3 ----------------------------------------------------------------
def section_3(f, out):
    title(out, "3. Four costs the back-of-envelope misses")
    g = rnd(SEARCH_QUERY, 4)
    tool_calls = CALLS_PER_TURN - 1

    out.append("A1. One turn is several model calls")
    a1_in = f["s0_input"] * CALLS_PER_TURN
    a1_out = OUTPUT_TOKENS + tool_calls * OUTPUT_PER_TOOL_CALL
    i = rnd(a1_in * PRO["in"] / MILLION, 4)
    o = rnd(a1_out * PRO["out"] / MILLION, 4)
    turn = i + o + g
    line(out, "input", f"{tok(f['s0_input'])} × {CALLS_PER_TURN} = {tok(a1_in)} tokens"
                       f" × {rate(PRO['in'])} / 1M", usd(i, 4))
    line(out, "output", f"{tok(OUTPUT_TOKENS)} + {tool_calls} × {OUTPUT_PER_TOOL_CALL} = {tok(a1_out)} tokens"
                        f" × {rate(PRO['out'])} / 1M", usd(o, 4))
    line(out, "grounding", f"1 × {rate(SEARCH_QUERY)}", usd(g, 4))
    result(out, (i, o, g), turn, per_trip(turn))
    f.update(a1_turn=turn, a1_trip=per_trip(turn), output_with_tools=a1_out)

    out.append("A2. Tool results stay in the history")
    earlier = D(TURNS_PER_SESSION - 1) / 2
    history = earlier * (CHAT_TOKENS + TOOL_TOKENS)
    per_call = SYSTEM_TOKENS + TOOL_TOKENS + history
    a2_in = per_call * CALLS_PER_TURN
    i = rnd(a2_in * PRO["in"] / MILLION, 4)
    turn = i + o + g
    out.append(f"  average history = {earlier} × {tok(CHAT_TOKENS + TOOL_TOKENS)} = {tok(history)} tokens")
    line(out, "input", f"({tok(SYSTEM_TOKENS)} + {tok(TOOL_TOKENS)} + {tok(history)}) × {CALLS_PER_TURN}"
                       f" = {tok(a2_in)} × {rate(PRO['in'])} / 1M", usd(i, 4))
    result(out, (i, o, g), turn, per_trip(turn))
    f.update(a2_input=a2_in, a2_turn=turn, a2_trip=per_trip(turn))

    out.append("A3. Most of that input is cached")
    eff = effective_input(PRO, CACHED_SHARE)
    i = rnd(a2_in * eff / MILLION, 4)
    turn = i + o + g
    out.append(f"  effective input price = {cached_working(PRO, CACHED_SHARE)} = {price(eff)} per 1M")
    line(out, "input", f"{tok(a2_in)} × {price(eff)} / 1M", usd(i, 4))
    result(out, (i, o, g), turn, per_trip(turn))
    f.update(a3_turn=turn, a3_trip=per_trip(turn))

    out.append("A4. Grounding is billed per search query, and Maps calls cost extra")
    search = rnd(QUERIES_PER_GROUNDED_PROMPT * SEARCH_QUERY, 4)
    maps = rnd(MAPS_CALLS_PER_TURN * MAPS_CALL, 4)
    data = search + maps
    model = i + o
    turn = model + data
    line(out, "data", f"{QUERIES_PER_GROUNDED_PROMPT} × {rate(SEARCH_QUERY)} + {MAPS_CALLS_PER_TURN} × {rate(MAPS_CALL)}"
                      f" = {usd(search, 4)} + {usd(maps, 4)}", usd(data, 4))
    line(out, "model", f"{usd(i, 4)} input + {usd(o, 4)} output", usd(model, 4))
    result(out, (model, data), turn, per_trip(turn))
    f.update(a4_data=data, a4_model=model, a4_turn=turn, a4_trip=per_trip(turn))

    out.append("Model choice for the naive agent (same turn on each model)")
    for key, label, p in (("a4", "Frontier (3.1 Pro)", PRO), ("mid", "Mid (3.8 Flash)", MID),
                          ("small", "Small (3.1 Flash-Lite)", SMALL)):
        eff = effective_input(p, CACHED_SHARE)
        i = rnd(a2_in * eff / MILLION, 4)
        o = rnd(a1_out * p["out"] / MILLION, 4)
        turn = i + o + data
        out.append(f"  {label:<23} input {tok(a2_in)} × {price(eff)} / 1M = {usd(i, 4)}"
                   f" | output {tok(a1_out)} × {price(p['out'])} / 1M = {usd(o, 4)}"
                   f" | search + maps {usd(data, 4)} | turn {usd(turn, 4)} | trip {usd(per_trip(turn))}")
        if key != "a4":
            f.update({f"{key}_turn": turn, f"{key}_trip": per_trip(turn)})
        if key == "small":
            f.update(small_model_trip=per_trip(i + o), small_data_trip=per_trip(data))
            out.append(f"  On the small model: search and maps {TURNS} × {usd(data, 4)} = {usd(per_trip(data))}"
                       f" per trip; the model {TURNS} × {usd(i + o, 4)} = {usd(per_trip(i + o))}")


# --- Section 4 ----------------------------------------------------------------
def section_4(f, out):
    title(out, "4. Six levers that bring it down")
    data = f["a4_data"]

    out.append("B1. Compaction plus trimmed tool results")
    per_call = SYSTEM_TOKENS + SUMMARY_TOKENS + RECENT_TOKENS + TRIMMED_TOOL_TOKENS
    b_in = per_call * CALLS_PER_TURN
    eff = effective_input(PRO, CACHED_SHARE_COMPACTED)
    i = rnd(b_in * eff / MILLION, 4)
    o = rnd(f["output_with_tools"] * PRO["out"] / MILLION, 4)
    model = i + o
    turn = model + data
    out.append(f"  per call {tok(SYSTEM_TOKENS)} + {tok(SUMMARY_TOKENS)} + {tok(RECENT_TOKENS)}"
               f" + {tok(TRIMMED_TOOL_TOKENS)} = {tok(per_call)}; × {CALLS_PER_TURN} = {tok(b_in)} per turn")
    out.append(f"  effective input price = {cached_working(PRO, CACHED_SHARE_COMPACTED)} = {price(eff)} per 1M")
    line(out, "input", f"{tok(b_in)} × {price(eff)} / 1M", usd(i, 4))
    line(out, "output", f"{tok(f['output_with_tools'])} × {rate(PRO['out'])} / 1M", usd(o, 4))
    line(out, "model", "", usd(model, 4))
    result(out, (model, data), turn, per_trip(turn))
    f.update(compacted_input=b_in, b1_turn=turn, b1_trip=per_trip(turn))
    b1_input = i

    out.append("B2. Cap thinking, and render instead of generating")
    o = rnd(CAPPED_OUTPUT_TOKENS * PRO["out"] / MILLION, 4)
    model = b1_input + o
    turn = model + data
    line(out, "output", f"{tok(CAPPED_OUTPUT_TOKENS)} × {rate(PRO['out'])} / 1M", usd(o, 4))
    line(out, "model", f"{usd(b1_input, 4)} input + {usd(o, 4)} output", usd(model, 4))
    result(out, (model, data), turn, per_trip(turn))
    f.update(b2_turn=turn, b2_trip=per_trip(turn))

    out.append("B3. Route each turn to the cheapest capable model")
    tiers = {"small": 0, "mid": 0, "frontier": 0}
    for split_ in TASK_SHARES.values():
        for tier, task_share in split_.items():
            tiers[tier] += task_share
    out.append(f"  task shares by tier: small {tiers['small']}%, mid {tiers['mid']}%,"
               f" frontier {tiers['frontier']}% (total {sum(tiers.values())}%)")
    p = blend(ROUTING)
    eff = effective_input(p, CACHED_SHARE_COMPACTED)
    i = rnd(b_in * eff / MILLION, 4)
    o = rnd(CAPPED_OUTPUT_TOKENS * p["out"] / MILLION, 4)
    routed_model = i + o
    turn = routed_model + data
    out.append(f"  blended input {price(p['in'])} per 1M (cached {price(p['cached'])}),"
               f" output {price(p['out'])} per 1M")
    out.append(f"  effective input = {cached_working(p, CACHED_SHARE_COMPACTED)} = {price(eff)} per 1M")
    line(out, "input", f"{tok(b_in)} × {price(eff)} / 1M", usd(i, 4))
    line(out, "output", f"{tok(CAPPED_OUTPUT_TOKENS)} × {price(p['out'])} / 1M", usd(o, 4))
    line(out, "model", f"{usd(i, 4)} + {usd(o, 4)}", usd(routed_model, 4))
    result(out, (routed_model, data), turn, per_trip(turn))
    f.update(routing_tiers=tiers, b3_turn=turn, b3_trip=per_trip(turn))

    out.append(f"B4. Add the calls nobody sees (+{share(OVERHEAD)} of model cost)")
    model = rnd(routed_model * (1 + OVERHEAD), 4)
    turn = model + data
    line(out, "model", f"{usd(routed_model, 4)} × {1 + OVERHEAD}", usd(model, 4))
    result(out, (model, data), turn, per_trip(turn))
    f.update(b4_turn=turn, b4_trip=per_trip(turn))

    out.append(f"B5. Ground only when needed ({GROUNDED_PROMPTS_SELECTIVE} grounded prompts per turn)")
    search = rnd(GROUNDED_PROMPTS_SELECTIVE * QUERIES_PER_GROUNDED_PROMPT * SEARCH_QUERY, 4)
    maps = rnd(MAPS_CALLS_PER_TURN * MAPS_CALL, 4)
    data = search + maps
    turn = model + data
    line(out, "data", f"{GROUNDED_PROMPTS_SELECTIVE} × {QUERIES_PER_GROUNDED_PROMPT} × {rate(SEARCH_QUERY)}"
                      f" + {MAPS_CALLS_PER_TURN} × {rate(MAPS_CALL)} = {usd(search, 4)} + {usd(maps, 4)}",
         usd(data, 4))
    result(out, (model, data), turn, per_trip(turn))
    f.update(b5_turn=turn, b5_trip=per_trip(turn))

    out.append(f"B6. A travel-tuned small model takes over most mid-tier work ({split(ROUTING_TUNED)})")
    p = blend(ROUTING_TUNED)
    eff = rnd(effective_input(p, CACHED_SHARE_COMPACTED), 4)
    i = rnd(b_in * eff / MILLION, 5)
    o = rnd(CAPPED_OUTPUT_TOKENS * p["out"] / MILLION, 5)
    model = rnd((i + o) * (1 + OVERHEAD), 4)
    turn = model + data
    out.append(f"  blended input {price(p['in'])} per 1M (cached {price(p['cached'])}),"
               f" output {price(p['out'])} per 1M")
    out.append(f"  effective input = {cached_working(p, CACHED_SHARE_COMPACTED)} = {price(eff)} per 1M")
    line(out, "input", f"{tok(b_in)} × {price(eff)} / 1M", usd(i, 5))
    line(out, "output", f"{tok(CAPPED_OUTPUT_TOKENS)} × {price(p['out'])} / 1M", usd(o, 5))
    line(out, "model", f"({usd(i, 5)} + {usd(o, 5)}) × {1 + OVERHEAD} overhead", usd(model, 4))
    result(out, (model, data), turn, per_trip(turn))
    saving = pct(1 - per_trip(turn) / f["a4_trip"], 0)
    out.append(f"  {usd(per_trip(turn))} is {saving}% below the naive agent ({usd(f['a4_trip'])})")
    f.update(b6_turn=turn, b6_trip=per_trip(turn), b6_saving=saving)


# --- Sections 5 and 6 ---------------------------------------------------------
def revenue():
    hotel_eur = ROOMS * NIGHTS * EUR_PER_ROOM_NIGHT
    hotel_usd = rnd(hotel_eur * USD_PER_EUR, 2)
    gross = rnd(hotel_usd * HOTEL_COMMISSION, 2)
    net = rnd(gross * (1 - CANCELLATIONS), 2)
    tour = rnd(TOUR_PEOPLE * TOUR_PRICE * TOUR_COMMISSION * TOUR_ATTACH, 2)
    single_room = rnd(rnd(D(hotel_eur) / ROOMS * USD_PER_EUR, 2) * HOTEL_COMMISSION, 2)
    return dict(hotel_eur=hotel_eur, hotel_usd=hotel_usd, gross=gross, net=net, tour=tour,
                total=net + tour, single_room=single_room)


def per_planner(turn, trip):
    friends = rnd(FRIENDS * FRIEND_TURNS * turn, 2)
    visitors = rnd(VISITORS * VISITOR_TURNS * turn, 2)
    ai = trip + friends + visitors
    bots = rnd(ai * BOTS, 2)
    infra = rnd((ai + bots) * INFRASTRUCTURE, 2)
    support = rnd(SUPPORT_CONTACT * SUPPORT_COST, 2)
    return dict(trip=trip, friends=friends, visitors=visitors, ai=ai, bots=bots, infra=infra,
                support=support, full=ai + bots + infra + support)


def in_trip():
    checks = rnd(CHECKS * (CHECK_IN * SMALL["in"] + CHECK_OUT * SMALL["out"]) / MILLION, 4)
    mix = blend(IN_TRIP_MIX)
    mix_in = effective_input(mix, QUESTION_CACHED_SHARE)
    q_in = QUESTION_IN_PER_CALL * CALLS_PER_TURN
    questions = rnd(QUESTIONS * PRIORITY_MULTIPLIER * (q_in * mix_in + QUESTION_OUT * mix["out"]) / MILLION, 4)
    voice = rnd(VOICE_EXCHANGES * VOICE_MINUTES_EACH_WAY
                * (LIVE_AUDIO_IN_PER_MINUTE + LIVE_AUDIO_OUT_PER_MINUTE), 4)
    lookups = rnd(LOOKUPS * QUERIES_PER_GROUNDED_PROMPT * SEARCH_QUERY, 4)
    subtotal = checks + questions + voice + lookups
    day = rnd(subtotal * (1 + INFRASTRUCTURE), 4)
    activity = rnd(ACTIVITY_DAY_SHARE * ACTIVITY_PRICE * ACTIVITY_COMMISSION, 3)
    transport = rnd(TRANSPORT_DAY_SHARE * TRANSPORT_PRICE * TRANSPORT_COMMISSION, 3)
    day_revenue = activity + transport
    cost = rnd(TRIP_DAYS * day, 2)
    income = rnd(TRIP_DAYS * day_revenue, 2)
    return dict(checks=checks, mix=mix, mix_in=mix_in, q_in=q_in, questions=questions, voice=voice,
                lookups=lookups, subtotal=subtotal, day=day, activity=activity, transport=transport,
                day_revenue=day_revenue, cost=cost, revenue=income, net=income - cost)


def section_5(f, out):
    title(out, "5. From one planner to one booking")
    r = revenue()
    out.append(f"  hotel   {ROOMS} rooms × {NIGHTS} nights × €{EUR_PER_ROOM_NIGHT} = €{r['hotel_eur']:,}"
               f" ≈ {usd(r['hotel_usd'])} (at {USD_PER_EUR} $/€)")
    out.append(f"          × {share(HOTEL_COMMISSION)} affiliate commission = {usd(r['gross'])}")
    out.append(f"          − {share(CANCELLATIONS)} cancellations         = {usd(r['net'])}")
    out.append(f"  wine tour  {TOUR_PEOPLE} people × ${TOUR_PRICE} × {share(TOUR_COMMISSION)} commission"
               f" × {share(TOUR_ATTACH)} of groups = {usd(r['tour'])}")
    out.append(f"  revenue per booking = {usd(r['net'])} + {usd(r['tour'])} = {usd(r['total'])}")
    out.append(f"  (a single room would earn {usd(r['single_room'])} before cancellations)")

    errors = rnd(ERROR_RATE * ERROR_COST, 2)
    after_errors = r["total"] - errors
    trip_net = in_trip()["net"]
    with_trip = after_errors + trip_net
    builds = (("eng", "Engineered build (B6)", f["b6_turn"], f["b6_trip"]),
              ("naive", "Naive agent (A4)", f["a4_turn"], f["a4_trip"]))
    for key, label, turn, trip in builds:
        p = per_planner(turn, trip)
        out.append(f"  {label}, {usd(turn, 4)} per turn:")
        out.append(f"    planner's trip {TURNS} turns {usd(p['trip'])} + friends {FRIENDS} × {FRIEND_TURNS} turns"
                   f" {usd(p['friends'])} + visitors {VISITORS} × {VISITOR_TURNS} turns {usd(p['visitors'])}"
                   f" = AI total {usd(p['ai'])}")
        out.append(f"    + bots {usd(p['bots'])} + infrastructure {usd(p['infra'])}"
                   f" + support {usd(p['support'])} = cost per planner {usd(p['full'])}")
        places = 0 if key == "naive" else 1  # round once, straight to the precision shown
        rates = (pct(p["trip"] / r["total"], places), pct(p["ai"] / r["total"], places),
                 pct(p["full"] / after_errors, places), pct(p["full"] / with_trip, places))
        out.append(f"    break-even: trip only {rates[0]}% | + friends and visitors {rates[1]}%"
                   f" | + bots, infrastructure, support, errors {rates[2]}%"
                   f" | + in-trip net margin {rates[3]}%")
        groups = PLANNING_GROUPS_PER_BOOKING * p["ai"]
        out.append(f"    {PLANNING_GROUPS_PER_BOOKING} planning groups × {usd(p['ai'])} = {usd(groups)}"
                   f" of AI cost per booking vs {usd(r['total'])} revenue")
        f.update({f"{key}_ai": p["ai"], f"{key}_full": p["full"], f"{key}_groups": groups,
                  f"be_{key}_trip": rates[0], f"be_{key}_headline": rates[1],
                  f"be_{key}_full": rates[2], f"be_{key}_intrip": rates[3]})
    per_booking = rnd(f["eng_full"] / CONVERSION, 2) + errors
    out.append(f"  cost per booking at {share(CONVERSION)} = {usd(f['eng_full'])} ÷ {share(CONVERSION)}"
               f" + {usd(errors)} = {usd(per_booking)} vs revenue {usd(r['total'])}")
    out.append(f"  revenue for break-even: {usd(r['total'])} − {usd(errors)} errors = {usd(after_errors)};"
               f" + {usd(trip_net)} in-trip net margin = {usd(with_trip)}")
    f.update(revenue=r["total"], errors=errors, eng_per_booking=per_booking,
             revenue_after_errors=after_errors, revenue_with_trip=with_trip)


def section_6(f, out):
    title(out, "6. After the booking: the trip itself (4 travellers, per day)")
    t = in_trip()
    line(out, "checks", f"{CHECKS} × ({tok(CHECK_IN)} × {price(SMALL['in'])}"
                        f" + {CHECK_OUT} × {price(SMALL['out'])}) / 1M", usd(t["checks"], 4))
    line(out, "questions", f"{QUESTIONS} × {PRIORITY_MULTIPLIER} × ({tok(t['q_in'])} × {price(t['mix_in'])}"
                           f" + {tok(QUESTION_OUT)} × {price(t['mix']['out'])}) / 1M", usd(t["questions"], 4))
    line(out, "voice", f"{VOICE_EXCHANGES} × {VOICE_MINUTES_EACH_WAY} min × ({rate(LIVE_AUDIO_IN_PER_MINUTE)}"
                       f" + {rate(LIVE_AUDIO_OUT_PER_MINUTE)}) per min", usd(t["voice"], 4))
    line(out, "lookups", f"{LOOKUPS} × {QUERIES_PER_GROUNDED_PROMPT} × {rate(SEARCH_QUERY)}", usd(t["lookups"], 4))
    line(out, "subtotal", "", usd(t["subtotal"], 4))
    line(out, f"+{share(INFRASTRUCTURE)}", f"{usd(t['subtotal'], 4)} × {(1 + INFRASTRUCTURE).normalize()}",
         f"{usd(t['day'], 4)} per day")
    line(out, "activity", f"{share(ACTIVITY_DAY_SHARE)} × ${ACTIVITY_PRICE} × {share(ACTIVITY_COMMISSION)}",
         usd(t["activity"], 3))
    line(out, "transport", f"{share(TRANSPORT_DAY_SHARE)} × ${TRANSPORT_PRICE} × {share(TRANSPORT_COMMISSION)}",
         usd(t["transport"], 3))
    line(out, "revenue", "per day", usd(t["day_revenue"], 3))
    out.append(f"  over {TRIP_DAYS} days: cost {TRIP_DAYS} × {usd(t['day'], 4)} = {usd(t['cost'])},"
               f" revenue {TRIP_DAYS} × {usd(t['day_revenue'], 3)} = {usd(t['revenue'])},"
               f" net margin {usd(t['net'])}")
    f.update(intrip_day=t["day"], intrip_cost=t["cost"], intrip_revenue=t["revenue"], intrip_net=t["net"])


def calculate():
    """Work through sections 1 to 6. Returns (figures, report lines)."""
    check()
    figures, out = {}, []
    for section in (section_1, section_2, section_3, section_4, section_5, section_6):
        section(figures, out)
    return figures, out


# --- Command line -------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Rerun every sum in tuscany_tokenomics_research.md, step by step.",
        epilog="Example: python3 tuscany_tokenomics_calculator.py --set CONVERSION=0.08 --set SESSIONS=2. "
               "Prices and mixes (PRO, ROUTING, ...) can only be changed by editing the file.")
    parser.add_argument("--set", action="append", default=[], dest="changes", metavar="NAME=VALUE",
                        help="change one assumption for this run; repeat it to change several (see --list)")
    parser.add_argument("--list", action="store_true", help="list the assumptions --set can change, then stop")
    args = parser.parse_args(argv)

    if args.list:
        for name, value in sorted(settable().items()):
            print(f"{name:<28} {value}")
        return 0

    changes = {}
    for item in args.changes:
        name, sep, text = item.partition("=")
        name = name.strip().upper()
        if not sep:
            parser.error(f"--set expects NAME=VALUE, for example --set CONVERSION=0.08 (got {item!r})")
        current = settable().get(name)
        if current is None:
            parser.error(f"{name!r} isn't an assumption --set can change; run with --list to see them")
        try:
            value = int(text) if isinstance(current, int) else D(text.strip())
        except (ValueError, InvalidOperation):
            value = None
        if value is None or not D(value).is_finite():
            kind = "whole number" if isinstance(current, int) else "number"
            parser.error(f"{name} needs a {kind}, not {text!r}")
        changes[name] = value

    with assumptions(**changes):
        try:
            report = calculate()[1]
        except ValueError as problem:
            parser.error(str(problem))
    print("One Tuscany trip, costed by hand: every step in tuscany_tokenomics_research.md")
    if changes:
        print("Changed for this run: " + ", ".join(f"{name}={value}" for name, value in changes.items()))
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
