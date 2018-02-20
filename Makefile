setup:
	pip install -r requirements.txt

run-yt-auth: setup ## Authenticate against YouTube API to generate credentials file
	python scripts/auth.py

run-yt-upload: setup ## Upload Zoom meetings to YouTube
	python scripts/upload_zoom_recordings.py

run-ia-healthcheck: setup ## Check the health status of the Internet Archive
	python scripts/ia_healthcheck.py

%:
	@true

.PHONY: help

help:
	@echo 'Usage: make <command>'
	@echo
	@echo 'where <command> is one of the following:'
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
