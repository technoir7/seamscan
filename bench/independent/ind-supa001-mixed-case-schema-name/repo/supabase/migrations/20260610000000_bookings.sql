CREATE TABLE Public.Bookings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  guest_name text NOT NULL,
  check_in date NOT NULL,
  check_out date NOT NULL
);
CREATE INDEX bookings_dates ON Public.Bookings (check_in, check_out);
