CREATE TABLE IF NOT EXISTS metrics_alert (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES project(id),
    metric_key TEXT NOT NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('threshold', 'anomaly')),
    severity TEXT NOT NULL CHECK (severity IN ('warning', 'critical', 'emergency')),
    value DOUBLE PRECISION NOT NULL,
    threshold DOUBLE PRECISION,
    context JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_metrics_alert_project ON metrics_alert(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_alert_severity ON metrics_alert(project_id, severity, acknowledged_at);
