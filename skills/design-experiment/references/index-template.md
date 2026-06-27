# docs/design/ index template

Copy the block below to `docs/design/index.md` in a DerivaML project. It is the
OKF bundle root — a directory listing of the design corpus. Add a line per
design doc as they are authored.

## Template (copy below this line)

---
type: Index
title: DerivaML design documents
description: >
  Up-front design specifications for this project's experiments, datasets,
  features, and models.
---

# Design documents

These design documents follow the
[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
— Markdown + YAML frontmatter. Each `<entity>/<slug>.md` is an OKF concept
document with a `type` of `Dataset Design`, `Experiment Design`,
`Feature Design`, or `Model Design`. These are abstract specifications (intent),
so they carry no OKF `resource` field; the produced catalog entities and their
RIDs live in `tacit-knowledge.md` and each doc's "Status & links" section.

## experiment/
<!-- - [<slug>](/experiment/<slug>.md) — <one-line description> (Status: <status>) -->

## dataset/
<!-- - [<slug>](/dataset/<slug>.md) — <one-line description> (Status: <status>) -->

## feature/
<!-- - [<slug>](/feature/<slug>.md) — <one-line description> (Status: <status>) -->

## model/
<!-- - [<slug>](/model/<slug>.md) — <one-line description> (Status: <status>) -->
