"""Paris-to-New York collection hours, including independent DST changes."""
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import runpy

import pytest

from scripts.internships_refresh_window import collection_window_open
from internships_project import internships as jobs


@pytest.mark.parametrize('day,last_paris_hour', [
    ('2026-01-15', 4), ('2026-03-15', 3), ('2026-04-15', 4),
    ('2026-10-27', 3), ('2026-11-15', 4),
])
def test_daily_opening_and_closing(day, last_paris_hour):
    paris = ZoneInfo('Europe/Paris')
    opening = datetime.combine(date.fromisoformat(day), time(8, 7), paris)
    assert not collection_window_open(opening - timedelta(hours=1))
    assert collection_window_open(opening)
    closing = (opening + timedelta(days=1)).replace(hour=last_paris_hour)
    assert collection_window_open(closing)
    assert closing.astimezone(ZoneInfo('America/New_York')).hour == 22
    assert not collection_window_open(closing + timedelta(hours=1))


def test_every_hour_of_2026_is_covered_without_duplicate_dst_slots():
    paris, ny = ZoneInfo('Europe/Paris'), ZoneInfo('America/New_York')
    candidate_hours = {0, 1, 2, 3, *range(6, 24)}
    now = datetime(2026, 1, 1, 0, 7, tzinfo=timezone.utc)
    for _ in range(365 * 24):
        opening_day = now.astimezone(paris).date()
        opening = datetime.combine(opening_day, time(8), paris)
        if now < opening:
            opening_day -= timedelta(days=1)
            opening = datetime.combine(opening_day, time(8), paris)
        closing = datetime.combine(opening_day, time(23), ny)
        expected = opening <= now < closing
        assert collection_window_open(now) is expected
        assert not expected or now.hour in candidate_hours
        now += timedelta(hours=1)


def test_manual_launch_bypasses_window_and_writes_output(tmp_path, monkeypatch):
    output = tmp_path / 'output'
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'workflow_dispatch')
    monkeypatch.setenv('GITHUB_OUTPUT', str(output))
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/internships_refresh_window.py'), run_name='__main__')
    assert output.read_text().strip() == 'active=true'


def test_hourly_public_cache_keeps_local_defaults(monkeypatch):
    monkeypatch.delenv('INTERNSHIPS_SOURCE_CACHE_SECONDS', raising=False)
    assert jobs._source_refresh_seconds('BNP Paribas', None) == 4 * 3600
    assert jobs._source_refresh_seconds('JobTeaser · sitemap', None) == 24 * 3600
    monkeypatch.setenv('INTERNSHIPS_SOURCE_CACHE_SECONDS', '3300')
    assert jobs._source_refresh_seconds('BNP Paribas', None) == 3300
    assert jobs._source_refresh_seconds('JobTeaser · sitemap', None) == 3300


def test_workflow_gates_build_and_configures_hourly_checks():
    root = Path(__file__).resolve().parents[1]
    path = root / '.github/workflows/pages.yml'
    if not path.is_file():
        path = root / 'deploy/github-pages/pages.yml'
    workflow = path.read_text(encoding='utf-8')
    assert "cron: '7 0-3,6-23 * * *'" in workflow
    assert 'timezone: Etc/UTC' in workflow
    assert 'needs: window' in workflow and "if: needs.window.outputs.active == 'true'" in workflow
    assert 'python3 scripts/internships_refresh_window.py' in workflow
    assert "INTERNSHIPS_SOURCE_CACHE_SECONDS: '3300'" in workflow
