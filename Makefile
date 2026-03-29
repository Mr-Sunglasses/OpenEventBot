.PHONY: install run docker-up docker-down docker-build clean help

help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | sed 's/://' | sort

install:
	uv sync

run:
	uv run openevent-bot

docker-build:
	docker build -t event-bot .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .venv data/ uv.lock
