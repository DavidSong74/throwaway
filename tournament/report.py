"""Passive local review page: captured evidence and explicit links, no generated scripts."""
from html import escape
import json
from pathlib import Path
import re


def build_report(directory):
    directory = Path(directory)
    results = json.loads((directory / "summary.json").read_text())
    task = json.loads((directory / "task.json").read_text())
    cards = []
    for result in results:
        name = result["candidate"]
        if not re.fullmatch(r"candidate-\d+", name):
            raise ValueError("Invalid candidate ID in report")
        candidate = directory / name
        checks_file = candidate / "checks.json"
        details = ""
        if checks_file.exists():
            checks = json.loads(checks_file.read_text()).get("checks", {})
            passed = sum(c.get("status") == "passed" for c in checks.values())
            details = f"<p>{passed} / {len(checks)} captured checks passed</p><ul>"
            details += "".join(f"<li>{escape(k.replace('_', ' '))}: <strong>{escape(c['status'])}</strong></li>"
                               for k, c in checks.items()) + "</ul>"
        links = []
        artifacts = [("proposed_file.html", "Open candidate HTML"), ("changes.diff", "View patch"),
                     ("checks.json", "Check report"), ("result.json", "Run record"),
                     ("baseline-checks.json", "Baseline checks"),
                     ("attempt-1.log", "Attempt 1 log"), ("attempt-2.log", "Attempt 2 log"),
                     ("infrastructure.log", "Infrastructure log")]
        for file, label in artifacts:
            if (candidate / file).exists():
                links.append(f'<a href="{name}/{file}" target="_blank" rel="noopener noreferrer">{label}</a>')
        images = "".join(f'<figure><figcaption>{label}</figcaption><a href="{name}/{file}">'
                         f'<img src="{name}/{file}" alt="{label} of {name}" loading="lazy"></a></figure>'
                         for file, label in [("desktop.png", "Desktop"), ("mobile.png", "Mobile"),
                                              ("failure.png", "Failure state")]
                         if (candidate / file).exists())
        status = result["status"]
        cards.append(f'<section><h2>{escape(name)}</h2><p class="status">{escape(status)}</p>'
                     f'<p>Model: {escape(result["model"])}</p>'
                     f'<p>Cleanup: {escape(result["cleanup"])}</p>' + details +
                     '<nav>' + "".join(links) + '</nav>' + images + '</section>')
    html = '''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Day Planner comparison</title>
<style>body{font:16px/1.5 system-ui,sans-serif;margin:0;background:#f4f5f7;color:#17202b}
main{max-width:1440px;margin:auto;padding:28px}h1{margin:0;font-size:26px}h2{margin-top:0}
.lead{max-width:900px}code{overflow-wrap:anywhere}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:24px;margin-top:24px}
section{padding:22px;background:white;border:1px solid #d7dce1;border-radius:12px;min-width:0}
.status{font-weight:700}nav{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}a{color:#1648a0}
figure{margin:20px 0}img{display:block;max-width:100%;height:auto;border:1px solid #d7dce1}
figcaption{font-weight:600;margin-bottom:6px}li{margin:4px 0}</style></head><body><main>
<h1>Day Planner comparison</h1><p class="lead">Real candidate files and captured verification.
No implementation is selected or merged automatically. Open each candidate manually;
use separate browser profiles for independent storage when testing exported HTML.</p>'''
    html += f'<p>Baseline: <code>{escape(task["base_sha"])}</code></p>'
    html += '<details><summary>Shared request</summary><p>' + escape(task["request"]) + '</p></details>'
    html += '<div class="grid">' + ''.join(cards) + '</div></main></body></html>'
    output = directory / "review.html"
    output.write_text(html, encoding="utf-8")
    return output
