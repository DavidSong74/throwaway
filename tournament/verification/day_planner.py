"""Standalone browser acceptance checks. Run inside Daytona for generated pages."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def verify(source, output, baseline=False):
    from playwright.sync_api import sync_playwright, expect

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name in ("checks.json", "desktop.png", "mobile.png", "failure.png"):
        (output / name).unlink(missing_ok=True)
    html = Path(source).read_text(encoding="utf-8")
    names = ["startup", "create_and_priority", "fixed_time_and_breaks", "complete_undo_delete",
             "persistence", "invalid_day", "clear_confirmation", "mobile"]
    if not baseline:
        names += ["search", "combined_status_filters", "no_matches", "schedule_unchanged", "filter_after_rerender"]
    checks = {name: {"status": "not_run"} for name in names}
    errors = []
    context = page = browser = None
    current = None

    def check(name, fn):
        nonlocal current
        current = name
        fn()
        checks[name] = {"status": "passed"}

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1280, "height": 900}, service_workers="block")
            page = context.new_page()
            page.set_default_timeout(5000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            # Offline origin gives localStorage a stable origin; no remote assets or requests allowed.
            page.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body=html)
                       if route.request.url == "http://day-planner.test/" else route.abort())
            page.goto("http://day-planner.test/", wait_until="domcontentloaded")

            def add(title, minutes=45, priority="2", fixed=""):
                page.locator("#t").fill(title)
                page.locator("#d").fill(str(minutes))
                page.locator("#p").select_option(priority)
                page.locator("#f").fill(fixed)
                page.locator("#add").click()

            def blocks():
                return page.locator("#tl .blk")

            def block(title):
                return blocks().filter(has=page.locator("b", has_text=title))

            def titles():
                return [b.inner_text() for b in page.locator("#tl .blk:visible b").all()]

            def startup():
                expect(page).to_have_title("Day Planner")
                expect(page.locator("#add")).to_be_visible()
                assert not errors, errors
            check("startup", startup)

            def priority():
                add("Low errands", 30, "1")
                add("CALCULUS study", 45, "3")
                add("Read history", 30, "2")
                expect(blocks()).to_have_count(3)
                assert titles() == ["CALCULUS study", "Read history", "Low errands"], titles()
            check("create_and_priority", priority)

            def schedule():
                add("Fixed meeting", 30, "2", "10:00")
                expect(block("Fixed meeting").locator("small")).to_contain_text("10:00")
                expect(block("Read history").locator("small")).to_contain_text("08:50")
                page.locator("#g").fill("10")
                page.locator("#g").dispatch_event("change")
                expect(block("Read history").locator("small")).to_contain_text("08:55")
            check("fixed_time_and_breaks", schedule)

            def actions():
                block("Low errands").get_by_role("button", name="Mark done", exact=True).click()
                expect(page.locator("#done li")).to_contain_text("Low errands")
                page.locator("#done li").get_by_role("button", name="Undo", exact=True).click()
                expect(block("Low errands")).to_have_count(1)
                block("Low errands").get_by_role("button", name="Mark done", exact=True).click()
                block("Read history").get_by_role("button", name="Delete", exact=True).click()
                expect(block("Read history")).to_have_count(0)
            check("complete_undo_delete", actions)

            def persistence():
                page.reload(wait_until="domcontentloaded")
                expect(block("CALCULUS study")).to_have_count(1)
                expect(page.locator("#done li")).to_contain_text("Low errands")
                expect(page.locator("#g")).to_have_value("10")
                stored = page.evaluate("JSON.parse(localStorage.getItem('dayplanner.v1'))")
                assert len(stored["tasks"]) == 3
            check("persistence", persistence)

            if not baseline:
                def search():
                    page.locator("#search").fill("calculus")
                    expect(page.locator("#tl .blk:visible b")).to_have_text(["CALCULUS study"])
                    expect(page.locator("#done li:visible")).to_have_count(0)
                check("search", search)

                def combined():
                    page.locator("#search").fill("")
                    page.locator("#status").select_option("done")
                    expect(page.locator("#tl .blk:visible")).to_have_count(0)
                    expect(page.locator("#done li:visible")).to_have_count(1)
                    page.locator("#search").fill("ERRANDS")
                    expect(page.locator("#done li:visible")).to_contain_text("Low errands")
                    page.locator("#status").select_option("open")
                    expect(page.locator("#done li:visible")).to_have_count(0)
                    expect(page.locator("#tl .blk:visible")).to_have_count(0)
                    page.locator("#status").select_option("all")
                    expect(page.locator("#done li:visible")).to_have_count(1)
                check("combined_status_filters", combined)

                def no_matches():
                    page.locator("#search").fill("no-task-matches-this-query")
                    expect(page.locator("#filter-empty")).to_be_visible()
                    assert page.locator("#filter-empty").inner_text().strip()
                check("no_matches", no_matches)

                def unchanged():
                    page.locator("#search").fill("")
                    add("Another flexible task", 30, "1")
                    before = block("Another flexible task").locator("small").inner_text()
                    page.locator("#search").fill("Another flexible")
                    expect(block("Another flexible task").locator("small")).to_have_text(before)
                    expect(page.locator("#filter-empty")).not_to_be_visible()
                check("schedule_unchanged", unchanged)

                def rerender():
                    page.locator("#search").fill("calculus")
                    page.locator("#status").select_option("open")
                    block("CALCULUS study").get_by_role("button", name="Mark done", exact=True).click()
                    expect(page.locator("#tl .blk:visible")).to_have_count(0)
                    expect(page.locator("#done li:visible")).to_have_count(0)
                    page.locator("#status").select_option("done")
                    expect(page.locator("#done li:visible")).to_have_count(1)
                    page.reload(wait_until="domcontentloaded")
                    # Whether filter preferences persist is optional; the controls must still work.
                    page.locator("#search").fill("CALCULUS")
                    page.locator("#status").select_option("done")
                    expect(page.locator("#done li:visible")).to_have_count(1)
                    page.locator("#search").fill("")
                    page.locator("#status").select_option("all")
                check("filter_after_rerender", rerender)

            def invalid():
                page.locator("#e").fill("07:00")
                page.locator("#e").dispatch_event("change")
                expect(blocks()).to_have_count(0)
                assert page.locator("#tl").inner_text().strip(), "Invalid day needs an explanatory message"
                page.locator("#e").fill("20:00")
                page.locator("#e").dispatch_event("change")
            check("invalid_day", invalid)

            page.screenshot(path=str(output / "desktop.png"), full_page=True)

            def mobile():
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                for selector in (["#t", "#add"] + ([] if baseline else ["#search", "#status"])):
                    control = page.locator(selector)
                    expect(control).to_be_visible()
                    box = control.bounding_box()
                    assert box and box["x"] >= 0 and box["x"] + box["width"] <= 391
                page.screenshot(path=str(output / "mobile.png"), full_page=True)
            check("mobile", mobile)

            def clear():
                page.once("dialog", lambda dialog: dialog.dismiss())
                page.locator("#clr").click()
                assert page.evaluate("JSON.parse(localStorage.getItem('dayplanner.v1')).tasks.length") > 0
                page.once("dialog", lambda dialog: dialog.accept())
                page.locator("#clr").click()
                expect(blocks()).to_have_count(0)
                expect(page.locator("#done li")).to_have_count(0)
                assert page.evaluate("JSON.parse(localStorage.getItem('dayplanner.v1')).tasks.length") == 0
                assert not errors, errors
            check("clear_confirmation", clear)
        except Exception as error:
            if current:
                checks[current] = {"status": "failed", "error": str(error)[-3000:]}
            else:
                checks["startup"] = {"status": "infrastructure_error", "error": str(error)[-3000:]}
            if page:
                try:
                    page.screenshot(path=str(output / "failure.png"), full_page=True, timeout=5000)
                except Exception:
                    pass
        finally:
            if browser:
                browser.close()
    report = {"profile": "baseline" if baseline else "day_planner",
              "source_sha256": hashlib.sha256(html.encode()).hexdigest(),
              "checks": checks, "page_errors": errors}
    (output / "checks.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    report = verify(args.file, args.output, args.baseline)
    print(json.dumps(report, indent=2))
    return 0 if all(check["status"] == "passed" for check in report["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
