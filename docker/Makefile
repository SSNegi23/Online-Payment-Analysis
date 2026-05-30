.PHONY: up down reset logs psql status

# Start Postgres in background
up:
	docker compose up -d

# Stop Postgres (data is safe)
down:
	docker compose down

# Wipe everything including DB data — fresh start
reset:
	docker compose down -v
	rm -rf pgdata/

# Tail live Postgres logs
logs:
	docker compose logs -f postgres

# Open psql shell directly
psql:
	docker exec -it onlinepayment_postgres psql -U onlinepayment_user -d payment_db

# Check if container is running
status:
	docker compose ps