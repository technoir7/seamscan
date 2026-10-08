/*
  # Add priority and due dates to todos

  1. Changes
    - Recreate `todos` with `priority` and `due_date` columns
*/

DROP TABLE IF EXISTS todos;

CREATE TABLE todos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) NOT NULL,
  title text NOT NULL,
  completed boolean DEFAULT false,
  priority text DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
  due_date date,
  created_at timestamptz DEFAULT now()
);
