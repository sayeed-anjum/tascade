import { Link } from "react-router-dom";

// ---------------------------------------------------------------------------
// DependencyLink -- clickable short_id that navigates to a referenced task.
// Styled as a code-like link (monospace, underlined, colored).
// ---------------------------------------------------------------------------

interface DependencyLinkProps {
  shortId: string;
  taskId: string;
  projectId: string;
}

export default function DependencyLink({
  shortId,
  taskId,
  projectId,
}: DependencyLinkProps) {
  return (
    <Link
      to={`/projects/${projectId}/tasks/${taskId}`}
      className="font-mono text-sm text-blue-600 underline hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
    >
      {shortId}
    </Link>
  );
}
