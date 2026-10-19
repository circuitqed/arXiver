-- Postgres settings for arxiver, applied with ALTER SYSTEM so they persist in
-- the pgdata volume:
--     docker compose exec -T db psql -U arxiver arxiver < ops/tune-postgres.sql
--     docker compose exec -T db psql -U arxiver arxiver -c 'select pg_reload_conf()'
--
-- Piped on stdin, not -f: the db container mounts only its data volume, so it
-- cannot see this file.
--
-- Everything here was stock default. The box has 23 GB of RAM and the article
-- table is ~24 GB, so none of this is a "fits in memory" situation -- the goal
-- is to stop the planner mis-costing index scans and to stop sorts spilling to
-- disk.

-- Was 4, the spinning-disk default. This host's block storage is SSD-backed
-- (the hypervisor reports rotational=1 regardless), so index scans were being
-- costed ~4x too expensively against sequential scans.
ALTER SYSTEM SET random_page_cost = '1.1';
ALTER SYSTEM SET effective_io_concurrency = '200';

-- Planner hint only, allocates nothing: how much of the table it can assume is
-- cached between shared_buffers and the OS page cache (11 GB in cache here).
ALTER SYSTEM SET effective_cache_size = '10GB';

-- Was 4MB, so any sort or hash over a few hundred thousand rows spilled to
-- disk. Per sort node per connection, so this is deliberately not huge -- this
-- host runs ~50 other containers.
ALTER SYSTEM SET work_mem = '32MB';

-- Was 64MB. Governs VACUUM and index builds; the former matters a lot after a
-- harvest churns millions of rows.
ALTER SYSTEM SET maintenance_work_mem = '512MB';

-- Requires a restart, unlike everything above. 2GB rather than the usual 25%
-- of RAM because this box is shared with many other projects.
ALTER SYSTEM SET shared_buffers = '2GB';
