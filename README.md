# Prophet Core Catalog

Prophet Core Catalog is the canonical catalog spine for SocioProphet data products, source registries, dataset workspaces, app integrations, lineage receipts, and end-user task workflows.

The catalog is intentionally not just a metadata index. It is the low-barrier task layer between raw sources, governed datasets, notebooks, apps, agents, visualizations, and downstream product APIs.

## Design posture

The catalog starts from the DataHub lesson: end users do not primarily care about storage models, query engines, or data schemas. They care about completing tasks: ingesting data, cleaning it, joining it, understanding it, visualizing it, sharing it, and turning it into decisions.

The catalog therefore tracks both data assets and the task-oriented apps that can operate on them.

## Core objects

- Source: external, open, licensed, client-owned, or internal feed.
- Dataset: versioned data asset created from one or more sources.
- Collection: workspace-visible grouping of datasets, notebooks, apps, and receipts.
- Catalog app: task processor for ingest, curation, integration, analytics, visualization, machine learning, entity resolution, or report generation.
- Receipt: auditable evidence of source access, transform, validation, policy decision, publication, or downstream export.
- Product package: governed bundle exposed to SocioProphet product surfaces.

## Operating principles

- Task-first UX before schema-first UX.
- Search and navigation are first-class.
- Collaboration, sharing, access control, and versioning are native.
- Every generated asset has provenance, policy metadata, and validation receipts.
- Expert tools remain available through notebooks, SQL, Python, R, Julia, agents, APIs, and workflow runners.
- Non-technical users should be able to discover the right app for the task without knowing the storage backend.

## Initial scope

The first implementation slice defines catalog contracts, source manifests, app manifests, and receipt hooks. Runtime execution belongs in Prophet Core Ingest, Prophet Core Query, AgentPlane, SocioSphere, Sherlock, Holmes, SynapseIQ, and the notebook/workroom surfaces.
