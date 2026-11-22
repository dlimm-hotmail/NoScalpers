# StopScalpers — single-store scalping policy simulation

Model of a Pokémon TCG release at one store, testing how waitlist discipline,
per-turn spend caps, progressive purchase timeouts, and ID-linked authority
shift the scalper's acquisition rate below the store next door (the Naples
principle).

## Run one scenario
    python main.py config/scenarios/no_mechanism.yaml
    python main.py config/scenarios/full_stack.yaml

## Run the parameter sweep + plots
    python main.py sweep

## Tests
    pytest -q