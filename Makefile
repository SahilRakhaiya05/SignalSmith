.PHONY: setup start test lint

setup:
	cp -n .env.example .env 2>/dev/null || true
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

start:
	./scripts/start.sh

test:
	cd backend && REQUIRE_SPLUNK=false python -m pytest tests -v

lint:
	cd backend && python -m compileall app
	cd frontend && npm run lint