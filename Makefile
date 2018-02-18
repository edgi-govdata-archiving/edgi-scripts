setup:
	pip install --quiet -r requirements.txt

check-yt-env:
ifndef EDGI_ZOOM_API_KEY
    $(error EDGI_ZOOM_API_KEY environment variable is not set)
endif
ifndef EDGI_ZOOM_API_SECRET
	$(error EDGI_ZOOM_API_SECRET environment variable is not set)
endif

check-ia-env:
ifndef SCANNER_USER
    $(error SCANNER_USER environment variable is not set)
endif
ifndef SCANNER_PASSWORD
	$(error SCANNER_PASSWORD environment variable is not set)
endif

run-yt-upload: check-yt-env setup ## Upload Zoom meetings to YouTube
	python scripts/upload_zoom_recordings.py

run-ia-healthcheck: check-ia-env setup ## Checked the health status of the Internet Archive
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
