#!/bin/bash
# Restore the database from the split dump files
# Usage: ./restore-db.sh
# Requires: docker compose services to be running

set -e

echo "Waiting for database to be ready..."
until docker compose exec -T db pg_isready -U arxiver 2>/dev/null; do
    sleep 1
done

echo "Step 1: Restoring schema and non-article table data..."
gunzip -c db-init/other-tables.sql.gz | docker compose exec -T db psql -U arxiver -d arxiver 2>&1 | tail -5

echo "Step 2: Restoring article data (without search vectors)..."
gunzip -c db-init/article-data.tsv.gz | docker compose exec -T db psql -U arxiver -d arxiver -c "COPY article (id, arxiv_id, title, abstract, full_description, comments, created, updated, doi, journalref, mscclass, acmclass, license) FROM STDIN" 2>&1

echo "Step 3: Updating sequence..."
docker compose exec -T db psql -U arxiver -d arxiver -c "SELECT setval('article_id_seq', (SELECT MAX(id) FROM article));"

echo "Step 4: Regenerating search vectors (this will take a while)..."
docker compose exec -T db psql -U arxiver -d arxiver -c "UPDATE article SET title = title WHERE search_vector IS NULL;" 2>&1

echo "Step 5: Updating table statistics..."
docker compose exec -T db psql -U arxiver -d arxiver -c "ANALYZE;" 2>&1

echo "Done! Database restored."
