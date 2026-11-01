"""Тесты сборки нескольких сообществ из одного репозитория.

Главный риск здесь — утечка одного сообщества в другое: спикер Moscow QA на
сайте Piter QA, чужой логотип на обложке, ссылка на moscowqa.ru из разметки
петербургского митапа. Поэтому тесты собирают настоящий сайт из маленького
сообщества во временной папке и смотрят на получившийся HTML.
Запуск: `make test` или `python3 -m pytest`.
"""
import re
import sys
import textwrap
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402
import sites  # noqa: E402


SITE_YML = """\
title: "Demo QA"
brand: "DemoQA"
url: "https://demo-qa.example"
city: "Казань"
city_genitive: "Казани"
city_prepositional: "Казани"
since: 2025
links:
  telegram: "https://t.me/demoqa"
"""

EVENT_MD = """\
---
title: "Demo QA #1"
number: 1
date: "2026-12-10"
time: "19:00"
type: "Offline"
address: "Казань, Примерная улица, 1"
company: "Пример"
talks:
  - title: "Первый доклад"
    speakers: ["Иван Иванов"]
    tags: ["автоматизация"]
---
Описание.
"""

SPEAKER_MD = """\
---
name: "Иван Иванов"
company: "Пример"
photo: "/static/images/speakers/ivan-ivanov.webp"
---
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Папка sites/ с одним сообществом demo; dist/ — тоже во временной папке."""
    sites_dir = tmp_path / "sites"
    demo = sites_dir / "demo"
    write(demo / "site.yml", SITE_YML)
    write(demo / "content" / "events" / "01-demo.md", EVENT_MD)
    write(demo / "content" / "speakers" / "ivan-ivanov.md", SPEAKER_MD)
    write(demo / "content" / "about.md", "---\ntitle: О нас\n---\nТекст.\n")

    images = demo / "static" / "images"
    (images / "speakers").mkdir(parents=True)
    Image.new("RGB", (1080, 1080), "white").save(images / "speakers" / "ivan-ivanov.webp")
    Image.new("RGB", (540, 540), "white").save(images / "speakers" / "ivan-ivanov-540.webp")
    Image.new("RGBA", (64, 64), "red").save(images / "logo.png")

    monkeypatch.setattr(sites, "SITES_DIR", sites_dir)
    monkeypatch.setattr(sites, "DIST_DIR", tmp_path / "dist")
    monkeypatch.delenv("SITE", raising=False)
    monkeypatch.delenv("SITE_URL", raising=False)
    yield tmp_path
    # Вернуть модуль сборки на сообщество по умолчанию для остальных тестов.
    monkeypatch.undo()
    build.configure()


class TestLoadSite:
    def test_reads_config_and_paths(self, sandbox):
        site = sites.load_site("demo")
        assert site.config["title"] == "Demo QA"
        assert site.domain == "demo-qa.example"
        assert site.events_dir == sandbox / "sites" / "demo" / "content" / "events"
        assert site.output_dir == sandbox / "dist" / "demo"

    def test_unknown_site_names_the_known_ones(self, sandbox):
        with pytest.raises(SystemExit, match="Есть: demo"):
            sites.load_site("nope")

    def test_missing_required_field(self, sandbox):
        write(sandbox / "sites" / "broken" / "site.yml", 'title: "Broken"\n')
        with pytest.raises(SystemExit, match="brand, url, city"):
            sites.load_site("broken")

    def test_site_url_from_environment_wins(self, sandbox, monkeypatch):
        monkeypatch.setenv("SITE_URL", "https://staging.example/")
        assert sites.load_site("demo").url == "https://staging.example"

    def test_resolve_all_by_default(self, sandbox):
        write(sandbox / "sites" / "other" / "site.yml", SITE_YML)
        assert [s.id for s in sites.resolve_sites([])] == ["demo", "other"]
        assert [s.id for s in sites.resolve_sites(["other"])] == ["other"]

    def test_resolve_respects_site_env(self, sandbox, monkeypatch):
        write(sandbox / "sites" / "other" / "site.yml", SITE_YML)
        monkeypatch.setenv("SITE", "other")
        assert [s.id for s in sites.resolve_sites([])] == ["other"]


class TestStaticPath:
    def test_community_file_wins_over_shared(self, tmp_path):
        site = sites.Site("demo", tmp_path / "site")
        for root in (tmp_path / "site", tmp_path / "shared"):
            write(root / "static" / "images" / "logo.png", root.name)
        found = site.static_path("/static/images/logo.png", tmp_path / "shared")
        assert found == tmp_path / "site" / "static" / "images" / "logo.png"

    def test_falls_back_to_shared(self, tmp_path):
        site = sites.Site("demo", tmp_path / "site")
        write(tmp_path / "shared" / "static" / "css" / "styles.css", "")
        found = site.static_path("/static/css/styles.css", tmp_path / "shared")
        assert found == tmp_path / "shared" / "static" / "css" / "styles.css"

    def test_missing_file(self, tmp_path):
        site = sites.Site("demo", tmp_path / "site")
        assert site.static_path("/static/nope.png", tmp_path) is None
        assert site.static_path("", tmp_path) is None


class TestBuildCommunity:
    @pytest.fixture
    def dist(self, sandbox, capsys):
        build.build("demo")
        capsys.readouterr()
        return sandbox / "dist" / "demo"

    def read(self, dist, path):
        return (dist / path).read_text(encoding="utf-8")

    def test_branding_comes_from_site_yml(self, dist):
        html = self.read(dist, "index.html")
        assert "DemoQA" in html
        assert "QA Казани" in html
        assert "Moscow" not in html and "Москв" not in html

    def test_footer_years_and_links(self, dist):
        html = self.read(dist, "index.html")
        assert re.search(r"&copy; 2025 &mdash; \d{4}, Demo QA Team", html)
        assert "https://t.me/demoqa" in html
        # YouTube и Timepad в site.yml не заданы — значков нет, пустых ссылок тоже.
        assert 'title="YouTube"' not in html
        assert 'href=""' not in html

    def test_speaker_and_talk_link_up(self, dist):
        event = self.read(dist, "events/01-demo/index.html")
        assert "/speakers/ivan-ivanov/" in event
        speaker = self.read(dist, "speakers/ivan-ivanov/index.html")
        assert "Доклады на Demo QA" in speaker
        assert "ivan-ivanov-540.webp" in speaker

    def test_community_images_are_copied_over_shared_static(self, dist):
        assert (dist / "static" / "images" / "speakers" / "ivan-ivanov.webp").is_file()
        assert (dist / "static" / "css" / "styles.css").is_file()
        with Image.open(dist / "static" / "images" / "logo.png") as logo:
            assert logo.size == (64, 64)

    def test_absolute_urls_use_community_domain(self, dist):
        assert "<loc>https://demo-qa.example/</loc>" in self.read(dist, "sitemap.xml")
        assert "https://demo-qa.example/sitemap.xml" in self.read(dist, "robots.txt")
        ics = self.read(dist, "events/01-demo/event.ics")
        assert "UID:01-demo@demo-qa.example" in ics
        assert "PRODID:-//Demo QA//demo-qa.example//RU" in ics
        event = self.read(dist, "events/01-demo/index.html")
        assert '"name": "Demo QA"' in event
        assert "moscowqa" not in event

    def test_og_card_is_generated(self, dist):
        assert (dist / "static" / "og" / "events" / "01-demo.png").is_file()

    def test_no_moscow_content_leaks_in(self, dist):
        assert not (dist / "events" / "28-black").exists()
        assert sorted(p.name for p in (dist / "speakers").iterdir()) == [
            "index.html", "ivan-ivanov",
        ]

    def test_template_override(self, sandbox, capsys):
        write(sandbox / "sites" / "demo" / "templates" / "page.html",
              "{% extends 'base.html' %}{% block content %}СВОЙ ШАБЛОН{% endblock %}")
        build.build("demo")
        capsys.readouterr()
        about = (sandbox / "dist" / "demo" / "about" / "index.html").read_text()
        assert "СВОЙ ШАБЛОН" in about


class TestRealCommunities:
    """Те сообщества, что лежат в репозитории, читаются без ошибок."""

    @pytest.mark.parametrize("site_id", sites.available_sites())
    def test_site_yml_is_valid(self, site_id):
        site = sites.load_site(site_id)
        assert site.content_dir.is_dir()
        assert site.logo_path.is_file()

    def test_moscowqa_is_the_default(self, monkeypatch):
        monkeypatch.delenv("SITE", raising=False)
        assert sites.load_site().id == "moscowqa"
