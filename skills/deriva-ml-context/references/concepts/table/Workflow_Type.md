---
type: Table
title: Workflow_Type
kind: vocabulary
description: Controlled vocabulary classifying workflows by their role in an ML pipeline.
---

# Workflow_Type

Controlled vocabulary classifying workflows by their **role in an ML pipeline**.
Tags are assigned to workflows via the
[Workflow_Workflow_Type](Workflow_Workflow_Type.md) association table — a
workflow can carry multiple types simultaneously (for example `Training` +
`Feature_Creation`).

## Foreign Keys

This is a vocabulary table. It has no outbound foreign keys to other
deriva-ml tables.

## Seeded terms

Nine terms are seeded at schema initialization:

| Name | Description |
|------|-------------|
| `Training` | Model training and fine-tuning workflows. |
| `Testing` | Workflows that evaluate model performance on held-out data, computing metrics such as accuracy, AUC, confusion matrices, and per-class statistics. |
| `Prediction` | Workflows that apply a trained model to new data to generate predictions, probability scores, or classification labels. |
| `Feature_Creation` | Workflows that extract or engineer features from raw data, producing structured feature values linked to source records. |
| `Visualization` | Workflows that produce visual analyses of data or model results, including plots, charts, and summary dashboards. |
| `Analysis` | Computational analysis workflows that combine and analyze data from multiple sources without training a model. |
| `Ingest` | Workflows that load external data into the catalog, including file upload, record creation, and initial metadata population. |
| `Data_Cleaning` | Workflows that clean and preprocess raw data, including standardizing formats, handling missing values, and filtering invalid records. |
| `Dataset_Management` | Workflows that create, split, version, or manage datasets. |

Domain-specific workflow categories belong in user vocabularies, not here.
