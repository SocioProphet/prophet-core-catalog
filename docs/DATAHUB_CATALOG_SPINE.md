# DataHub-Inspired Catalog Spine v0.1

## Thesis

The catalog is the task-first control plane for SocioProphet data work. It exists because raw data lakes, warehouses, notebooks, APIs, and query engines do not solve the end-user problem by themselves.

The key design lesson is simple: users do not primarily care about data models. They care about tasks. They need to ingest, clean, join, summarize, visualize, govern, share, and publish data without first understanding every backend, schema, or distributed-system detail.

## What this catalog is

Prophet Core Catalog is a governed registry for:

- sources and source-access contracts;
- datasets and dataset versions;
- collections and workspaces;
- task-oriented catalog apps;
- lineage and validation receipts;
- policy, license, privacy, and access metadata;
- product packages exposed through SocioProphet surfaces.

It is not a clone of any upstream DataHub project. It is our SocioProphet catalog spine, designed to connect open data, licensed data, client-owned data, notebooks, agents, apps, and product APIs.

## User classes

The catalog must serve four user classes without forcing one class into another class's toolchain.

1. Programmers need APIs, SDKs, stable identifiers, schemas, and integration contracts.
2. Data scientists need notebooks, transforms, model features, experiments, and reproducible datasets.
3. Business owners need numbers, charts, decision views, narratives, and shareable reports.
4. Data administrators need privacy, access control, retention, audit, compliance, and policy enforcement.

A fifth reference class, journalists and civic analysts, is useful as a UX stress test: they need to import public files, join across sources, understand messy data quickly, and produce visual explanations without becoming database engineers.

## Core architecture

The catalog has seven planes.

1. Source Registry: records source identity, license, auth mode, access method, rate limits, source URLs, freshness cadence, policy class, and provenance strength.
2. Dataset Registry: records normalized datasets, schema versions, snapshots, partitions, quality checks, and lineage.
3. Collection Registry: groups datasets, notebooks, apps, visualizations, receipts, and user/team permissions.
4. App Registry: records task processors for ingest, ETL, curation, integration, analytics, visualization, entity resolution, machine learning, and publication.
5. Receipt Registry: records evidence for source access, transforms, validation, policy decisions, publication, and export.
6. Product Package Registry: records governed bundles that can become external or internal products.
7. Search and Navigation Surface: lets users find data by task, entity, topic, location, time range, license, policy class, and product eligibility.

## Ownership boundaries

Prophet Core Catalog owns the contracts and registry semantics.

Execution belongs elsewhere:

- Prophet Core Ingest executes source ingestion and normalization.
- Prophet Core Query exposes query/search APIs.
- Prophet Core Ledger stores durable receipts.
- Policy Fabric and Guardrail Fabric decide policy admission.
- AgentPlane runs governed agent tasks.
- Sherlock, Holmes, and SynapseIQ expose discovery and reasoning surfaces.
- SocioSphere coordinates workspace and service-register awareness.

## Initial MVP

The first slice is deliberately small:

- JSON schemas for source, dataset, catalog app, receipt, and product package manifests.
- Example manifests for open-data source ingestion and task apps.
- A stdlib-only validator for checked-in manifest examples.
- A CI workflow that validates catalog contracts.
- Documentation that prevents the catalog from collapsing into a generic metadata list.

## Non-goals

The catalog does not initially implement a full storage engine, query engine, notebook server, app runtime, or data marketplace. Those belong to adjacent repos and services. The catalog defines the auditable coordination layer that makes those systems discoverable, governed, and composable.
