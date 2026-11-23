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
        # New Predictions vs Reality verification: these numbers are exported
        # by an executed scientific notebook, never hardcoded in the UI.
        page.wait_for_function("() => window.CRLValidation && window.CRL_VALIDATION.rows.length===335", timeout=30000)
        evidence = page.evaluate("""() => {
          const d=window.CRL_VALIDATION,r=d.rows,s=d.scores;
          const mean=(a)=>a.reduce((x,y)=>x+y,0)/a.length;
          const brier=(p,e)=>mean(p.map((x,i)=>(x-e[i])**2));
          return {
            first:r[0].date,last:r.at(-1).date,origins:r.length,
            event10:r.reduce((a,x)=>a+x.events[0],0),
            event20:r.reduce((a,x)=>a+x.events[1],0),
            event35:r.reduce((a,x)=>a+x.events[2],0),
            markovBrier10:brier(r.map(x=>x.p.markov[0]),r.map(x=>x.events[0])),
            gbmBrier10:brier(r.map(x=>x.p.gbm[0]),r.map(x=>x.events[0])),
            ewmaBrier20:brier(r.map(x=>x.p.ewma[1]),r.map(x=>x.events[1])),
            notebookMarkov10:s["10"].models.markov.brier,
            notebookGbm10:s["10"].models.gbm.brier,
            notebookEwma20:s["20"].models.ewma.brier,
            sameOriginPrice:Math.abs(r[0].price-window.CRL_HISTORY.candles[31].close)<.01,
            bootstrap:d.bootstrap.length,
            calibrationOrigin:window.CRLCore.origin,
          };
        }""")
        assert evidence["first"]=="2025-01-01" and evidence["last"]=="2025-12-01"
        assert evidence["origins"]==335
        assert (evidence["event10"],evidence["event20"],evidence["event35"])==(62,8,0)
        assert evidence["sameOriginPrice"] and evidence["calibrationOrigin"]==93576
        for computed,expected in [
            ("markovBrier10","notebookMarkov10"),
            ("gbmBrier10","notebookGbm10"),
            ("ewmaBrier20","notebookEwma20"),
        ]:
            assert abs(evidence[computed]-evidence[expected])<1e-12, (computed,expected)
        assert evidence["bootstrap"]>=3
        assert "0.151176" in page.locator("#rvScoreTable").inner_text()
        print("PASS: 335 genuine notebook origins, 62/8/0 events, exact Brier parity", flush=True)

        page.locator('button[data-rv-threshold="20"]').click()
        assert "0.024159" in page.locator("#rvScoreTable").inner_text()
        page.locator("#rvDateSlider").evaluate(
            "(e) => {e.value=334;e.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert page.locator("#rvOrigin").inner_text()=="2025-12-01"
        assert "2025-12-31" in page.locator("#rvEnd").inner_text()
        page.locator("#rvReveal").click()
        assert "Hidden" not in page.locator("#rvFinalPrice").inner_text()
        assert "Day 30 / 30" in page.locator("#rvDayLabel").inner_text()
        final_dated_close = page.evaluate("""() => {
           const d=window.CRLValidation;
           return {expected:d.rows.at(-1).future,
                   observed:window.CRL_HISTORY.candles.at(-1).close,
                   revealed:d.state.revealDay};
        }""")
        assert abs(final_dated_close["expected"]-final_dated_close["observed"])<.01
        assert final_dated_close["revealed"]==30
        page.locator("#rvHide").click()
        assert "Hidden" in page.locator("#rvFinalPrice").inner_text()
        print("PASS: Date selector and observed 30-day price reveal/hide without lookahead", flush=True)

        # Selecting one date does not recalculate the frozen Brier figures.
        page.locator("#rvPrev").click()
        assert "0.024159" in page.locator("#rvScoreTable").inner_text()
        page.locator('button[data-rv-threshold="35"]').click()
        assert page.locator("#rvFindEvent").is_disabled()
        page.locator('button[data-rv-threshold="10"]').click()
        assert page.locator("#rvFindEvent").is_enabled()
        page.locator("#rvFindEvent").click()
        selected_loss = page.evaluate("""() => {
          const d=window.CRLValidation;return d.rows[d.state.index].events[0];
        }""")
        assert selected_loss == 1
        print("PASS: Event filtering, threshold-dependent accuracy and frozen scoring", flush=True)

        fans = page.evaluate("""() => {
           const v=window.CRLValidation,d=v.rows[v.state.index],b=v.getForecastBands(v.state.index);
           return {initial:d.price,ends:["gbm","markov","ewma"].map(m=>b[m][30]),
                   starts:["gbm","markov","ewma"].map(m=>b[m][0])};
        }""")
        for band in fans["starts"]:
            assert all(abs(q-fans["initial"])<.01 for q in band)
        for band in fans["ends"]:
            assert all(band[k]<=band[k+1] for k in range(4))
            assert all(v>0 for v in band)
        assert page.locator("#rvTimelineChart").is_visible()
        assert page.locator("#rvReplayChart").is_visible()
        page.locator("#validation").scroll_into_view_if_needed()
        page.screenshot(path="browser-verification-predictions-reality.png", full_page=False)
        print("PASS: Simulation percentile envelopes are positive, ordered and match origin", flush=True)
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(150)
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
        page.wait_for_function("n => window.CRLApp.chart.view.count < n", arg=before_zoom["count"])
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
        assert page.locator("#revealBtn").get_attribute("aria-pressed") == "true"
        page.keyboard.press("Home")
        assert page.evaluate("() => window.CRLApp.chart.view.count") < 396
        # Return the observed-candle toggle to its original hidden state before
        # testing the separate Reveal actual 2025 button below.
        page.locator("#revealBtn").click()
        assert page.locator("#revealBtn").get_attribute("aria-pressed") == "false"
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
