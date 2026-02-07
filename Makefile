.PHONY: build-web serve

# Build the web UI production bundle (output: web/dist/)
build-web:
	cd web && npm install && npm run build

# Run the FastAPI server (serves API + embedded UI)
serve: build-web
	uvicorn app.main:app --host 0.0.0.0 --port 8000
