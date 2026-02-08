CREATE INDEX IF NOT EXISTS idx_event_log_metrics_cursor
  ON event_log(project_id, entity_type, event_type, id);
