"""Export only allowlisted public offer fields to an isolated static directory."""
from __future__ import annotations

import argparse
import json
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from internships_project import internships as jobs
from internships_project.public_safety import assert_public, public_job_url, validate_snapshot


def discovery_dates(offers: list, updated: datetime) -> tuple[Path, dict[str, str]]:
    path = jobs.CACHE_PATH.with_name("pages_discovery_dates.json")
    try:
        dates = json.loads(path.read_bytes())
    except FileNotFoundError:
        dates = {}
    if not isinstance(dates, dict):
        raise ValueError("Invalid offer discovery history")

    def remember(url: str, stamp: str):
        parsed = datetime.fromisoformat(stamp)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        value = parsed.astimezone(timezone.utc).isoformat()
        dates[url] = min(dates.get(url, value), value)

    for url, stamp in list(dates.items()):
        remember(url, stamp)
    seed = ROOT / "public_seed.json"
    if seed.is_file():
        document = json.loads(seed.read_bytes())
        validate_snapshot(document)
        for record in document["offers"]:
            if record.get("discovered_at"):
                remember(record["url"], record["discovered_at"])
    history = jobs._read_history_document()
    for snapshot in [history.get("baseline"), *(history.get("snapshots") or [])]:
        if not isinstance(snapshot, dict) or not snapshot.get("updated"):
            continue
        for record in snapshot.get("jobs") or []:
            if isinstance(record, dict) and record.get("url"):
                # A posting date is not evidence of when our collector found the offer.
                remember(record["url"], snapshot["updated"])
    for offer in offers:
        if offer.url not in dates:
            remember(offer.url, updated.isoformat())
    return path, dates


def build_site(output: Path, *, collect: bool = False, force: bool = False) -> int:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Build directory must be empty; existing files are never published implicitly")
    if collect:
        seed = ROOT / "public_seed.json"
        if not jobs.CACHE_PATH.exists() and seed.is_file():
            seed_bytes = seed.read_bytes()
            assert_public(seed_bytes, "public seed")
            previous = json.loads(seed_bytes)
            validate_snapshot(previous)
            baseline = [jobs.Opportunity(
                title=j["title"], company=j["company"], location=j["location"], kind=j["kind"],
                url=public_job_url(j["url"]), published=j["published"], score=max(0, 1000-i),
                start_period=j["start"], family=j["family"],
                published_inferred=j["date_label"].startswith("Détectée"),
            ) for i, j in enumerate(previous["offers"])]
            jobs._write_cache(datetime.fromisoformat(previous["updated"]), baseline, [])
        offers, _, updated = jobs.refresh_opportunities(force=force, notify_email=False, fail_if_busy=True)
    else:
        offers, _, updated = jobs.load_opportunities(refresh=False)
    if not offers:
        raise ValueError("No offers available; preserve the previous deployment")
    discovery_path, detected = discovery_dates(offers, updated)
    categories = ("Stages Paris", "Stages International", "VIE", "Graduate")
    records = []
    logos = {}
    for job in jobs.matching_opportunities(offers):
        host = jobs.COMPANY_ICON_HOSTS.get(jobs._canonical_company(job.company), "")
        logo = jobs.COMPANY_LOGO_DIR / f"{host}.png"
        icon = ""
        if host and logo.is_file() and not logo.is_symlink() and logo.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            icon = f"logos/{logo.name}"
            logos[icon] = logo
        # No description, profile, tracking, raw error, token or account data.
        records.append({
            "title": jobs._display_offer_title(job.title), "company": job.company,
            "location": job.location or "Non précisé", "kind": job.kind,
            "url": public_job_url(job.url), "published": job.published,
            "discovered_at": detected[job.url],
            "date_label": ("Détectée le " if job.published_inferred else "Publiée le ") + jobs._display_offer_date(job.published),
            "start": jobs._display_offer_date(job.start_period), "start_month": jobs.start_month(job.start_period) or "",
            "family": job.family, "logo": icon,
            "categories": [category for category in categories if jobs.matching_opportunities([job], category)],
        })
    checks = jobs.source_checks()
    payload = json.dumps({"updated": updated.isoformat(), "generated": datetime.now(timezone.utc).isoformat(),
                          "sources": {"checked": len(checks),
                                      "unavailable": sum(c.get("status") == "error" for c in checks.values()),
                                      "retained": sum(c.get("status") == "stale" for c in checks.values())},
                          "offers": records}, ensure_ascii=False, separators=(",", ":")).encode()
    assert_public(payload, "offers.json")
    validate_snapshot(json.loads(payload))
    assets = {name: ROOT / "deploy/github-pages/site" / name for name in ("index.html", "site.css", "app.js", "marketdesk-icon.svg")}
    assets.update(logos)
    # Validate every byte before creating the publish directory.
    for name, path in assets.items():
        if path.is_symlink():
            raise ValueError("Symlink in public assets")
        assert_public(path.read_bytes(), name)
    output.mkdir(parents=True, exist_ok=True)
    for name, path in assets.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if name == "index.html":
            document = path.read_text(encoding="utf-8")
            for asset in ("site.css", "app.js"):
                version = hashlib.sha256(assets[asset].read_bytes()).hexdigest()[:12]
                document = document.replace(f'"{asset}"', f'"{asset}?v={version}"')
            assert_public(document.encode(), "index.html")
            target.write_text(document, encoding="utf-8")
        else:
            shutil.copyfile(path, target)
    (output / "offers.json").write_bytes(payload)
    (output / ".nojekyll").touch()
    discovery_bytes = json.dumps(detected, separators=(",", ":")).encode()
    assert_public(discovery_bytes, "public discovery dates")
    discovery_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = discovery_path.with_suffix(".tmp")
    temporary.write_bytes(discovery_bytes)
    temporary.replace(discovery_path)
    return len(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--force", action="store_true", help="Recheck source caches during a manual collection")
    args = parser.parse_args()
    if args.force and not args.collect:
        parser.error("--force requires --collect")
    print(f"Static site built: {build_site(args.output, collect=args.collect, force=args.force)} public offers")
