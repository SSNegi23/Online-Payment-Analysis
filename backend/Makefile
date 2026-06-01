# backend/Makefile
.PHONY: run dev install freeze lint

# Run the backend server (production-like, no reload)
run:
	cd .. && uvicorn backend.app.main:app --port 8000

# Run with auto-reload (development mode)
dev:
	cd .. && uvicorn backend.app.main:app --reload --port 8000

# Install all dependencies from root requirements.txt
install:
	pip install -r ../requirements.txt

# Update requirements.txt after installing new packages
freeze:
	pip freeze > ../requirements.txt

# Check for any obvious errors (requires pyflakes: pip install pyflakes)
lint:
	python -m pyflakes app/
