.DEFAULT_GOAL := help
PIO           := pio

.PHONY: help build upload monitor clean secrets

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

build: ## Compile firmware
	$(PIO) run

upload: ## Compile and flash firmware to connected ESP32
	$(PIO) run --target upload

monitor: ## Open serial monitor (115200 baud)
	$(PIO) device monitor

upload-monitor: ## Flash firmware then open serial monitor
	$(PIO) run --target upload && $(PIO) device monitor

clean: ## Remove PlatformIO build artifacts
	$(PIO) run --target clean

secrets: ## Create secrets.h from example (skips if already exists)
	@test -f main/secrets.h && echo "main/secrets.h already exists, skipping." || \
		(cp main/secrets.example.h main/secrets.h && echo "Created main/secrets.h — fill in your WiFi credentials")
