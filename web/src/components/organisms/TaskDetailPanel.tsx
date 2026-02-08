import { useMemo } from "react";

import {
  useGateDecisions,
  useProjectGraph,
  useTask,
  useTaskArtifacts,
} from "@/api/hooks";
import type { Artifact, DependencyEdge, GateDecision, GraphTask } from "@/api/types";
import DependencyLink from "@/components/molecules/DependencyLink";
import ErrorMessage from "@/components/molecules/ErrorMessage";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { stateColorClass } from "@/lib/state-colors";

// ---------------------------------------------------------------------------
// TaskDetailPanel -- slide-in drawer showing full task context.
// ---------------------------------------------------------------------------

interface TaskDetailPanelProps {
  taskId: string | null;
  projectId: string;
  open: boolean;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Check status badge variants.
// ---------------------------------------------------------------------------

const CHECK_STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  passed: "default",
  pending: "secondary",
  failed: "destructive",
};

// ---------------------------------------------------------------------------
// Outcome / verdict badge variants.
// ---------------------------------------------------------------------------

const OUTCOME_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  approved: "default",
  rejected: "destructive",
  approved_with_risk: "secondary",
};

// ---------------------------------------------------------------------------
// Collapsible section using native <details>/<summary>.
// ---------------------------------------------------------------------------

interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  count?: number;
  children: React.ReactNode;
}

function CollapsibleSection({
  title,
  defaultOpen = false,
  count,
  children,
}: CollapsibleSectionProps) {
  return (
    <details open={defaultOpen || undefined} className="border-b last:border-b-0">
      <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold hover:bg-muted/50">
        {title}
        {count != null && count > 0 && (
          <span className="ml-2 text-xs text-muted-foreground">({count})</span>
        )}
      </summary>
      <div className="px-4 pb-4">{children}</div>
    </details>
  );
}

// ---------------------------------------------------------------------------
// Dependency resolution helpers.
// ---------------------------------------------------------------------------

interface ResolvedDependency {
  taskId: string;
  shortId: string;
  title: string;
}

function resolveBlockedBy(
  taskId: string,
  dependencies: DependencyEdge[],
  taskMap: Map<string, GraphTask>,
): ResolvedDependency[] {
  return dependencies
    .filter((d) => d.to_task_id === taskId)
    .map((d) => {
      const t = taskMap.get(d.from_task_id);
      return {
        taskId: d.from_task_id,
        shortId: t?.short_id ?? d.from_task_id.slice(0, 8),
        title: t?.title ?? "Unknown task",
      };
    });
}

function resolveBlocks(
  taskId: string,
  dependencies: DependencyEdge[],
  taskMap: Map<string, GraphTask>,
): ResolvedDependency[] {
  return dependencies
    .filter((d) => d.from_task_id === taskId)
    .map((d) => {
      const t = taskMap.get(d.to_task_id);
      return {
        taskId: d.to_task_id,
        shortId: t?.short_id ?? d.to_task_id.slice(0, 8),
        title: t?.title ?? "Unknown task",
      };
    });
}

// ---------------------------------------------------------------------------
// Sub-sections rendered inside the panel.
// ---------------------------------------------------------------------------

function WorkSpecSection({ objective, acceptanceCriteria }: {
  objective: string;
  acceptanceCriteria: string[];
}) {
  return (
    <CollapsibleSection title="Work Spec" defaultOpen>
      {objective && (
        <p className="text-sm text-foreground mb-3">{objective}</p>
      )}
      {acceptanceCriteria.length > 0 ? (
        <ul className="list-disc pl-5 space-y-1">
          {acceptanceCriteria.map((ac, i) => (
            <li key={i} className="text-sm text-muted-foreground">{ac}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No acceptance criteria defined.</p>
      )}
    </CollapsibleSection>
  );
}

function DependenciesSection({ blockedBy, blocks, projectId }: {
  blockedBy: ResolvedDependency[];
  blocks: ResolvedDependency[];
  projectId: string;
}) {
  const hasAny = blockedBy.length > 0 || blocks.length > 0;

  if (!hasAny) return null;

  return (
    <CollapsibleSection
      title="Dependencies"
      defaultOpen
      count={blockedBy.length + blocks.length}
    >
      {blockedBy.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
            Blocked by
          </p>
          <ul className="space-y-1">
            {blockedBy.map((dep) => (
              <li key={dep.taskId} className="flex items-center gap-2 text-sm">
                <DependencyLink
                  shortId={dep.shortId}
                  taskId={dep.taskId}
                  projectId={projectId}
                />
                <span className="text-muted-foreground truncate">{dep.title}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {blocks.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
            Blocks
          </p>
          <ul className="space-y-1">
            {blocks.map((dep) => (
              <li key={dep.taskId} className="flex items-center gap-2 text-sm">
                <DependencyLink
                  shortId={dep.shortId}
                  taskId={dep.taskId}
                  projectId={projectId}
                />
                <span className="text-muted-foreground truncate">{dep.title}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </CollapsibleSection>
  );
}

function ArtifactsSection({ artifacts }: { artifacts: Artifact[] }) {
  if (artifacts.length === 0) return null;

  return (
    <CollapsibleSection title="Artifacts" defaultOpen count={artifacts.length}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Branch</TableHead>
            <TableHead>SHA</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Files</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {artifacts.map((a) => (
            <TableRow key={a.id}>
              <TableCell className="font-mono text-xs">
                {a.branch ?? "-"}
              </TableCell>
              <TableCell className="font-mono text-xs">
                {a.commit_sha ? a.commit_sha.slice(0, 7) : "-"}
              </TableCell>
              <TableCell>
                <Badge variant={CHECK_STATUS_VARIANT[a.check_status] ?? "outline"}>
                  {a.check_status}
                </Badge>
              </TableCell>
              <TableCell>
                {a.touched_files.length > 0 ? (
                  <details>
                    <summary className="cursor-pointer text-xs text-muted-foreground">
                      {a.touched_files.length} file{a.touched_files.length !== 1 ? "s" : ""}
                    </summary>
                    <ul className="mt-1 space-y-0.5">
                      {a.touched_files.map((f) => (
                        <li key={f} className="font-mono text-xs text-muted-foreground">
                          {f}
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : (
                  <span className="text-xs text-muted-foreground">-</span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </CollapsibleSection>
  );
}

function IntegrationAttemptsSection({ task }: { task: { id: string } }) {
  // Integration attempts are not yet exposed as a dedicated hook.
  // This section is included for structural completeness and will render
  // once the API hook is available. For now, we show a placeholder.
  void task;
  return (
    <CollapsibleSection title="Integration Attempts">
      <p className="text-sm text-muted-foreground">
        No integration attempts recorded.
      </p>
    </CollapsibleSection>
  );
}

function GateDecisionsSection({ decisions }: { decisions: GateDecision[] }) {
  if (decisions.length === 0) {
    return (
      <CollapsibleSection title="Gate Decisions">
        <p className="text-sm text-muted-foreground">No gate decisions recorded.</p>
      </CollapsibleSection>
    );
  }

  return (
    <CollapsibleSection title="Gate Decisions" count={decisions.length}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Reviewer</TableHead>
            <TableHead>Verdict</TableHead>
            <TableHead>Evidence</TableHead>
            <TableHead>Time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {decisions.map((d) => (
            <TableRow key={d.id}>
              <TableCell className="text-xs">{d.actor_id.slice(0, 8)}</TableCell>
              <TableCell>
                <Badge variant={OUTCOME_VARIANT[d.outcome] ?? "outline"}>
                  {d.outcome.replace("_", " ")}
                </Badge>
              </TableCell>
              <TableCell className="text-xs max-w-[160px] truncate" title={d.reason}>
                {d.reason || "-"}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {new Date(d.created_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </CollapsibleSection>
  );
}

// ---------------------------------------------------------------------------
// Main component.
// ---------------------------------------------------------------------------

export default function TaskDetailPanel({
  taskId,
  projectId,
  open,
  onClose,
}: TaskDetailPanelProps) {
  const { data: task, isLoading: taskLoading, isError: taskError, error: taskErr, refetch: refetchTask } = useTask(taskId ?? undefined);
  const { data: artifactsData } = useTaskArtifacts(taskId ?? undefined);
  const { data: gateData } = useGateDecisions(projectId);
  const { data: graphData } = useProjectGraph(projectId);

  // Build a lookup map of graph tasks for dependency resolution.
  const taskMap = useMemo(() => {
    const map = new Map<string, GraphTask>();
    if (graphData?.tasks) {
      for (const t of graphData.tasks) {
        map.set(t.id, t);
      }
    }
    return map;
  }, [graphData?.tasks]);

  // Resolve dependencies for this task.
  const blockedBy = useMemo(
    () =>
      taskId && graphData?.dependencies
        ? resolveBlockedBy(taskId, graphData.dependencies, taskMap)
        : [],
    [taskId, graphData?.dependencies, taskMap],
  );

  const blocks = useMemo(
    () =>
      taskId && graphData?.dependencies
        ? resolveBlocks(taskId, graphData.dependencies, taskMap)
        : [],
    [taskId, graphData?.dependencies, taskMap],
  );

  // Filter gate decisions to this task.
  const taskGateDecisions = useMemo(
    () =>
      gateData?.items.filter((d) => d.task_id === taskId) ?? [],
    [gateData?.items, taskId],
  );

  const artifacts = artifactsData?.items ?? [];

  return (
    <Sheet open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-[480px] p-0 flex flex-col"
      >
        {taskLoading ? (
          <div role="status" aria-label="Loading task" className="flex flex-col gap-4 p-4">
            <div className="flex items-center gap-2">
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-24 rounded-full" />
              <Skeleton className="h-5 w-10 rounded-full" />
            </div>
            <Skeleton className="h-6 w-3/4" />
            <div className="flex items-center gap-2">
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <Skeleton className="h-px w-full" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : taskError ? (
          <div className="flex items-center justify-center h-full p-6">
            <ErrorMessage
              message={`Failed to load task: ${taskErr instanceof Error ? taskErr.message : "Unknown error"}`}
              onRetry={() => refetchTask()}
            />
          </div>
        ) : !task ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-muted-foreground">Task not found.</p>
          </div>
        ) : (
          <>
            {/* ---- Header ---- */}
            <SheetHeader className="border-b px-4 py-4 pr-10">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono font-bold text-sm">
                  {task.short_id ?? task.id.slice(0, 8)}
                </span>
                <Badge
                  className={stateColorClass(task.state)}
                  variant="outline"
                >
                  {task.state.replace("_", " ")}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  P{task.priority}
                </Badge>
              </div>
              <SheetTitle className="text-base leading-snug">
                {task.title}
              </SheetTitle>
              <SheetDescription className="flex items-center gap-2 flex-wrap">
                <Badge variant="outline" className="text-xs">
                  {task.task_class}
                </Badge>
                {task.capability_tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </SheetDescription>
            </SheetHeader>

            {/* ---- Scrollable content ---- */}
            <ScrollArea className="flex-1 overflow-hidden">
              <div className="divide-y">
                <WorkSpecSection
                  objective={task.work_spec.objective}
                  acceptanceCriteria={task.work_spec.acceptance_criteria}
                />

                <DependenciesSection
                  blockedBy={blockedBy}
                  blocks={blocks}
                  projectId={projectId}
                />

                <ArtifactsSection artifacts={artifacts} />

                <IntegrationAttemptsSection task={task} />

                <GateDecisionsSection decisions={taskGateDecisions} />
              </div>
            </ScrollArea>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
