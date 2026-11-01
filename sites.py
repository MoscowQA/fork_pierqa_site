"""Сообщества, которые собирает этот репозиторий.

Движок у всех один: `build.py`, шаблоны из `templates/`, CSS, JS и шрифты
из `static/`. Своё у каждого сообщества лежит в `sites/{id}/`:

    sites/{id}/site.yml                    название, город, домен, соцсети
    sites/{id}/content/events/*.md         митапы
    sites/{id}/content/speakers/*.md       спикеры
    sites/{id}/content/*.md                about, cfp, organizers, venues
    sites/{id}/static/images/...           логотип, фото спикеров, обложки
    sites/{id}/templates/                  (необязательно) свои шаблоны

На сборке `sites/{id}/static/` накладывается поверх общего `static/`, поэтому
адреса в контенте не зависят от сообщества: фото спикера — это всё так же
`/static/images/speakers/{слаг}.webp`. Найти такой файл на диске помогает
`Site.static_path`.

Шаблон из `sites/{id}/templates/` с тем же именем, что и общий, заменяет
общий — так сообщество может переписать, например, главную, не трогая
остальных.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SITES_DIR = ROOT / "sites"
SHARED_STATIC_DIR = ROOT / "static"
SHARED_TEMPLATES_DIR = ROOT / "templates"
DIST_DIR = ROOT / "dist"

# Сообщество, которое собирается, когда его не назвали: исторически сайт был
# один, и всё, что запускают без аргументов, по-прежнему про Moscow QA.
DEFAULT_SITE = "moscowqa"

# Поля site.yml, без которых сайт не собрать. Остальные — с умолчаниями.
REQUIRED_FIELDS = ("title", "brand", "url", "city")


@dataclass
class Site:
    id: str
    dir: Path
    config: dict = field(default_factory=dict)

    @property
    def content_dir(self) -> Path:
        return self.dir / "content"

    @property
    def events_dir(self) -> Path:
        return self.content_dir / "events"

    @property
    def speakers_dir(self) -> Path:
        return self.content_dir / "speakers"

    @property
    def static_dir(self) -> Path:
        return self.dir / "static"

    @property
    def templates_dir(self) -> Path:
        return self.dir / "templates"

    @property
    def output_dir(self) -> Path:
        return DIST_DIR / self.id

    @property
    def url(self) -> str:
        """Адрес сайта без слеша на конце. SITE_URL из окружения важнее."""
        return (os.environ.get("SITE_URL") or self.config["url"]).rstrip("/")

    @property
    def domain(self) -> str:
        return self.config.get("domain") or self.url.split("://", 1)[-1]

    @property
    def logo_path(self) -> Path:
        return self.static_path("/static/images/logo.png") or (
            self.static_dir / "images" / "logo.png"
        )

    def template_dirs(self) -> list[str]:
        """Где Jinja ищет шаблоны: сначала свои, потом общие."""
        dirs = []
        if self.templates_dir.is_dir():
            dirs.append(str(self.templates_dir))
        dirs.append(str(SHARED_TEMPLATES_DIR))
        return dirs

    def static_path(self, url: str, shared_root: Path = ROOT) -> Path | None:
        """Файл на диске для адреса `/static/...`, или None, если его нет.

        Сначала смотрим в static/ сообщества, потом в общий — в том же
        порядке, в каком они наслаиваются в dist/.
        """
        relative = (url or "").strip().lstrip("/")
        if not relative:
            return None
        for root in (self.dir, shared_root):
            candidate = root / relative
            if candidate.exists():
                return candidate
        return None

    def rel(self, path: Path) -> str:
        return rel(path)


def rel(path: Path) -> str:
    """Путь от корня репозитория — для сообщений об ошибках."""
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def available_sites() -> list[str]:
    """Все сообщества: папки в sites/, у которых есть site.yml."""
    if not SITES_DIR.is_dir():
        return []
    return sorted(p.name for p in SITES_DIR.iterdir() if (p / "site.yml").is_file())


def load_site(site_id: str | None = None) -> Site:
    """Прочитать sites/{id}/site.yml. Без id — SITE из окружения или moscowqa."""
    site_id = (site_id or os.environ.get("SITE") or DEFAULT_SITE).strip()
    directory = SITES_DIR / site_id
    config_file = directory / "site.yml"
    if not config_file.is_file():
        known = ", ".join(available_sites()) or "нет ни одного"
        raise SystemExit(
            f"Нет сообщества «{site_id}»: не найден {rel(config_file)}. "
            f"Есть: {known}."
        )

    config = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    missing = [name for name in REQUIRED_FIELDS if not config.get(name)]
    if missing:
        raise SystemExit(
            f"{rel(config_file)}: нет обязательных полей {', '.join(missing)}"
        )
    config.setdefault("links", {})
    config.setdefault("city_genitive", config["city"])
    config.setdefault("city_prepositional", config["city"])
    config.setdefault(
        "description", f"QA-сообщество {config['city_genitive']} — митапы по тестированию"
    )
    return Site(id=site_id, dir=directory, config=config)


def resolve_sites(names: list[str] | None, all_by_default: bool = True) -> list[Site]:
    """Сообщества по списку из командной строки.

    Пустой список — все сообщества (или одно по умолчанию, если
    `all_by_default=False`). Слово `all` тоже значит «все».
    """
    names = [n for n in (names or []) if n]
    if not names or names == ["all"]:
        if os.environ.get("SITE"):
            return [load_site(os.environ["SITE"])]
        if all_by_default:
            return [load_site(n) for n in available_sites()]
        return [load_site(DEFAULT_SITE)]
    return [load_site(n) for n in names]
