# Opus 5.5 run of the guitar-arrangement eval (task v0.2.2) — incomplete

Batch `batch-20261002T180426Z-dc756bdf`: Claude Code `claude-opus-5-5`, effort `high`,
concurrency 2, 3600 s per song, Linux cloud container, TuxGuitar 1.6.6 Java libs, JDK 21,
fresh sessions, run dir separate from the Sonnet runs. Variant-input audio (same WAVs and
`--allow-audio-variant` as the Sonnet runs). No event log in this batch references the Sonnet
outputs or another batch.

**The container restarted at about 20:09 UTC and killed the batch** while 09 and 10 were
running. `batch.json` still says `running` (stale); `run.py status` reports it as
interrupted. `run.py export` refuses a batch in that state, so there is no export zip yet and
the batch record was not edited.

| task | status | time | output |
|---|---|---|---|
| 02-fix-you | process_failed — `API Error: Output blocked by content filtering policy` | 25 min | none |
| 03-payphone | process_failed — same content-filter error | 26 min | none |
| 04-zenzenzense | timed_out at 60 min; file already written, sole output, parseable | 60 min | `04-zenzenzense/arrangement.gp` |
| 06-christmas-eve | process_completed, sole output, parseable | 58 min | `06-christmas-eve/arrangement.gp` |
| 08-smooth-criminal | process_completed, sole output, parseable | 27 min | `08-smooth-criminal/arrangement.gp` |
| 09-chocolate-disco | killed by restart about 40 min in | ~40 min | `09-chocolate-disco/arrangement.INTERRUPTED.gp` — mid-run file, not a submission (parses: 3 tracks, 119 bars) |
| 10-koi | killed by restart about 14 min in | ~14 min | none |

`parseable` only means the fixed TuxGuitar parser read a non-empty score; no quality judging.

Also in `/home/user/opus-runs/`: `batch-20261002T180426Z-957fc68d`, an accidental duplicate
launch that was interrupted after about 1 minute (02 and 03 only). It is not a result.
