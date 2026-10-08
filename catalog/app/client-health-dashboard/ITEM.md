# client-health-dashboard (app)

**Status:** spec · **Version:** 0.1.0 · **Who it's for:** an owner who wants one green, amber or red signal per client and an alert only when one turns red.

## Purpose
**Specification only: there is no code.** A collector reads configured sources, scores each client green, amber or red, writes the score to columns on a Notion client board (v1) or a static page behind an auth proxy (v2), and alerts on red only. The thresholds are config and are not set yet.

## Depends on
Nothing in this catalog. The wiring to real systems (which product data, which board, which brain) belongs in a private catalog item that depends on this one.

## Config
None until it is built. The design lists what will be configurable: sources, thresholds, alert channel.

## Install
Status **spec**: `catalog.py install client-health-dashboard --docs` copies `DESIGN.md` into your personal brain to discuss or extend. Do not build, deploy or set thresholds without the owner.

## Files
| Path | Role |
|---|---|
| `DESIGN.md` | The specification |
