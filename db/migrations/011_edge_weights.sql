ALTER TABLE curiosity_edges ALTER COLUMN weight SET DEFAULT 0.1;
UPDATE curiosity_edges SET weight = 0.1 WHERE weight IS NULL OR weight = 0.0;