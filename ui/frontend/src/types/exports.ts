// Exports types · Stage 6 ExportPack MVP.
// Mirrors `ui/backend/services/export_csv.py` manifest shape.

export interface ExportManifest {
  schema_version: string;
  n_columns: number;
  n_batch_rows: number;
  columns: string[];
  exported_at_utc: string;
  exporter: string;
}
