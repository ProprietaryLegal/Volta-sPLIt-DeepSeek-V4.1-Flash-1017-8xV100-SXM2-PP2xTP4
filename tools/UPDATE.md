# Updating this repository

How the numbers on this page are refreshed when a queued test finishes or a new lever is adopted.

## Sources, in order of authority

1. The queue's state log (`pp2-go.state` in the bench directory; a sanitized copy is `evidence/queue-log.txt`). Each test
   writes `QUEUE-Dnn ... pairs:` and `... verdict:` lines with the ABBA means, pair signs, text identity and greedy
   result, and `... done` when it has restored production.
2. The `ab-*.out` files of each arm (ms/round and tok/s per prompt).
3. The lever-results notes kept with the build.

A number goes onto the page only from (1) or (2), with its date, labelled MEASURED; or as arithmetic on them, labelled
ESTIMATED with the arithmetic stated.

## What to change for a finished test

1. `docs/roadmap.md`: the test's row (status → result, or move it to `docs/levers.md`).
2. `docs/levers.md`: under Adopted (switch, source, ABBA means, numerics gate) or Did not work (result and why).
3. README:
   - the hero row and badges, if the production tok/s changes. The hero T=0 and T=1 figures are 1000 x (1 + accepted
     drafts per round) / ms per round on the A/B harness; when a lever is adopted, subtract its ABBA mean from the last
     MEASURED stack and label the result ESTIMATED until a full-stack run measures it;
   - the tok/s progression and ms/round tables (one row per adopted step);
   - What worked / What did not work / In testing tables.
4. `engine/configs/rec.env` and `docs/production.md` for a newly adopted switch; move its patch from `engine/in-testing/`
   to `engine/production/` (check that it applies on the production tree with `git apply --check`).
5. `evidence/queue-log.txt`: re-copy the state log through our path and host-name scrubber (not published: it lists the
   names it removes).
6. `CHANGELOG.md`: one entry per update.
7. Mirror the headline numbers to the Hugging Face card, the DGX sPLIce sister section and the organization profile.

## Before every push

```bash
# scrub every copied file of paths and host names first (our scrubber is not published)
tools/check_data_boundary.sh --staged      # then --tree HEAD after committing
```

and a scan for host names, internal paths and personal addresses. Commit as `PLI Labs`.

## Scheduled updates

- About five hours after first publication: the D35-D39 results (prefill skip, TP8 probe, prefill switches, hot ring,
  harness v2).
- After the queue's last item: every remaining result, then the head-to-head benchmark against DGX sPLIce (same tools,
  same day, per-text-type decode, and a legal benchmark if one can run on both).
