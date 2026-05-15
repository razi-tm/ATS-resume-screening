.PHONY: install streamlit api test lint format docker-up
install:
	python -m pip install -e .[api,dev]
streamlit:
	streamlit run app.py
api:
	uvicorn app.main:app --app-dir apps/api --reload
test:
	pytest -q
lint:
	ruff check . && mypy packages apps/api
format:
	black . && ruff check . --fix
docker-up:
	docker compose up --build
