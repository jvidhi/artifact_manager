#!/usr/bin/env python3
"""Tests for tuscany_tokenomics_calculator.py.

Six kinds of check:

1. The calculator still produces every published figure.
2. The assumptions are internally consistent (for example, the routing shares add up).
3. Other assumptions move the results the way they should, and impossible ones are refused.
4. The command line (--set, --list) works and explains bad input.
5. The documents show the calculator's figures and assumptions, so the code
   and the Markdown can't drift apart.
6. Every relative link in the documents points to a file and heading that exist.

    python3 -m unittest
"""

import os
import re
import subprocess
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tuscany_tokenomics_calculator as calc  # noqa: E402

RESEARCH = "tuscany_tokenomics_research.md"
STUDY = "tokenomics_study.md"
README = "README.md"
DOCS = (README, STUDY, RESEARCH, "LICENSE-docs.md")

FIG, REPORT = calc.calculate()

# Every figure the calculator returns, as published in the research notes.
PUBLISHED = {
    # Section 1: one turn
    "one_turn_input": "23500", "one_turn": "0.085",
    # Section 2: the back-of-envelope
    "s0_input": "24250", "s0_turn": "0.0865", "s0_trip": "6.92",
    # Section 3: the naive agent
    "a1_turn": "0.1665", "a1_trip": "13.32", "output_with_tools": "2600",
    "a2_input": "203125", "a2_turn": "0.4515", "a2_trip": "36.12",
    "a3_turn": "0.1407", "a3_trip": "11.26",
    "a4_data": "0.0261", "a4_model": "0.1267", "a4_turn": "0.1528", "a4_trip": "12.22",
    "mid_turn": "0.1172", "mid_trip": "9.38",
    "small_turn": "0.0419", "small_trip": "3.35",
    "small_model_trip": "1.26", "small_data_trip": "2.09",
    # Section 4: the engineered build
    "compacted_input": "28750",
    "b1_turn": "0.0889", "b1_trip": "7.11",
    "b2_turn": "0.0757", "b2_trip": "6.06",
    "b3_turn": "0.0417", "b3_trip": "3.34",
    "b4_turn": "0.0456", "b4_trip": "3.65",
    "b5_turn": "0.0330", "b5_trip": "2.64",
    "b6_turn": "0.0252", "b6_trip": "2.02",
    "b6_saving": "83",
    # Section 5: from one planner to one booking
    "revenue": "56.90", "errors": "1.20",
    "revenue_after_errors": "55.70", "revenue_with_trip": "80.83",
    "eng_ai": "3.75", "eng_full": "5.42", "eng_groups": "56.25", "eng_per_booking": "109.60",
    "naive_ai": "22.77", "naive_full": "31.38", "naive_groups": "341.55",
    "be_eng_trip": "3.6", "be_eng_headline": "6.6", "be_eng_full": "9.7", "be_eng_intrip": "6.7",
    "be_naive_trip": "21", "be_naive_headline": "40", "be_naive_full": "56", "be_naive_intrip": "39",
    # Section 6: the trip itself
    "intrip_day": "0.4919", "intrip_cost": "1.97", "intrip_revenue": "27.10", "intrip_net": "25.13",
}
PUBLISHED_ROUTING_TIERS = {"small": 70, "mid": 25, "frontier": 5}


# --- Formatting, as the documents write numbers --------------------------------
def money(x, places=2):
    """$1,234.56, rounded half-up like the documents."""
    return f"${calc.rnd(x, places):,.{places}f}"


def share(x):
    """A share as a percentage without trailing zeros: 0.85 -> '85%', 0.045 -> '4.5%'."""
    return f"{(D(x) * 100).normalize():f}%"


def split(mix):
    """A routing mix as the documents write it: '70/25/5'."""
    return "/".join(f"{(v * 100).normalize():f}" for v in mix.values())


def tier_parts(tier):
    """The task shares that make up one tier, in table order: [30, 30, 10] for small."""
    return [s[tier] for s in calc.TASK_SHARES.values() if tier in s]


def slugs(markdown):
    """GitHub-style anchors for every heading in a Markdown document."""
    found = set()
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", markdown, flags=re.M):
        found.add(re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-"))
    return found


def read(name):
    return (HERE / name).read_text(encoding="utf-8")


# --- 1. Published figures ------------------------------------------------------
class PublishedFigures(unittest.TestCase):
    """The calculator reproduces every figure in the research notes."""

    def test_every_figure_is_pinned(self):
        self.assertEqual(set(FIG) - {"routing_tiers"}, set(PUBLISHED))

    def test_figures(self):
        for key, value in PUBLISHED.items():
            with self.subTest(key):
                self.assertEqual(FIG[key], D(value))

    def test_routing_tiers(self):
        self.assertEqual(FIG["routing_tiers"], PUBLISHED_ROUTING_TIERS)

    def test_script_prints_the_report(self):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        result = subprocess.run([sys.executable, "-B", str(HERE / "tuscany_tokenomics_calculator.py")],
                                capture_output=True, encoding="utf-8", env=env, check=True)
        self.assertEqual(result.stdout.splitlines()[1:], REPORT)
        self.assertIn("= $0.0252  →  × 80 = $2.02 per trip", result.stdout)


# --- 2. Assumptions ------------------------------------------------------------
class Assumptions(unittest.TestCase):
    """The assumptions are internally consistent."""

    def test_task_shares_add_up_to_100(self):
        self.assertEqual(sum(sum(s.values()) for s in calc.TASK_SHARES.values()), 100)

    def test_task_shares_match_the_routing_split(self):
        tiers = {tier: D(pct) / 100 for tier, pct in FIG["routing_tiers"].items()}
        self.assertEqual(tiers, calc.ROUTING)

    def test_mixes_add_up_to_one(self):
        for name in ("ROUTING", "ROUTING_TUNED", "IN_TRIP_MIX"):
            with self.subTest(name):
                self.assertEqual(sum(getattr(calc, name).values()), 1)

    def test_calls_per_turn(self):
        # 1.5 tool calls, then 1 call that writes the answer
        self.assertEqual(calc.CALLS_PER_TURN - 1, D("1.5"))

    def test_tool_tokens_estimate(self):
        # 9,000 characters of JSON at about 3 per token, plus 12,000 of text at about 4
        self.assertEqual(9_000 // 3 + 12_000 // 4, calc.TOOL_TOKENS)

    def test_rounded_rates_in_prose(self):
        # "about 1 in 15" (6.6%), "about 1 in 10" (9.7%) and "more than 2 in 5" (40%)
        self.assertLess(abs(100 / FIG["be_eng_headline"] - calc.PLANNING_GROUPS_PER_BOOKING), 1)
        self.assertEqual(calc.rnd(100 / FIG["be_eng_full"], 0), 10)
        self.assertEqual(D(2) / 5 * 100, FIG["be_naive_headline"])


# --- 3. Other assumptions --------------------------------------------------------
class Scenarios(unittest.TestCase):
    """Change an assumption and the results move the way they should; impossible ones are refused."""

    NAIVE = ("s0", "a1", "a2", "a3", "a4")
    ENGINEERED = ("b1", "b2", "b3", "b4", "b5", "b6")

    def run_with(self, **changes):
        with calc.assumptions(**changes):
            figures, report = calc.calculate()
        return figures, "\n".join(report)

    def test_more_sessions_scale_every_trip_cost(self):
        figures, _ = self.run_with(SESSIONS=8)
        for step in self.NAIVE + self.ENGINEERED:
            with self.subTest(step):
                self.assertEqual(figures[f"{step}_turn"], FIG[f"{step}_turn"])
                self.assertLessEqual(abs(figures[f"{step}_trip"] - 2 * FIG[f"{step}_trip"]), D("0.01"))

    def test_shorter_sessions_only_cheapen_the_naive_agent(self):
        figures, report = self.run_with(TURNS_PER_SESSION=10)
        for step in self.NAIVE:
            with self.subTest(step):
                self.assertLess(figures[f"{step}_turn"], FIG[f"{step}_turn"])
        for step in self.ENGINEERED:  # compaction caps the history from B1 on
            with self.subTest(step):
                self.assertEqual(figures[f"{step}_turn"], FIG[f"{step}_turn"])
        self.assertIn("turn 10 sends 23,500", report)

    def test_without_caching_a3_saves_nothing(self):
        figures, _ = self.run_with(CACHED_SHARE=D("0"))
        self.assertEqual(figures["a3_turn"], figures["a2_turn"])

    def test_conversion_moves_cost_per_booking_not_break_even(self):
        figures, report = self.run_with(CONVERSION=D("0.10"))
        self.assertEqual(figures["eng_per_booking"], calc.rnd(FIG["eng_full"] / D("0.10"), 2) + FIG["errors"])
        for key in ("be_eng_headline", "be_eng_full", "be_naive_headline", "be_naive_full"):
            with self.subTest(key):
                self.assertEqual(figures[key], FIG[key])
        self.assertIn("cost per booking at 10% =", report)

    def test_no_grounding_leaves_only_maps_in_b5(self):
        figures, report = self.run_with(GROUNDED_PROMPTS_SELECTIVE=D("0"))
        maps = calc.rnd(calc.MAPS_CALLS_PER_TURN * calc.MAPS_CALL, 4)
        self.assertEqual(figures["b5_turn"], FIG["b4_turn"] - FIG["a4_data"] + maps)
        self.assertIn("0 × 1.5 × $0.014 + 0.3 × $0.017", report)

    def test_changed_prices_reach_every_step_that_uses_them(self):
        figures, report = self.run_with(PRO=dict(calc.PRO, **{"in": D("3.00")}))
        self.assertGreater(figures["a4_trip"], FIG["a4_trip"])
        self.assertGreater(figures["b3_turn"], FIG["b3_turn"])  # the routing blend picks up the new price
        self.assertEqual(figures["small_trip"], FIG["small_trip"])  # Flash-Lite didn't change
        self.assertIn("23,500 × $3 / 1M", report)

    def test_in_trip_revenue_follows_the_activity_rate(self):
        figures, _ = self.run_with(ACTIVITY_DAY_SHARE=D("0.50"))
        self.assertGreater(figures["intrip_revenue"], FIG["intrip_revenue"])
        self.assertEqual(figures["intrip_cost"], FIG["intrip_cost"])

    def test_impossible_assumptions_are_refused(self):
        bad = {"CONVERSION": D("0"), "CACHED_SHARE": D("1.5"), "TURNS_PER_SESSION": 0, "SESSIONS": -1,
               "MAPS_CALL": D("-0.01"), "ROUTING": {"small": D("0.80"), "mid": D("0.25"), "frontier": D("0.05")}}
        for name, value in bad.items():
            with self.subTest(name), self.assertRaisesRegex(ValueError, name):
                self.run_with(**{name: value})

    def test_only_real_assumptions_can_be_changed(self):
        for name in ("SESION", "TURNS", "MILLION", "D", "rnd"):
            with self.subTest(name), self.assertRaises(ValueError):
                self.run_with(**{name: 1})

    def test_assumptions_are_put_back(self):
        with self.assertRaises(ValueError):
            self.run_with(SESSIONS=2, CONVERSION=D("0"))
        self.assertEqual((calc.SESSIONS, calc.TURNS, calc.CONVERSION), (4, 80, D("0.05")))
        self.assertEqual(calc.calculate()[0], FIG)


# --- 4. The command line -----------------------------------------------------------
class CommandLine(unittest.TestCase):
    """--set and --list work, and bad input gets a clear message."""

    def run_script(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        return subprocess.run([sys.executable, "-B", str(HERE / "tuscany_tokenomics_calculator.py"), *args],
                              capture_output=True, encoding="utf-8", env=env)

    def test_set_changes_one_assumption(self):
        result = self.run_script("--set", "CONVERSION=0.10")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Changed for this run: CONVERSION=0.10", result.stdout)
        expected = calc.rnd(FIG["eng_full"] / D("0.10"), 2) + FIG["errors"]
        self.assertIn(f"cost per booking at 10% = {money(FIG['eng_full'])} ÷ 10% + {money(FIG['errors'])}"
                      f" = {money(expected)}", result.stdout)

    def test_set_is_repeatable_and_ignores_case(self):
        result = self.run_script("--set", "sessions=2", "--set", "TURNS_PER_SESSION=15")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Changed for this run: SESSIONS=2, TURNS_PER_SESSION=15", result.stdout)
        self.assertIn("  →  × 30 = ", result.stdout)

    def test_bad_input_gets_a_clear_error(self):
        cases = ((["--set", "CONVERSION=abc"], "CONVERSION needs a number"),
                 (["--set", "CACHED_SHARE=nan"], "CACHED_SHARE needs a number"),
                 (["--set", "SESSIONS=2.5"], "SESSIONS needs a whole number"),
                 (["--set", "NOPE=1"], "run with --list"),
                 (["--set", "TURNS=10"], "run with --list"),
                 (["--set", "CONVERSION"], "--set expects NAME=VALUE"),
                 (["--set", "CONVERSION=0"], "CONVERSION must be above 0"),
                 (["--set", "CACHED_SHARE=1.5"], "must be between 0 and 1"))
        for args, message in cases:
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)

    def test_list_shows_what_can_be_set(self):
        result = self.run_script("--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"(?m)^CONVERSION\s+0\.05$")
        self.assertRegex(result.stdout, r"(?m)^SESSIONS\s+4$")
        self.assertNotRegex(result.stdout, r"(?m)^(TURNS|MILLION|PRO|ROUTING)\s")

    def test_help(self):
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--set NAME=VALUE", result.stdout)


# --- 5. The documents match the calculator --------------------------------------
class DocsMatchCalculator(unittest.TestCase):
    """Both documents show the calculator's figures and assumptions."""

    @classmethod
    def setUpClass(cls):
        cls.docs = {name: read(name) for name in (README, STUDY, RESEARCH)}

    def check(self, doc, *snippets):
        for snippet in snippets:
            with self.subTest(doc=doc, snippet=snippet):
                self.assertTrue(snippet in self.docs[doc], f"{snippet!r} not found in {doc}")

    def both(self, *snippets):
        self.check(RESEARCH, *snippets)
        self.check(STUDY, *snippets)

    def test_prices(self):
        for p in (calc.PRO, calc.MID, calc.SMALL):
            self.check(RESEARCH, f"| {calc.price(p['in'])} | {calc.price(p['out'])} | {calc.price(p['cached'])} |")
        self.check(RESEARCH,
                   f"(${calc.SEARCH_QUERY} each)",
                   f"{calc.PRIORITY_MULTIPLIER}× the standard price",
                   f"${calc.LIVE_AUDIO_IN_PER_MINUTE} per minute of audio in"
                   f" and ${calc.LIVE_AUDIO_OUT_PER_MINUTE} per minute out")
        self.check(STUDY,
                   f"${calc.PRO['in'].normalize()} per million input tokens,"
                   f" ${calc.PRO['out'].normalize()} per million output,"
                   f" ${calc.SEARCH_QUERY} per search query")

    def test_assumptions_register(self):
        rows = [
            f"| Sessions × turns per trip | {calc.SESSIONS} × {calc.TURNS_PER_SESSION} = {calc.TURNS} |",
            f"| System prompt and profile | {calc.SYSTEM_TOKENS:,} tokens |",
            f"| Tool results per turn | {calc.TOOL_TOKENS:,} tokens ({calc.TRIMMED_TOOL_TOKENS:,} when trimmed) |",
            f"| Chat history per earlier turn | {calc.CHAT_TOKENS:,} tokens |",
            f"| Output per turn, including thinking | {calc.OUTPUT_TOKENS:,}"
            f" ({FIG['output_with_tools']:,.0f} with tool calls; {calc.CAPPED_OUTPUT_TOKENS:,} when capped) |",
            f"| Model calls per turn | {calc.CALLS_PER_TURN} ({calc.CALLS_PER_TURN - 1} tool calls + 1 answer) |",
            f"| Output per tool call (request plus thinking) | {calc.OUTPUT_PER_TOOL_CALL} tokens |",
            f"| Cached share of input | {share(calc.CACHED_SHARE)} ({share(calc.CACHED_SHARE_COMPACTED)} with compaction) |",
            f"| Compacted context per call | summary {calc.SUMMARY_TOKENS:,}"
            f" + last couple of turns {calc.RECENT_TOKENS:,} tokens |",
            f"| Search queries per grounded prompt | {calc.QUERIES_PER_GROUNDED_PROMPT} |",
            f"| Direct Maps calls per turn | {calc.MAPS_CALLS_PER_TURN} at ~${calc.MAPS_CALL} (price not verified) |",
            f"| Grounded prompts per turn | 1 → {calc.GROUNDED_PROMPTS_SELECTIVE} |",
            f"| Routing split (small/mid/frontier) | {split(calc.ROUTING)} → {split(calc.ROUTING_TUNED)} |",
            f"| Overhead calls | +{share(calc.OVERHEAD)} of model cost |",
            f"| Hotel | {calc.ROOMS} rooms × {calc.NIGHTS} nights × €{calc.EUR_PER_ROOM_NIGHT};"
            f" {share(calc.HOTEL_COMMISSION)} commission; {share(calc.CANCELLATIONS)} cancelled |",
            f"| Exchange rate | {calc.USD_PER_EUR} $/€ |",
            f"| Wine tour | {calc.TOUR_PEOPLE} × ${calc.TOUR_PRICE}; {share(calc.TOUR_COMMISSION)} commission;"
            f" {share(calc.TOUR_ATTACH)} attach rate |",
            f"| Friends and visitors | {calc.FRIENDS} × {calc.FRIEND_TURNS} turns;"
            f" {calc.VISITORS} × {calc.VISITOR_TURNS} turns |",
            f"| Bots / infrastructure / support | +{share(calc.BOTS)} / +{share(calc.INFRASTRUCTURE)}"
            f" / {share(calc.SUPPORT_CONTACT)} × ${calc.SUPPORT_COST} |",
            f"| Conversion; booking errors | {share(calc.CONVERSION)} (illustrative);"
            f" {share(calc.ERROR_RATE)} × ${calc.ERROR_COST} |",
            f"| {calc.CHECKS} checks ({calc.CHECK_IN:,} tokens in, {calc.CHECK_OUT} out);"
            f" {calc.QUESTIONS} questions ({calc.CALLS_PER_TURN} calls × {calc.QUESTION_IN_PER_CALL:,} tokens in,"
            f" half cached; {calc.QUESTION_OUT:,} out); {calc.VOICE_EXCHANGES} voice exchanges of"
            f" {calc.VOICE_MINUTES_EACH_WAY} minute each way; {calc.LOOKUPS} grounded lookups |",
            f"an {split(calc.IN_TRIP_MIX)} small/mid mix at Priority prices",
            f"| activity {share(calc.ACTIVITY_DAY_SHARE)} × ${calc.ACTIVITY_PRICE} × {share(calc.ACTIVITY_COMMISSION)};"
            f" transport {share(calc.TRANSPORT_DAY_SHARE)} × ${calc.TRANSPORT_PRICE}"
            f" × {share(calc.TRANSPORT_COMMISSION)}; {calc.TRIP_DAYS} days |",
        ]
        self.assertEqual(calc.QUESTION_CACHED_SHARE, D("0.5"))  # "half cached"
        self.check(RESEARCH, *rows)

    def test_section_1_one_turn(self):
        i = calc.rnd(FIG["one_turn_input"] * calc.PRO["in"] / calc.MILLION, 3)
        o = calc.rnd(calc.OUTPUT_TOKENS * calc.PRO["out"] / calc.MILLION, 3)
        first = calc.SYSTEM_TOKENS + calc.TOOL_TOKENS
        last = first + (calc.TURNS_PER_SESSION - 1) * calc.CHAT_TOKENS
        self.both(f"= {money(i, 3)}", f"= {money(o, 3)}", f"= {money(calc.SEARCH_QUERY, 3)}",
                  f"= {money(FIG['one_turn'], 3)}", f"{(FIG['one_turn'] * 100).normalize():f} cents",
                  f"sends {first:,}", f"sends {last:,}")
        self.check(RESEARCH,
                   f"profile: **{calc.SYSTEM_TOKENS:,}** tokens",
                   f"ZTL page): **{calc.TOOL_TOKENS:,}** tokens",
                   f"at {calc.CHAT_TOKENS:,} each: **{9 * calc.CHAT_TOKENS:,}** tokens",
                   f"**total input: {FIG['one_turn_input']:,} tokens**",
                   f"**{calc.OUTPUT_TOKENS:,}** tokens",
                   f"≈ {calc.TOOL_TOKENS:,} tokens")
        self.check(STUDY,
                   f"about **{FIG['one_turn_input']:,} tokens**",
                   f"profile: {calc.SYSTEM_TOKENS:,}",
                   f"rules: {calc.TOOL_TOKENS:,}",
                   f"session: {9 * calc.CHAT_TOKENS:,}",
                   f"about **{calc.OUTPUT_TOKENS:,} tokens**",
                   f"9,000 ÷ 3 + 12,000 ÷ 4 = {calc.TOOL_TOKENS:,} tokens")

    def test_section_2_back_of_envelope(self):
        tokens = calc.TURNS * (FIG["s0_input"] + calc.OUTPUT_TOKENS) / calc.MILLION
        self.check(RESEARCH,
                   f"= {FIG['s0_input']:,.0f} tokens",
                   f"= {money(FIG['s0_turn'], 4)}",
                   f"= {money(FIG['s0_trip'])} per planned trip",
                   f"{calc.TURNS} × {FIG['s0_input']:,.0f} = **{calc.TURNS * FIG['s0_input'] / calc.MILLION:.2f}M"
                   f" input tokens**")
        self.check(STUDY,
                   f"{FIG['s0_input']:,.0f} tokens and costs **{money(FIG['s0_turn'], 4)}**",
                   f"**{money(FIG['s0_trip'])} per planned trip**",
                   f"about {calc.rnd(tokens, 0)} million tokens")

    def test_sections_3_and_4_cost_per_turn_and_trip(self):
        for step in ("a1", "a2", "a3", "a4", "b1", "b2", "b3", "b4", "b5", "b6"):
            turn, trip = FIG[f"{step}_turn"], FIG[f"{step}_trip"]
            self.check(RESEARCH, f"= {money(turn, 4)}  →  × {calc.TURNS} = {money(trip)} per trip")
        self.check(STUDY, *(f"**{money(FIG[f'{s}_trip'])}**" for s in ("a1", "a2", "a3", "a4")))
        self.check(STUDY, *(f"| {money(FIG[f'b{n}_trip'])} |" for n in range(1, 6)))
        self.check(STUDY, f"| **{money(FIG['b6_trip'])}** |")
        history = calc.CHAT_TOKENS + calc.TOOL_TOKENS
        self.check(RESEARCH, f"leaves **{history:,}** tokens behind")
        self.check(STUDY, f"leaves {history:,} tokens behind instead of {calc.CHAT_TOKENS:,}")
        self.both(f"drops from {share(calc.CACHED_SHARE)} to")

    def test_section_3_model_choice(self):
        for key in ("a4", "mid", "small"):
            turn, trip = FIG[f"{key}_turn"], FIG[f"{key}_trip"]
            self.check(RESEARCH, f"| {money(turn, 4)} | **{money(trip)}** |")
            self.check(STUDY, f"| about {calc.rnd(turn * 100, 0)}¢ | {money(trip)} |")
        self.check(RESEARCH, f"= {money(FIG['small_data_trip'])} per trip", f"= {money(FIG['small_model_trip'])}.")
        self.check(STUDY, f"cost {money(FIG['small_data_trip'])} per trip",
                   f"costs {money(FIG['small_model_trip'])}.")
        self.check(STUDY, f"**about {calc.rnd(FIG['b6_turn'] * 100, 1)}¢** | **{money(FIG['b6_trip'])}**")
        self.both(f"about {calc.rnd(FIG['a4_trip'] / FIG['s0_trip'], 1)} times",
                  f"about {calc.rnd(FIG['a4_turn'] * 100, 0)} cents per question",
                  f"{calc.rnd(FIG['b6_turn'] * 100, 1)} cents per question")
        self.check(RESEARCH, f"{FIG['b6_saving']}% below the naive agent ({money(FIG['a4_trip'])})")

    def test_section_4_routing(self):
        tiers = FIG["routing_tiers"]
        sums = (f"small {' + '.join(map(str, tier_parts('small')))} = **{tiers['small']}%**,"
                f" mid {' + '.join(map(str, tier_parts('mid')))} = **{tiers['mid']}%**"
                f" and frontier **{tiers['frontier']}%**")
        self.both(sums, *(f"| {sum(s.values())}% |" for s in calc.TASK_SHARES.values()))
        self.check(STUDY,
                   f"({tiers['small']}% small, {tiers['mid']}% mid, {tiers['frontier']}% frontier)",
                   f"from {split(calc.ROUTING)} to {split(calc.ROUTING_TUNED)}",
                   f"retries: +{share(calc.OVERHEAD)})")

    def test_section_5_booking(self):
        r = calc.revenue()
        eng = calc.per_planner(FIG["b6_turn"], FIG["b6_trip"])
        naive = calc.per_planner(FIG["a4_turn"], FIG["a4_trip"])
        turns = calc.TURNS + calc.FRIENDS * calc.FRIEND_TURNS + calc.VISITORS * calc.VISITOR_TURNS
        revenue_sum = f"{money(r['net'])} + {money(r['tour'])} = "

        # Revenue
        self.check(RESEARCH, revenue_sum + money(r["total"]))
        self.check(STUDY, revenue_sum + f"**{money(r['total'])}**",
                   f"€{r['hotel_eur']:,}, or about {money(r['hotel_usd'], 0)}",
                   f"that's {money(r['gross'])}", f"it's {money(r['net'])}", f"adds {money(r['tour'])}",
                   f"about ${calc.rnd(r['single_room'], 0)} before cancellations")

        # Cost per planner, on both builds
        for row in ("trip", "friends", "visitors"):
            self.both(f"| {money(eng[row])} | {money(naive[row])} |")
        for row in ("bots", "infra", "support"):
            self.check(RESEARCH, f"| {money(eng[row])} | {money(naive[row])} |")
        self.both(f"| **{money(eng['ai'])}** | **{money(naive['ai'])}** |")
        self.check(RESEARCH, f"| {turns} turns |", f"| **{money(eng['full'])}** | **{money(naive['full'])}** |",
                   f"{money(FIG['b6_turn'], 4)} on the engineered build (B6) and"
                   f" {money(FIG['a4_turn'], 4)} on the naive agent (A4)")

        # Cost per booking
        self.check(RESEARCH,
                   f"= {money(FIG['errors'])} per booking",
                   f"{money(FIG['eng_full'])} ÷ {share(calc.CONVERSION)} + {money(FIG['errors'])}"
                   f" = {money(FIG['eng_per_booking'])}")
        self.check(STUDY, f"**{money(FIG['eng_per_booking'])} per booking to earn {money(FIG['revenue'])}**")

        # Break-even conversion
        self.check(RESEARCH,
                   f"{money(FIG['revenue'])} − {money(FIG['errors'])} = {money(FIG['revenue_after_errors'])}",
                   f"{money(FIG['revenue_after_errors'])} + {money(FIG['intrip_net'])}"
                   f" = {money(FIG['revenue_with_trip'])}",
                   f"+{money(FIG['intrip_net'])})")
        layers = (("trip", "trip", "revenue"), ("ai", "headline", "revenue"),
                  ("full", "full", "revenue_after_errors"), ("full", "intrip", "revenue_with_trip"))
        for cost, rate, revenue in layers:
            for key, build in (("eng", eng), ("naive", naive)):
                self.check(RESEARCH, f"{money(build[cost])} ÷ {money(FIG[revenue])} = **{FIG[f'be_{key}_{rate}']}%**")
        full_groups = int(calc.rnd(100 / FIG["be_eng_full"], 0))  # "about 1 in 10"
        self.check(STUDY,
                   f"**{FIG['be_eng_headline']}%** (about 1 in {calc.PLANNING_GROUPS_PER_BOOKING})"
                   f" | {FIG['be_naive_headline']}% |",
                   f"**{FIG['be_eng_full']}%** (about 1 in {full_groups}) | {FIG['be_naive_full']}% |",
                   f"**{FIG['be_eng_intrip']}%** | {FIG['be_naive_intrip']}% |",
                   f"(+{share(calc.INFRASTRUCTURE)})",
                   "more than 2 in 5 planners book")
        self.both(f"{FIG['be_naive_headline']}–{FIG['be_naive_full']}%")
        self.check(RESEARCH, f"about **1 in {full_groups}** ({FIG['be_eng_full']}%)")
        self.check(STUDY, f"about 1 in {full_groups} once infrastructure, support and errors are counted")

        # Each booking pays for the AI chats of PLANNING_GROUPS_PER_BOOKING planning groups
        groups = calc.PLANNING_GROUPS_PER_BOOKING
        self.check(RESEARCH, f"{groups} × {money(eng['ai'])}", f"{groups} × {money(naive['ai'])}",
                   f"= {money(FIG['eng_groups'])} of AI cost per booking",
                   f"= {money(FIG['naive_groups'])} of AI cost per booking")
        self.check(STUDY, f"{groups} × {money(eng['ai'])} = **{money(FIG['eng_groups'])}**",
                   f"{groups} × {money(naive['ai'])} = **{money(FIG['naive_groups'])}**")

    def test_section_6_in_trip(self):
        t = calc.in_trip()
        days = calc.TRIP_DAYS
        self.check(RESEARCH, *(f"= {money(t[key], 4)}" for key in ("checks", "questions", "voice", "lookups",
                                                                   "subtotal")))
        self.check(RESEARCH,
                   f"{calc.QUESTIONS} × {calc.PRIORITY_MULTIPLIER} × ({t['q_in']:,.0f} × {calc.price(t['mix_in'])}"
                   f" + {calc.QUESTION_OUT:,} × {calc.price(t['mix']['out'])}) / 1M",
                   f"= {calc.price(t['mix']['in'])} per 1M input tokens, or {calc.price(t['mix']['cached'])} cached",
                   f"= {calc.price(t['mix_in'])}.",
                   f"= {calc.price(t['mix']['out'])} per 1M.",
                   f"{money(t['subtotal'], 4)} × {(1 + calc.INFRASTRUCTURE).normalize()}",
                   f"= {money(t['day'], 4)} per day",
                   f"= **{money(t['activity'])}**",
                   f"= **{money(t['transport'], 3)}**",
                   f"{money(t['activity'])} + {money(t['transport'], 3)} = **{money(t['day_revenue'], 3)} per day**",
                   f"{days} × {money(t['day_revenue'], 3)} = **{money(FIG['intrip_revenue'])}",
                   f"{money(FIG['intrip_revenue'])} − {money(FIG['intrip_cost'])} = **{money(FIG['intrip_net'])}**")
        self.both(f"{days} × {money(t['day'], 4)} = **{money(FIG['intrip_cost'])}")
        self.check(STUDY,
                   f"costs about **{money(t['day'])}**",
                   f"about **{money(t['day_revenue'])}** a day",
                   f"{days} × {money(t['day_revenue'], 3)} = **{money(FIG['intrip_revenue'])} earned**",
                   f"{calc.QUESTIONS} group questions",
                   f"costs about ${calc.rnd(FIG['intrip_cost'], 0)} over a {days}-day trip"
                   f" and earns about ${calc.rnd(FIG['intrip_revenue'], 0)}")

    def test_readme(self):
        self.check(README,
                   f"**{money(FIG['a4_trip'])}**",
                   f"says {money(FIG['s0_trip'])}",
                   f"**{money(FIG['b6_trip'])}**",
                   f"({FIG['be_eng_headline']}%)",
                   f"needs {FIG['be_naive_headline']}%",
                   f"costs {money(FIG['intrip_cost'])} over a {calc.TRIP_DAYS}-day trip"
                   f" and earns {money(FIG['intrip_revenue'])}")


# --- 6. Links -----------------------------------------------------------------
class Links(unittest.TestCase):
    """Every relative link points to a file that exists, and every anchor to a heading."""

    def test_relative_links(self):
        for name in DOCS:
            for target in re.findall(r"\]\(([^)\s]+)\)", read(name)):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                with self.subTest(doc=name, link=target):
                    file_part, _, anchor = target.partition("#")
                    linked = HERE / (file_part or name)
                    self.assertTrue(linked.is_file(), f"{target} not found")
                    if anchor:
                        self.assertIn(anchor, slugs(linked.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
