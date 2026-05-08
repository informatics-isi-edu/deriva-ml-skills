---
name: generate-descriptions
description: "ALWAYS use when creating any DerivaML entity (Dataset, Workflow, Execution, Feature, Asset, Experiment, multirun) and the user hasn't provided a description. Auto-generate a meaningful description from context. For generic Deriva catalog entities (tables, columns, vocabularies, vocabulary terms), use the generate-descriptions skill in deriva-skills."
user-invocable: false
---

# Generate Descriptions for DerivaML Entities

Every DerivaML entity that accepts a description should have a meaningful one. If the user doesn't provide a description when creating one, generate a draft based on context from the repository, conversation, hydra-zen configs, and existing catalog state, then confirm with the user before creating the entity. Descriptions support GitHub-flavored Markdown which renders in the Chaise web UI.

## Scope

This skill covers descriptions for the **DerivaML domain entities** — the abstractions the deriva-ml plugin layers on top of plain Deriva catalogs:

- **Datasets** (`deriva_ml_create_dataset` -- description parameter)
- **Workflows** (`deriva_ml_create_workflow` -- description parameter)
- **Executions** (`deriva_ml_create_execution` -- description parameter)
- **Features** (`deriva_ml_create_feature` -- description parameter)
- **Assets** (`exe.asset_file_path()` -- description parameter; built-in execution metadata files like Hydra configs and `configuration.json` get automatic descriptions)
- **Experiments** (description parameter on the experiment config)
- **Multiruns / sweeps** (description parameter on the multirun config)

For generic catalog entities — tables, columns, vocabularies, vocabulary terms — use `/deriva:generate-descriptions` *(deriva-skills, also auto-fires)*. The two skills cover non-overlapping entity sets and share the same generic workflow and quality bar.

## Workflow

1. Check if the user provided a description.
2. If not, gather context from all available sources:
   - The user's request and stated intent
   - Repository structure (README, hydra-zen configs, existing experiment / dataset definitions)
   - The producing or consuming Execution (for Datasets and Assets)
   - Existing entities of the same type (for consistency in tone and depth)
   - Conversation history and decisions made
3. Draft a description using the entity-specific template in `references/templates.md`.
4. Present the draft to the user for confirmation.
5. Create the entity with the approved description.

DerivaML entities are part of the provenance graph; once created they are referenced by RID and become hard to rename or repurpose. Always confirm before creating.

## What a good description answers

- **What** does this entity represent?
- **Why** does it exist (the experimental question, the workflow purpose)?
- **How** is it produced or consumed (which Workflow / Execution / Dataset)?
- **What does it contain** (composition, key characteristics, parameters)?

## Quality checklist

Before finalizing any description, verify it is:

- **Specific** — avoids generic language like "a dataset" or "some data"
- **Informative** — provides enough context for someone unfamiliar with the project
- **Accurate** — correctly reflects the entity's actual contents and purpose
- **Concise** — no unnecessary words, but complete enough to be useful
- **Consistent** — matches the tone and style of existing descriptions in the catalog
- **Actionable** — helps users understand how to use the entity

## Templates

Per-entity templates and worked examples (Dataset, Workflow, Execution, Feature, Asset, Experiment, multirun) plus the markdown formatting affordance live in `references/templates.md`. Read it when drafting a description for a specific entity type.

## Autonomous-agent fallback

If you're operating with no human in the loop (an unattended agent script), generate the best draft from available context and add a note in your response so a future audit can see which descriptions were auto-generated without confirmation.
