# Makefile для сайтов QA-сообществ (Moscow QA, Piter QA, ...).
#
# Обёртка над командами, которые описаны в CLAUDE.md, SITES.md, EVENT_GUIDE.md
# и parsers/README.md — сами скрипты по-прежнему можно запускать напрямую.
#
#   make                      список целей
#   make build                собрать все сообщества в dist/{id}/
#   make build SITE=piterqa   только одно
#   make serve SITE=piterqa   собрать и открыть локально (по умолчанию moscowqa)
#
# SITE выбирает сообщество из sites/. Где он не указан, build, validate и
# sync проходят по всем сообществам, а команды про конкретный файл (photos,
# covers, og, serve) работают с moscowqa.
#
# Переменные окружения передаются сборке как есть, например:
#   TIMEPAD_WIDGET_MODE=popup make build

PYTHON ?= python3
VENV ?= .venv
PORT ?= 8000
DIST := dist
SITE ?=
# Для команд, которым нужно ровно одно сообщество.
ONE_SITE := $(or $(SITE),moscowqa)
SITE_FLAG := --site $(ONE_SITE)

.DEFAULT_GOAL := help

.PHONY: help sites install install-dev install-parsers venv build serve clean check test validate \
	sync sync-dry sync-heisenbug sync-sqadays \
	collect-heisenbug collect-sqadays photo photos covers og fonts

help: ## Показать этот список
	@awk 'BEGIN {FS = ":.*##"} \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } \
		/^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-19s\033[0m %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST)
	@echo ""

##@ Сборка сайта

sites: ## Список сообществ из sites/
	@for d in sites/*/site.yml; do id=$$(basename $$(dirname $$d)); \
		printf "  \033[36m%-12s\033[0m %s\n" "$$id" "$$(sed -n 's/^title: *"\{0,1\}\([^"]*\)"\{0,1\}.*/\1/p' $$d)"; done

install: ## Установить зависимости сборки
	$(PYTHON) -m pip install -r requirements.txt

install-dev: ## Установить зависимости для тестов
	$(PYTHON) -m pip install -r requirements-dev.txt

build: ## Собрать сайты в dist/{id}/ (SITE=piterqa — только одно)
	$(PYTHON) build.py $(SITE)

serve: ## Собрать и поднять локальный сервер (SITE=moscowqa, PORT=8000)
	$(PYTHON) build.py $(ONE_SITE)
	@echo "→ http://127.0.0.1:$(PORT)/  (Ctrl+C — остановить)"
	@cd $(DIST)/$(ONE_SITE) && $(PYTHON) -m http.server $(PORT)

clean: ## Удалить dist/ и кэш Python
	rm -rf $(DIST)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

test: ## Прогнать тесты (pytest)
	$(PYTHON) -m pytest -q

validate: build ## Проверить контент и ссылки в собранных сайтах
	$(PYTHON) scripts/validate_content.py $(SITE)

check: ## Проверить синтаксис Python и прогнать сборку
	$(PYTHON) -m compileall -q build.py og_images.py sites.py parsers scripts
	$(PYTHON) build.py $(SITE)
	@for d in $(if $(SITE),sites/$(SITE),sites/*); do id=$$(basename $$d); out=$(DIST)/$$id; \
		test -s $$out/index.html || { echo "$$out/index.html не собрался"; exit 1; }; \
		test -s $$out/sitemap.xml || { echo "$$out/sitemap.xml не собрался"; exit 1; }; \
		if ls $$d/content/events/*.md >/dev/null 2>&1; then \
			ls $$out/static/og/events/*.png >/dev/null 2>&1 || { echo "$$id: og-обложки не собрались"; exit 1; }; \
		fi; \
	done
	@echo "OK"

##@ Спикеры и конференции

install-parsers: ## Установить зависимости парсеров
	$(PYTHON) -m pip install -r parsers/requirements.txt

venv: ## Создать .venv и поставить в него все зависимости
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements-dev.txt -r parsers/requirements.txt
	@echo "Активировать: source $(VENV)/bin/activate"

sync: sync-heisenbug sync-sqadays ## Подтянуть внешние доклады спикеров всех сообществ (или SITE=...)

sync-heisenbug: ## Подтянуть доклады с Heisenbug
	$(PYTHON) parsers/sync_heisenbug.py $(SITE) $(ARGS)

sync-sqadays: ## Подтянуть доклады с SQA Days
	$(PYTHON) parsers/sync_sqadays.py $(SITE) $(ARGS)

sync-dry: ## Показать, что изменит sync, ничего не записывая
	$(PYTHON) parsers/sync_heisenbug.py --dry-run $(SITE)
	$(PYTHON) parsers/sync_sqadays.py --dry-run $(SITE)

collect-heisenbug: ## Заново собрать данные с heisenbug.ru (ARGS="--edition '2026 Spring'")
	$(PYTHON) parsers/collect_heisenbug.py $(ARGS)

collect-sqadays: ## Заново собрать данные с sqadays.com (ARGS="--event 144051")
	$(PYTHON) parsers/collect_sqadays.py $(ARGS)

##@ Прочее

photo: ## Сжать фото спикера до ~1080px (FILE=sites/moscowqa/static/images/speakers/name.png)
	@test -n "$(FILE)" || { echo "Укажите файл: make photo FILE=sites/$(ONE_SITE)/static/images/speakers/name.png"; exit 1; }
	$(PYTHON) scripts/compress_photo.py $(FILE) $(ARGS)

photos: ## Перенести фото спикеров к себе в webp (SITE=..., ARGS="ivan-ivanov" или --dry-run)
	$(PYTHON) scripts/localize_speaker_photos.py $(SITE_FLAG) $(ARGS)

covers: ## Пересобрать webp-варианты обложек событий (SITE=..., ARGS="28-black" или --dry-run)
	$(PYTHON) scripts/event_cover_variants.py $(SITE_FLAG) $(ARGS)

og: ## Посмотреть og-обложки событий в og-preview/{id}/ (SITE=..., ARGS="28-black")
	$(PYTHON) og_images.py $(SITE_FLAG) --out og-preview/$(ONE_SITE) $(ARGS)

fonts: ## Перекачать Inter с Google Fonts к себе и пересобрать fonts.css
	$(PYTHON) scripts/fetch_fonts.py $(ARGS)
