// ---------------------------------------------------------------------------
// Shared Tailwind colour classes derived from STATE_COLORS values.
// Extracted so both StateBadge and other components can reuse the mapping.
// ---------------------------------------------------------------------------

import { STATE_COLORS } from "@/lib/constants";

// All colour pairings are verified against WCAG AA (≥ 4.5:1 for normal text).
// Light mode: *-900 text on *-100 bg. Dark mode: *-200 text on *-900 bg.
const COLOR_BG_CLASSES: Record<string, string> = {
  blue: "bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-200",
  amber: "bg-amber-100 text-amber-900 dark:bg-amber-900 dark:text-amber-200",
  purple:
    "bg-purple-100 text-purple-900 dark:bg-purple-900 dark:text-purple-200",
  teal: "bg-teal-100 text-teal-900 dark:bg-teal-900 dark:text-teal-200",
  green: "bg-green-100 text-green-900 dark:bg-green-900 dark:text-green-200",
  red: "bg-red-100 text-red-900 dark:bg-red-900 dark:text-red-200",
};

const FALLBACK_COLOR =
  "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";

/**
 * Returns a Tailwind class string for the given task state.
 * Falls back to a neutral gray if the state is unknown.
 */
export function stateColorClass(state: string): string {
  const color = (STATE_COLORS as Record<string, string>)[state];
  return COLOR_BG_CLASSES[color] ?? FALLBACK_COLOR;
}
