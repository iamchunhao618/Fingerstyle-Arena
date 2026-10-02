# Sonnet 5.5 run of the guitar-arrangement eval (task v0.2.2)

Batch: Claude Code `claude-sonnet-5-5`, effort `high`, concurrency 2, 3600 s per song,
Linux cloud container, TuxGuitar 1.6.6 Java libs, JDK 21. **Not** the Opus 5.5 batch the
bundle was written for; do not compare it as if it were.

Input audio: user-supplied WAVs. Format, 48 kHz stereo 16-bit and duration match
`audio-sources.json`, but the decoded-PCM SHA-256 differs from the historical value for all
seven, so the batch was run with `--allow-audio-variant` (see `opus55-eval/audio-check.json`).
It is a variant-input run, not identical-input.

| task | status | elapsed (s) | tracks | measures | notes | parseable_score | sole GP output |
|---|---|---:|---:|---:|---:|---:|---|
| 02-fix-you | process_failed | 222 | - | - | - | 0 | no (empty output) |
| 03-payphone | process_failed | 300 | - | - | - | 0 | no (empty output) |
| 04-zenzenzense | process_completed | 2557 | 1 | 182 | 1962 | 1 | yes |
| 06-christmas-eve | process_completed | 1133 | 1 | 88 | 1117 | 1 | yes |
| 08-smooth-criminal | process_failed | 1067 | - | - | - | 0 | no (empty output) |
| 09-chocolate-disco | process_completed | 1573 | 3 | 121 | 7269 | 1 | yes |
| 10-koi | process_completed | 1698 | 3 | 140 | 4160 | 1 | yes |

The three failures all ended with `API Error: Output blocked by content filtering policy`
reported by the agent's own session; none left an `arrangement.gp`. They were not retried.

`parseable_score = 1` only means the fixed TuxGuitar parser read a non-empty score. It says
nothing about musical quality, instrumentation compliance or playability; no quality
judging has been done.

Files: `sonnet55-results.zip` is the `run.py export` bundle (settings, event logs, verifier
reports, GP files; no audio or software). The four `*/arrangement.gp` files are copies of the
delivered scores.

## Retry batch (02, 03, 08)

Requested by the operator after the first batch. Same settings as above (Claude Code
`claude-sonnet-5-5`, `high`, 3600 s, `--allow-audio-variant`), run as a separate batch
(`batch-20261002T174121Z-d4870e71`); the first batch's results are unchanged and nothing was
selected between attempts.

| task | batch 1 | retry | retry elapsed (s) | output |
|---|---|---|---:|---|
| 02-fix-you | failed | process_failed | 321 | none |
| 03-payphone | failed | process_failed | 764 | none |
| 08-smooth-criminal | failed | process_failed | 553 | none |

All three retries ended with the same `API Error: Output blocked by content filtering policy`
and delivered no `arrangement.gp` (`parseable_score = 0`, `missing_or_ambiguous_submission`).
So these three songs failed 2/2 with an identical error. The last tool calls before each block
were ordinary audio-analysis scripts (librosa / pyin / pretty_midi); the logs do not show what
triggered the filter. Bundle: `retry/sonnet55-retry-results.zip`.

Overall for this Sonnet 5.5 run: 4 of 7 songs delivered a parseable score (04, 06, 09, 10).
