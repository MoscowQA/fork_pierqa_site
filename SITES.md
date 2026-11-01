# Несколько сообществ в одном репозитории

Репозиторий собирает сайты нескольких QA-сообществ на одном движке. У каждого
сообщества свои события, спикеры, страницы и картинки; шаблоны, CSS, JS,
шрифты, генератор og-обложек и все проверки — общие.

| Сообщество | Папка            | Адрес              | Деплой                      |
|------------|------------------|--------------------|-----------------------------|
| Moscow QA  | `sites/moscowqa` | https://moscowqa.ru | GitHub Pages этого репозитория |
| Piter QA   | `sites/piterqa`  | https://piterqa.ru (уточнить) | пока не настроен, см. «Деплой» |

## Что где лежит

```
build.py, og_images.py, sites.py   движок (общий)
templates/                         шаблоны (общие)
static/css, static/js, static/fonts  оформление (общее)
heisenbug_speakers.json,
sqadays_speakers.json              данные конференций для make sync (общие)

sites/{id}/
    site.yml                       название, город, домен, соцсети
    content/events/*.md            митапы
    content/speakers/*.md          спикеры
    content/about.md, cfp.md, organizers.md, venues.md
    static/images/logo.png         логотип (шапка, favicon, og-обложки)
    static/images/speakers/        фото спикеров
    static/images/events/          обложки событий
    templates/                     необязательно: свои версии шаблонов
```

Сборка кладёт каждое сообщество в свою папку: `dist/moscowqa/`,
`dist/piterqa/`. Сначала туда копируется общий `static/`, потом поверх —
`sites/{id}/static/`. Поэтому адреса в контенте одинаковые у всех:
`photo: "/static/images/speakers/ivan-ivanov.webp"` у спикера Piter QA
ведёт на файл `sites/piterqa/static/images/speakers/ivan-ivanov.webp`.

Спикеры не общие. Доклад в `sites/piterqa/content/events/*.md` связывается
только со спикером из `sites/piterqa/content/speakers/` — по тому же правилу
точного совпадения `name`. Если человек выступал в обоих сообществах, у него
два файла, по одному в каждом. `make sync` дописывает доклады с конференций в
оба.

## site.yml

```yaml
title: "Piter QA"            # в текстах, <title>, schema.org
brand: "PiterQA"             # рядом с логотипом, на карточках, на og-обложке
description: "..."           # meta description по умолчанию
url: "https://piterqa.ru"    # без слеша на конце; SITE_URL из окружения важнее
domain: "piterqa.ru"         # в подвале og-обложки и в UID .ics-файлов
city: "Санкт-Петербург"                 # schema.org areaServed
city_genitive: "Санкт-Петербурга"       # «QA Санкт-Петербурга»
city_prepositional: "Санкт-Петербурге"  # «митапы в Санкт-Петербурге»
since: 2026                  # «© 2026 — 2027» в подвале
links:                       # пустая ссылка — значка в подвале нет
  telegram: "https://t.me/..."
  youtube: ""
  timepad: "https://....timepad.ru"
timepad_org_id: ""           # для виджета-афиши; TIMEPAD_ORG_ID важнее
```

Обязательны `title`, `brand`, `url`, `city` — без них сборка остановится с
понятной ошибкой. Остальное имеет умолчания.

Время событий у всех считается по Москве (UTC+3): Петербург в том же поясе.
Сообщество в другом часовом поясе потребует доработать `build.py`
(`MOSCOW_OFFSET`).

## Команды

`SITE` выбирает сообщество. Без него `build`, `check`, `validate` и `sync`
проходят по всем, а команды про один сайт или файл работают с moscowqa.

```bash
make sites                           # список сообществ
make build                           # все → dist/{id}/
make build SITE=piterqa              # одно
make serve SITE=piterqa              # собрать и открыть на :8000
make validate                        # проверить все сообщества
make sync                            # доклады с конференций для всех
make sync SITE=piterqa
make photos SITE=piterqa ARGS="ivan-ivanov"
make covers SITE=piterqa
make og SITE=piterqa                 # превью обложек в og-preview/piterqa/
```

Напрямую — так же: `python3 build.py piterqa`,
`python3 scripts/validate_content.py piterqa`,
`python3 parsers/sync_heisenbug.py piterqa`,
`python3 scripts/event_cover_variants.py --site piterqa`.

## Своё оформление

Тексты шаблонов собраны из `site.yml`, поэтому новому сообществу обычно
ничего переписывать не нужно. Если всё же надо — положите файл с тем же
именем в `sites/{id}/templates/` (например, `sites/piterqa/templates/index.html`
или `.../partials/event_card.html`): он заменит общий только для этого
сообщества. Свой CSS — так же через `sites/{id}/static/css/styles.css`, но
тогда правки общего стиля придётся переносить руками, так что лучше не надо.

## Новое сообщество

1. Скопируйте `sites/piterqa/` в `sites/{id}/`.
2. Заполните `site.yml`, замените `static/images/logo.png` (квадрат, ~512px,
   PNG с прозрачностью).
3. Перепишите `content/about.md`, `cfp.md`, `venues.md`, `organizers.md`
   (и поставьте в них `updated`).
4. `make check SITE={id} && make validate SITE={id}`.

CI (`.github/workflows/ci.yml`) подхватит новое сообщество сам: тесты,
сборка и валидация идут по всем папкам `sites/*/site.yml`.

## Деплой

`.github/workflows/deploy.yml` собирает и выкладывает на GitHub Pages только
`dist/moscowqa/` — у репозитория одна Pages. Для Piter QA варианты:

* **Отдельный репозиторий под Pages** (например, `piterqa_site`): workflow
  здесь собирает `dist/piterqa/` и пушит его в ветку `gh-pages` того
  репозитория (нужен deploy key или токен в секретах). Контент остаётся
  здесь, домен настраивается в том репозитории.
* **Другой хостинг** (Netlify, Cloudflare Pages, свой сервер): тот же шаг
  сборки `python build.py piterqa`, публикуется папка `dist/piterqa/`.

Ночная пересборка нужна каждому сообществу: прошедшее/предстоящее считается
на сборке.

## Общий сайт сообществ (план)

Задел под него уже есть: `load_events()`, `load_speakers()` и `load_pages()`
принимают папку контента, а `sites.load_site()` открывает любое сообщество.
Предлагаемая схема:

* `sites/{hub}/site.yml` с полем `members: [moscowqa, piterqa]` и своими
  страницами (о проекте, контакты);
* главная — ближайшие митапы всех сообществ одной лентой, с плашкой
  сообщества и ссылкой на страницу события **на сайте сообщества** (свои
  страницы событий хаб не дублирует: две копии одного митапа — это дубль
  контента для поисковиков);
* общий список спикеров: профили сообществ, склеенные по `name`, со ссылками
  на страницы на сайтах сообществ;
* общие страницы тем (`/tags/`) по докладам всех сообществ.

Что нужно решить до реализации: домен хаба, ведёт ли он на сайты сообществ
или со временем их заменяет (тогда URL вида `/moscowqa/events/...`), и
нужны ли ему свои события (совместные конференции).
