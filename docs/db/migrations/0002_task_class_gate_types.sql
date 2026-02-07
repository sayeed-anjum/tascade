-- Add first-class task classes for review and merge checkpoint tasks.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_enum e ON e.enumtypid = t.oid
    WHERE t.typname = 'task_class'
      AND e.enumlabel = 'review_gate'
  ) THEN
    ALTER TYPE task_class ADD VALUE 'review_gate' AFTER 'cross_cutting';
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_enum e ON e.enumtypid = t.oid
    WHERE t.typname = 'task_class'
      AND e.enumlabel = 'merge_gate'
  ) THEN
    ALTER TYPE task_class ADD VALUE 'merge_gate' AFTER 'review_gate';
  END IF;
END $$;
