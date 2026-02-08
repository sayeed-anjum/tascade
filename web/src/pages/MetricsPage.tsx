// ---------------------------------------------------------------------------
// MetricsPage -- project metrics dashboard page.
// Gets projectId from URL params and renders the MetricsDashboard organism
// with loading / error / empty states.
// ---------------------------------------------------------------------------

import { useParams } from 'react-router-dom';

import MetricsDashboard from '@/components/organisms/MetricsDashboard';

export default function MetricsPage() {
  const { projectId } = useParams<{ projectId: string }>();

  if (!projectId) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">
          No project selected. Please select a project to view metrics.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold tracking-tight">Metrics</h1>
      <MetricsDashboard projectId={projectId} />
    </div>
  );
}
