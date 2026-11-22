# StopScalpers — Single-Store Scalping Policy Simulation

A Monte Carlo simulation of one retail store's in-store sales process for
Pokémon TCG collectibles. Tests how operational policies (per-SKU caps,
escalating cooldowns, ticket lotteries, collusion/parasite injection) affect
the allocation of scarce inventory between legitimate consumers and scalper
networks.

**Core thesis (the Naples principle):** The goal is not to eliminate scalpers.
The goal is to make this store a less attractive target than the store next
door. Every mechanism shifts the scalper's marginal profit-per-hour-of-effort
curve downward until it falls below the scalper's opportunity cost, causing
the network to rationally relocate. The consequence: this store's consumers
receive a higher share of inventory.

The mechanism is behavior-proportional, not person-targeted. A collector
wanting 3 items never encounters the friction. A scalper wanting 100 items
re-enters the queue 34 times and drowns in cooldown. Nobody is labeled.
Nobody is judged. The duck walks, and the walk costs time proportional to
how many people you displace.

---

## Quick Start

    pip install numpy matplotlib pyyaml pytest
    python run_grid.py          # all 9 scenarios × 30 seeds, prints table
    python main.py config/scenarios/S2_timeout.yaml   # single scenario
    pytest -q                   # unit + integration tests

---

## The 9-Cell Grid

Two axes: **ticket mode** (how agents enter the queue) × **limit mode**
(how much they can buy per turn). Each cell is a scenario file in
`config/scenarios/`.

|  | No limit | Per-SKU cap + cooldown | Dollar cap ($270) |
|---|---|---|---|
| **No ticketing (FIFO)** | S1: true baseline | S2: timeout only | S3: cap only |
| **No ticketing + collusion** | S4: parasite baseline | S5: timeout vs collusion | S6: cap vs collusion |
| **Random lottery ticketing** | S7: lottery only | S8: recommended policy | S9: lottery + cap |

**S1** is the honest baseline: nothing. A scalper who camps at 1am walks in
at 9:05 and buys 100 ETBs before anyone else touches a register.

**S8** is the recommended policy: per-SKU cap of 3 with escalating cooldown
(10, 20, 30… min between turns) + random lottery ticketing. This is the
Pareto knee.

---

## Mechanisms (toggleable via config)

### Per-SKU Cap + Escalating Cooldown ("the timeout")
- Max 3 units of any SKU per turn (×2 for 2-person parties).
- Between turns, the agent must wait: 10 min after turn 1, 20 min after
  turn 2, 30 min after turn 3, etc.
- During cooldown the agent is NOT at the register. The line keeps moving.
- The agent keeps its queue position; a timer gates when it can be served.
- A consumer wanting ≤3 of a SKU never re-enters. Friction = zero.
- A scalper wanting 100 of a SKU re-enters ~34 times. Friction = days.
- This is the duck rule: the behavior pattern triggers the cost, not the label.

### Dollar Cap ($X per turn)
- Caps total spend per turn across all SKUs. ×2 for 2-person parties.
- Structurally slack when a per-SKU cap is also active (they overlap).
- Useful only as a fallback when no per-SKU cap exists.

### Ticket / Queue Discipline
- `arrival`: pure FIFO. No ticket event. First come, first served.
- `random_time`: a single ticket-distribution event at a random time.
  Only agents present at that moment get queue positions.
- `waves`: 2–4 ticket events at random times.
- `sequential`: within an event, positions follow arrival order.
- `random`: within an event, positions are a random permutation.

### Collusion / Parasite Injection
- `collusion_enabled: true` groups scalper recruits by arrival proximity.
- Each group member gets the earliest member's queue position.
- Models "join their friend who's been camping all night."
- Consumers are unaffected. Only scalper recruits are regrouped.

### Parent-Child 2× Authority
- A party with a child gets 2× the per-SKU cap and 2× the dollar cap.
- The child's patience (60–120 min) is the natural enforcement.
- The store never verifies the relationship. Two IDs = 2× authority.
- A scalper cannot exploit this because no real scalper brings a child
  into a store for 5 hours.

---

## Key Findings (from the 9-cell grid, 30 seeds each)

1. **The timeout is the mechanism that works.** Per-SKU cap of 3 + escalating
   cooldown cuts scalper share ~30% with near-zero consumer cost.
2. **The dollar cap is structurally slack** when a per-SKU cap is active.
   They overlap. The cap alone hurts consumers (forces re-entries) without
   limiting scalper extraction.
3. **Tickets change position, not quantity.** Lottery ticketing alone does
   nothing to scalper share. It is a multiplier on the timeout, not a
   standalone mechanism.
4. **The timeout survives collusion.** S5 ≈ S2: teleporting scalpers to the
   front doesn't defeat the cooldown, because the cooldown is per-turn and
   position-independent.
5. **The lottery restores what collusion took away** when combined with the
   timeout. S8 beats S5 because the random shuffle disrupts coordination.
6. **S1 (true baseline) is much worse than previously measured.** The earlier
   "no_mechanism" was actually "sequential FIFO + no cap," which already had
   some structure. The true baseline (no ticketing, no limits, no cooldown)
   shows scalpers extracting 3× more.

---

## Known Limitations

- **Coordinated networks.** The mechanism does not detect or prevent N
  distinct people with N distinct IDs each buying their vector. The network's
  ceiling is bounded by its own coordination cost, not by store enforcement.
- **The couple loophole.** Two IDs at one register = 2× authority. A couple
  buying 6 items is indistinguishable from a scalper couple. Not modeled.
  The mechanism is calibrated against the 100-unit pathological case.
- **Single store, single period.** No multi-store competition or multi-period
  policy learning. The alternative store is a scalar parameter (22 u/hr).
- **No online channel.** Bots, API scalping, online ticketing are out of scope.
- **No employee judgment.** The store does not ask "are you with the
  scalpers?" Enforcement is purely mechanical: IDs, spend, turns, cooldown.
- **Calibration.** Demand tables, markup distributions, velocity parameters,
  and arrival distributions are placeholders. Real data from line
  observations and scalper Discord posts would tighten these.
- **Patience-as-ROI is parked.** Consumer patience is currently a flat draw.
  It should vary with arrival time and remaining inventory at arrival.
  Needs a shadow-inventory pass. Not yet wired.

---

## File Structure

    config/
      base.yaml                    # all defaults; edit here for global changes
      scenarios/
        S1_no_limit.yaml           # true baseline: nothing
        S2_timeout.yaml            # per-SKU cap + cooldown, FIFO
        S3_cap.yaml                # dollar cap only, FIFO
        S4_collusion_no_limit.yaml # parasite baseline
        S5_collusion_timeout.yaml  # timeout vs collusion
        S6_collusion_cap.yaml      # cap vs collusion
        S7_lottery_no_limit.yaml   # lottery only (no limits)
        S8_lottery_timeout.yaml    # RECOMMENDED: lottery + timeout
        S9_lottery_cap.yaml        # lottery + cap
    src/
      __init__.py
      types.py                     # Agent, Sku, TurnConstraint dataclasses
      config.py                    # YAML loader, DEFAULTS, validation
      distributions.py             # arrival, demand, markup, patience sampling
      waitlist.py                  # persistent position-ordered queue with
                                   #   per-agent serve timer (gate model)
      mechanisms.py                # cap, timeout, qty limits, 2× authority,
                                   #   cooldown — each is a constraint function
      scalper_behavior.py          # BehaviorA (margin-calculating solo),
                                   #   BehaviorB/C stubs, categorical draw
      scalper_network.py           # acquisition rate curve, displacement
      secondary_market.py          # post-store scalper→consumer matching
      simulation.py                # main loop, run_one, collusion regroup
      metrics.py                   # fulfillment, friction, extraction
      frontier.py                  # Pareto construction
      sweep.py                     # parameter grid runner
      viz.py                       # headless PNG plots
    tests/
      test_waitlist.py             # FIFO, re-entry, empty queue, gate
      test_mechanisms.py           # cap, timeout, 2× authority in isolation
      test_integration.py          # end-to-end: thesis holds across seeds
    run_grid.py                    # runs all 9 scenarios, prints table
    main.py                        # single-scenario entry point
    README.md

---

## How to Add a New Mechanism

1. Add a constraint function in `src/mechanisms.py`. It takes
   `(agent, sku, turn_state, config)` and returns a `TurnConstraint`
   (max_qty, additional_wait_min).
2. Add a config toggle in `base.yaml` (e.g. `my_mechanism_enabled: false`).
3. Call it from the turn loop in `simulation.py`. The loop intersects all
   enabled constraints. No structural changes needed.
4. Add a scenario file that enables it.
5. Add a test in `tests/test_mechanisms.py`.

The simulation loop is mechanism-agnostic. Toggling a mechanism is setting
a flag. This is the design constraint from the spec.

---

## How to Calibrate

The placeholder distributions (arrival times, desired vectors, markups,
velocity) should be replaced with observed data:

- **Arrival:** time-stamp line positions at 1am, 3am, 5am, 7am, 8am, 9am
  at a real release. Fit a mixture distribution (hardcore cluster + general
  cluster).
- **Desired vectors:** count basket sizes at the front and back of the line.
- **Markups / velocity:** scrape eBay/Mercari time-to-sale and realized
  markup per SKU from the scalper Discord.
- **Sell-through ceilings:** ask scalpers in the Discord how many they
  typically move before $/hr collapses.

Replace the placeholder tables in `src/distributions.py` and the
`scalper_sell_through` / `sku_velocity_hours` blocks in `base.yaml`.

---

## What's Next

1. **Behavior B** — the co-op/Costco credit pool where recruits share
   inventory and a coordinator absorbs friction. Designed to challenge
   the timeout.
2. **Behavior C** — opportunistic/impulse decoy. Easy. Keeps the model
   honest.
3. **Behavior mix sweep** — vary the A/B/C weights and see how robust the
   timeout is to the network adapting its composition.
4. **Patience-as-ROI** — wire consumer patience to remaining inventory at
   arrival. One shadow-inventory pass.
5. **Wave ticketing** — the 7th ticket mode. Valid design (no consumer
   friction; only scalpers pay the "hold tickets across waves" cost).
   Parked until the 9-cell grid is validated.