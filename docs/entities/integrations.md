# Integrations

Data import/export, automation, and external connectivity.

Labels: [`data/entity-labels.json`](../data/entity-labels.json) · Hints: [`data/table-hints.json`](../data/table-hints.json)

## Export

**Tables:** `Export`, `ExportLine`, `ExportCondition`, `ExportCalculation`

Defines data export from requests (CSV, XML, SQL, Excel).

Key fields (from hints):

- `ExportName` — export definition name
- `ExportTypeID` — CSV/XML/SQL/Excel format
- `ExportDeliveryID` — Download or Email
- `ExportLineTypeID` — object line, fixed value, request metadata, etc.

Often triggered from workflow steps via `WorkflowStepExport`.

## Import

**Tables:** `Import`, `ImportSection`, `ImportSectionLine`

Inbound data pipelines into objects.

## Periodic

**Tables:** `Periodic`, `PeriodicAction`, `PeriodicCondition`, `PeriodicCalculation`

Scheduled automation on an object (conditions + actions).

## Scheduler

**Tables:** `Scheduler`, `SchedulerLine`, `SchedulerLineParam`

CRON-based job definitions.

## Object Service & Webhook

**Tables:** `ObjectService`, `ObjectWebhook`

External HTTP/service integrations callable from workflow or templates.

## DB transfer

All listed parent tables are type **U** or **D** in [`data/transfer-tables.json`](../data/transfer-tables.json).

Not covered by minimal `create_object` spec — extend spec format in future phases.
