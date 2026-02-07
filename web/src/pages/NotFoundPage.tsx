import { Link } from "react-router-dom";

// ---------------------------------------------------------------------------
// NotFoundPage -- shown for unrecognised routes.
// ---------------------------------------------------------------------------

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-background text-foreground">
      <h1 className="text-6xl font-bold">404</h1>
      <p className="text-muted-foreground text-lg">Page not found</p>
      <Link
        to="/projects"
        className="text-primary underline underline-offset-4 hover:text-primary/80"
      >
        Back to projects
      </Link>
    </div>
  );
}
