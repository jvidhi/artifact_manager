# The Hidden Tokenomics of an AI Travel Agent

What does an AI travel agent really cost to run, and can the bookings pay for it? This repo follows one group trip, four friends planning 4 nights in Florence with day trips to Chianti and Siena, through every model call, search query and booking. Each step is priced with public Gemini API list prices, and every other number is a stated assumption.

It accompanies the Substack article "AI Can Plan Your Trip. Can It Get Paid for It?" A link will follow once it's published.

## The short version

- A **naive agent** (a realistic agent loop on a frontier model, with no cost engineering) costs **$12.22** per planned trip of 80 questions. The usual back-of-envelope estimate says $6.92.
- An **engineered build** brings that to **$2.02**, without moving every question to the cheapest model.
- Even then, about 1 in 15 planners (6.6%) must book through the app to cover the AI cost of everyone who chats. The naive agent needs 40%.
- The trip itself makes money: in-trip help costs $1.97 over a 4-day trip and earns $27.10 in commissions.

## What's here

Read in this order, after the article:

1. [tokenomics_study.md](tokenomics_study.md): the study. The story, the cost levers and what they mean for the business.
2. [tuscany_tokenomics_research.md](tuscany_tokenomics_research.md): the research notes. Every sum step by step, the assumptions register and the sources.
3. [tuscany_tokenomics_calculator.py](tuscany_tokenomics_calculator.py): reruns every sum in the research notes, and lets you try your own assumptions.
4. [test_tuscany_tokenomics.py](test_tuscany_tokenomics.py): checks the calculator against the published figures, runs it on other assumptions, and checks that both documents show the same figures.

## Run it

You need Python 3.9 or later. Everything uses the standard library, so there is nothing to install. Tested on Python 3.9, 3.12, 3.13 and 3.14. Run the commands from this folder.

### Run the calculator

```sh
python3 tuscany_tokenomics_calculator.py
```

It prints every step of the research notes, section by section. Each line matches a sum in the notes:

```text
One Tuscany trip, costed by hand: every step in tuscany_tokenomics_research.md

1. One turn, dissected (session 3, turn 10)
-------------------------------------------
  input      23,500 × $2 / 1M                                     = $0.047
  output     2,000 × $12 / 1M                                     = $0.024
  grounding  1 query                                              = $0.014
  turn                                                            = $0.085
  The history grows: turn 1 sends 10,000 input tokens, turn 20 sends 38,500.
```

To pull out one result, pipe it through `grep`:

```sh
python3 tuscany_tokenomics_calculator.py | grep "below the naive agent"
#   $2.02 is 83% below the naive agent ($12.22)
```

### Try your own assumptions

`--set NAME=VALUE` changes one assumption for a single run and leaves the file alone. Repeat it to change several; names aren't case-sensitive. `--list` shows every assumption you can set, with its published value:

```sh
python3 tuscany_tokenomics_calculator.py --list
# ACTIVITY_COMMISSION          0.08
# ACTIVITY_DAY_SHARE           0.25
# ACTIVITY_PRICE               320
# BOTS                         0.05
# CACHED_SHARE                 0.85
# ...
```

Some questions you can answer this way:

```sh
# What if 10% of planners book, not 5%?
python3 tuscany_tokenomics_calculator.py --set CONVERSION=0.10 | grep "cost per booking at"
#   cost per booking at 10% = $5.42 ÷ 10% + $1.20 = $55.40 vs revenue $56.90

# What if planning takes 2 sessions, not 4?
python3 tuscany_tokenomics_calculator.py --set SESSIONS=2 | grep "below the naive agent"
#   $1.01 is 83% below the naive agent ($6.11)

# What if nothing is cached? A3 then saves nothing: $36.12 per trip, the same as A2.
python3 tuscany_tokenomics_calculator.py --set CACHED_SHARE=0 | grep -A3 "^A3"

# Change several at once: 10% conversion, and an activity booked on half the trip days
python3 tuscany_tokenomics_calculator.py --set conversion=0.10 --set activity_day_share=0.5
```

The report then opens with a `Changed for this run:` line, and every working line shows your numbers. Impossible values are refused with a message instead of a wrong answer:

```sh
python3 tuscany_tokenomics_calculator.py --set CONVERSION=0
# tuscany_tokenomics_calculator.py: error: CONVERSION must be above 0
```

`--set` covers every single number: turns, tokens, shares, commissions, and the prices of a search query or a Maps call. The model prices and routing mixes (`PRO`, `MID`, `SMALL`, `ROUTING`, `ROUTING_TUNED`, `IN_TRIP_MIX`) are tables, so change those by editing the constants at the top of the calculator. After you edit the file, the tests that pin the published figures will fail. That's expected. `--set` never changes the file, so the tests keep passing.

### Run the tests

```sh
python3 -m unittest                                                  # all 36 tests, in about a second
python3 -m unittest -v                                               # one line per test
python3 -m unittest test_tuscany_tokenomics.Scenarios -v             # one group
python3 -m unittest test_tuscany_tokenomics.CommandLine.test_help    # one test
```

A passing run ends like this:

```text
----------------------------------------------------------------------
Ran 36 tests in 0.802s

OK
```

| Group | What it checks |
|---|---|
| `PublishedFigures` | The calculator still produces every figure published in the research notes. |
| `Assumptions` | The assumptions are consistent, for example the routing shares add up to 100%. |
| `Scenarios` | Other assumptions move the results the right way. Twice the sessions doubles each trip cost, no caching means A3 saves nothing, and a higher conversion rate lowers cost per booking but not break-even. Impossible values are refused. |
| `CommandLine` | `--set` and `--list` work, and bad input gets a clear error. |
| `DocsMatchCalculator` | The README, the study and the research notes show the calculator's figures, so the code and the text can't drift apart. |
| `Links` | Every relative link in the Markdown files points to a file and a heading that exist. |

When a test fails, the message names the figure and the file it expected to find it in, for example `'**$2.02**' not found in README.md`.

## Prices and assumptions

- **Prices:** Gemini API list prices taken on 30 September 2026 and re-checked on 2 October 2026. Prices change often, so check them before reusing the numbers.
- **One unverified price:** the cost of a direct Google Maps Platform call is an assumption, and it is labelled as one.
- **Everything else** (turns, tokens, conversion, commissions) is a stated assumption, collected in the [assumptions register](tuscany_tokenomics_research.md#appendix-a-assumptions-register).

## Disclaimer

This is an independent, illustrative analysis of a hypothetical app. It isn't financial advice or a price quote. Product names and trademarks belong to their owners.

## Licence

- Text (the Markdown files): [CC BY 4.0](LICENSE-docs.md)
- Code (the calculator and the tests): [MIT](LICENSE)

## Changelog

- **2 October 2026:** first version, with prices re-checked.
