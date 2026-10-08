-- Bookings for the salon scheduler
CREATE TABLE IF NOT EXISTS Public.Bookings (
  Id BIGSERIAL PRIMARY KEY,
  Customer_Name TEXT NOT NULL,
  Phone TEXT NOT NULL,
  Service TEXT NOT NULL,
  Starts_At TIMESTAMPTZ NOT NULL,
  Notes TEXT
);

CREATE INDEX IF NOT EXISTS bookings_starts_at_idx ON Public.Bookings (Starts_At);
