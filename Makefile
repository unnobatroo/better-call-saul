.PHONY: install lint format test docker-build docker-run

install:
	pip install -e ".[dev]"

lint:
	ruff check app tests

format:
	ruff format app tests

test:
	pytest

docker-build:
	docker build -t better-call-saul .

docker-run:
	docker run --rm -p 8000:8000 -v ice_station_zebra:/data better-call-saul
