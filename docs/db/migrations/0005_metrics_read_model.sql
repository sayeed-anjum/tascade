-- Metrics read-model schema (P5.M2.T1)

CREATE TYPE metrics_time_grain AS ENUM ('hour', 'day', 'week', 'month');

CREATE TABLE metrics_summary (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  captured_at TIMESTAMPTZ NOT NULL,
  version TEXT NOT NULL DEFAULT '1.0',
  scope JSONB NOT NULL DEFAULT '{}'::jsonb,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_metrics_summary_project_captured
  ON metrics_summary(project_id, captured_at DESC);

CREATE TABLE metrics_trend_point (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  metric_key TEXT NOT NULL,
  time_grain metrics_time_grain NOT NULL,
  time_bucket TIMESTAMPTZ NOT NULL,
  dimensions JSONB NOT NULL DEFAULT '{}'::jsonb,
  value_numeric DOUBLE PRECISION NULL,
  value_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_metrics_trend_project_metric_time
  ON metrics_trend_point(project_id, metric_key, time_grain, time_bucket DESC);
CREATE INDEX idx_metrics_trend_dimensions_gin
  ON metrics_trend_point USING GIN (dimensions);

CREATE TABLE metrics_breakdown_point (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  metric_key TEXT NOT NULL,
  time_grain metrics_time_grain NULL,
  time_bucket TIMESTAMPTZ NULL,
  dimension_key TEXT NOT NULL,
  dimension_value TEXT NOT NULL,
  value_numeric DOUBLE PRECISION NULL,
  value_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_metrics_breakdown_project_metric_time
  ON metrics_breakdown_point(project_id, metric_key, time_grain, time_bucket DESC);
CREATE INDEX idx_metrics_breakdown_dimension
  ON metrics_breakdown_point(project_id, dimension_key, dimension_value);

CREATE TABLE metrics_drilldown (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  metric_key TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID NULL,
  reference_id TEXT NULL,
  time_bucket TIMESTAMPTZ NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_metrics_drilldown_project_metric_entity
  ON metrics_drilldown(project_id, metric_key, entity_type, entity_id);
CREATE INDEX idx_metrics_drilldown_reference
  ON metrics_drilldown(project_id, metric_key, reference_id);
