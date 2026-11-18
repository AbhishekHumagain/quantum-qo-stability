-- Dedicated synthetic smoke-test schema; idempotent and project-local.
CREATE SCHEMA IF NOT EXISTS qopt_smoke;
CREATE TABLE IF NOT EXISTS qopt_smoke.dim (id integer PRIMARY KEY, bucket integer NOT NULL);
CREATE TABLE IF NOT EXISTS qopt_smoke.fact (id integer PRIMARY KEY, a integer, b integer, c integer, d integer);
INSERT INTO qopt_smoke.dim SELECT i, i % 10 FROM generate_series(1,1000) i ON CONFLICT DO NOTHING;
INSERT INTO qopt_smoke.fact SELECT i, 1+i%1000, 1+(i*7)%1000, 1+(i*13)%1000, 1+(i*17)%1000
FROM generate_series(1,20000) i ON CONFLICT DO NOTHING;
ANALYZE qopt_smoke.dim;
ANALYZE qopt_smoke.fact;
