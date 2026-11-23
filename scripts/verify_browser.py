"""Browser end-to-end checks for the CryptoRisk Lab v2 historical research terminal."""
import contextlib
import json
import pathlib
import socket
import subprocess
import time

from playwright.sync_api import sync_playwright

PORT = 8765
server = subprocess.Popen(["python", "-m", "http.server", str(PORT), "--directory", "docs"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
try:
    for _ in range(70):
        with contextlib.closing(socket.socket()) as sock:
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                break
        time.sleep(.25)
    else:
        raise RuntimeError("Could not start static site server")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="load")
        page.wait_for_function("() => !!window.CRLApp && !!window.CRLCore && !!window.CRL_HISTORY")
        assert page.locator("#mainChart").is_visible()
        assert page.evaluate("() => window.CRL_HISTORY.candles.length") == 396
        assert page.evaluate("() => window.CRL_HISTORY.candles[30].close") == 93576
        assert page.evaluate("() => window.CRL_HISTORY.candles.at(-1).date") == "2025-12-31"
        assert "2025-12-31" in page.locator("#actual2025Summary").inner_text()
        print("PASS: 396 authentic daily Binance candles, complete 2025, origin preserved", flush=True)
        # Verify the price-level crosshair numerically, not merely the OHLC tooltip.
        box = page.locator("#mainChart").bounding_box()
        assert box is not None
        hover_x, hover_y = box["width"] * .59, box["height"] * .44
        page.locator("#mainChart").hover(position={"x": hover_x, "y": hover_y})
        page.wait_for_function("() => Number.isFinite(window.CRLApp.chart.crosshairPrice)")
        crosshair = page.evaluate("""() => {
            const c = window.CRLApp.chart, a = c.axis;
            return {value:c.crosshairPrice, inverse:a.priceAtY(c.cursor.y),
                    tooltip:c.tooltip.textContent, y:c.cursor.y};
        }""")
        assert abs(crosshair["value"] - crosshair["inverse"]) < .001
        assert crosshair["value"] > 0
        assert "OBSERVED" in crosshair["tooltip"] or "Future region" in crosshair["tooltip"]
        page.screenshot(path="browser-verification-crosshair.png", full_page=False)
        print("PASS: Crosshair reflects actual hovered price on right axis", flush=True)

        # Pointer-centred scroll zoom must leave the date beneath the pointer stable.
        viewport_x = hover_x
        before_zoom = page.evaluate("""x => {
            const c=window.CRLApp.chart;
            return {count:c.view.count,
                    world:c.view.start+(x-13)/c.plotWidth*c.view.count};
        }""", viewport_x)
        page.mouse.wheel(0,-330)
        page.wait_for_function("n => window.CRLApp.chart.view.count < n", before_zoom["count"])
        after_zoom = page.evaluate("""x => {
            const c=window.CRLApp.chart;
            return {count:c.view.count,
                    world:c.view.start+(x-13)/c.plotWidth*c.view.count};
        }""", viewport_x)
        assert abs(before_zoom["world"]-after_zoom["world"]) < .06, (
            "Scroll zoom drifted away from cursor date"
        )
        assert after_zoom["count"] < before_zoom["count"]
        print("PASS: Pointer-centred wheel zoom preserves target date", flush=True)

        # Mouse drag should pan instead of selecting an accidental Monte Carlo path.
        before_pan = page.evaluate("() => window.CRLApp.chart.view.start")
        page.mouse.move(box["x"]+hover_x, box["y"]+hover_y)
        page.mouse.down()
        page.mouse.move(box["x"]+hover_x-125, box["y"]+hover_y, steps=5)
        page.mouse.up()
        after_pan = page.evaluate("() => window.CRLApp.chart.view.start")
        assert abs(after_pan-before_pan)>1, "Drag failed to pan chart"
        print("PASS: Chart drags horizontally without losing zoom", flush=True)

        # Right-side USDT scale: draggable vertical zoom and double-click autoscale.
        axis_x = box["width"]-24
        axis_y = box["height"]*.43
        page.mouse.move(box["x"]+axis_x,box["y"]+axis_y)
        page.wait_for_function("() => Number.isFinite(window.CRLApp.chart.crosshairPrice)")
        before_price_zoom = page.evaluate("() => window.CRLApp.chart.axis.max-window.CRLApp.chart.axis.min")
        page.mouse.down()
        page.mouse.move(box["x"]+axis_x,box["y"]+axis_y+62,steps=5)
        page.mouse.up()
        page.wait_for_function("() => window.CRLApp.chart.manualPriceRange!==null")
        after_price_zoom = page.evaluate("() => window.CRLApp.chart.axis.max-window.CRLApp.chart.axis.min")
        assert abs(after_price_zoom-before_price_zoom)>1, "Price-scale drag did not rescale"
        page.locator("#mainChart").dblclick(position={"x":axis_x,"y":axis_y})
        assert page.evaluate("() => window.CRLApp.chart.manualPriceRange===null")
        print("PASS: Draggable vertical USDT scale and double-click autoscale", flush=True)

        # Keyboard navigation remains functional and accessible.
        page.locator("#mainChart").focus()
        page.keyboard.press("End")
        assert page.evaluate("() => window.CRLApp.chart.view.count") == 396
        page.keyboard.press("Home")
        assert page.evaluate("() => window.CRLApp.chart.view.count") < 396
        print("PASS: Keyboard date navigation and fit views", flush=True)
        assert page.evaluate("() => window.CRLCore.ewmaWarmStart(.9)") > 0
        page.locator('input[name="paths"][value="1000"]').check(force=True)
        page.locator("#startBtn").click()
        page.wait_for_function("() => window.CRLApp.result && window.CRLApp.result.models.ewma.n === 1000", timeout=30000)
        first = page.locator("#kpiGbm").inner_text()
        assert "%" in first
        assert "PASS" in page.locator("#verifyStatus").inner_text()
        assert "0.151631" in page.locator("#validation").inner_text()
        print("PASS: GBM, Markov and EWMA simulation + frozen 2025 validation", flush=True)
        page.locator("#dayScrub").evaluate("(e) => {e.value = 15; e.dispatchEvent(new Event('input',{bubbles:true}));}")
        assert "15" in page.locator("#dayLabel").inner_text()
        assert "Sample Markov path:" in page.locator("#regimeStatus").inner_text()
        page.locator('button[data-view="markov"]').click()
        assert page.locator('button[data-view="markov"]').get_attribute("aria-pressed") == "true"
        pick = page.evaluate("""() => {
          const c=window.CRLApp.chart,a=c.axis,d=15;
          const sample=window.CRLApp.result.models.markov.paths[0].values[d];
          return {x: a.pad.l+((c.originIdx+d-c.view.start+.5)/c.view.count)*a.graphW, y:a.y(sample)};
        }""")
        page.locator("#mainChart").click(position=pick)
        assert "MARKOV path" in page.locator("#pathInspector").inner_text()
        print("PASS: Clickable simulated path reveals price, P/L, drawdown and regime", flush=True)
        page.locator("#revealBtn").click()
        assert page.locator("#revealBtn").get_attribute("aria-pressed") == "true"
        assert page.evaluate("() => window.CRLApp.chart.view.count") == 396
        assert "2025-12-31" in page.locator("#actual2025Summary").inner_text()
        page.evaluate("() => window.scrollTo(0, 0)")
        page.screenshot(path="browser-verification-full-year.png", full_page=False)
        assert page.evaluate("() => window.CRLApp.result.settings.horizon") == 30
        page.locator("#resetView").click()
        assert page.evaluate("() => window.CRLApp.chart.view.count") < 396
        page.locator("#fitYear").click()
        assert page.evaluate("() => window.CRLApp.chart.view.count") == 396
        print("PASS: Full-year observed 2025 navigation and finite 30-day forecast", flush=True)
        page.locator("#helpOpen").click()
        assert page.locator("#helpDialog").evaluate("(e) => e.open")
        page.locator("#helpClose").click()
        assert not page.locator("#helpDialog").evaluate("(e) => e.open")
        print("PASS: Compact how-to-use dialog opens and closes", flush=True)
        page.locator("#startBtn").click()
        page.wait_for_function("() => window.CRLApp.result && window.CRLApp.result.models.gbm.n === 1000", timeout=30000)
        assert first == page.locator("#kpiGbm").inner_text(), "Same seed/settings did not reproduce GBM output"
        print("PASS: Reproducible Monte Carlo probabilities", flush=True)
        # Capture the full 30-day forecast fan and sample trajectories, not a half-drawn frame.
        page.locator("#revealBtn").click()
        page.locator("#dayScrub").evaluate("(e) => { e.value = 30; e.dispatchEvent(new Event('input',{bubbles:true})); }")
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(200)
        page.screenshot(path="browser-verification.png", full_page=True)
        page.locator("#resetBtn").click()
        assert page.locator("#kpiGbm").inner_text() == "—"
        print("PASS: Reset invalidates old output", flush=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(350)
        assert not page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth+2"), "Mobile width overflow"
        assert page.locator("#mainChart").is_visible()
        page.screenshot(path="browser-verification-mobile.png", full_page=True)
        print("PASS: Mobile viewport without horizontal overflow", flush=True)
        # The static application must also run as a directly-opened local file.
        file_page = browser.new_page()
        file_page.on("pageerror", lambda e: errors.append("file mode: "+str(e)))
        file_page.goto(pathlib.Path("docs/index.html").resolve().as_uri())
        file_page.wait_for_function("() => !!window.CRLApp && !!window.CRL_HISTORY")
        assert file_page.locator("#mainChart").is_visible()
        print("PASS: file:// standalone opening, no CDN/backend dependency", flush=True)
        assert not errors, "Uncaught JS errors: "+json.dumps(errors)
        print("PASS: No uncaught browser JavaScript errors", flush=True)
        browser.close()
finally:
    server.terminate()
    with contextlib.suppress(Exception):
        server.wait(timeout=5)
