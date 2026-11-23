"""Browser end-to-end checks for the CryptoRisk Lab five-model scientific research terminal."""
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

        # 2026 ledger is directly sourced from the frozen audited scientific model run.
        page.wait_for_function("() => !!window.CRLHoldout2026 && !!window.CRL_EVIDENCE_2026", timeout=30000)
        five = page.evaluate("""() => {
          const core=window.CRLCore,d=window.CRLHoldout2026,models=core.models;
          const rows=d.rows,metric=d.evidence.scores;
          const brier=(m,t)=>rows.reduce((sum,r)=>sum+(r.prob[m][t]-r.events[t])**2,0)/rows.length;
          return {
            models,first:rows[0].origin,last:rows.at(-1).origin,n:rows.length,
            events:[10,20,35].map(t=>rows.reduce((s,r)=>s+r.events[t],0)),
            fixedFit:core.CAL.garch,nextVar:core.CAL.garch.nextVar,
            rollingSigma:core.adaptiveWarmStart(),
            auditedGBM:brier("gbm",10),publishedGBM:metric["10"].models.gbm.brier,
            auditedGarch:brier("garch",20),publishedGarch:metric["20"].models.garch.brier,
            publishedAdaptive:metric["10"].models.adaptive_gbm.brier,
            actualOct:d.getHistoricalClose("2026-10-31"),
            startingPrice:core.origin
          };
        }""")
        assert five["models"] == ["gbm","markov","ewma","adaptive_gbm","garch"]
        assert (five["first"],five["last"],five["n"]) == ("2026-01-01","2026-10-01",274)
        assert five["events"] == [62,38,0]
        assert abs(five["auditedGBM"]-five["publishedGBM"])<1e-10
        assert abs(five["auditedGarch"]-five["publishedGarch"])<1e-10
        assert five["publishedAdaptive"]>five["publishedGBM"]
        assert 0<five["rollingSigma"]<1 and five["startingPrice"]==93576
        assert abs(five["nextVar"]-5.547208876802669)<1e-10
        assert five["actualOct"]>0
        assert "0.175239" in page.locator("#holdoutScoreTable").inner_text()
        assert page.locator("#holdoutModelBars .v3-bar-row").count() == 6
        print("PASS: Five-model engine + 274 genuine 2026 outcomes, all loss events, exact Brier parity", flush=True)

        # Exercise a distinct historical year without modifying the original 2025 validation.
        page.evaluate("() => document.getElementById('validation2026').scrollIntoView({block:'start',behavior:'instant'})")
        page.wait_for_timeout(130)
        page.screenshot(path="browser-verification-2026-overview.png",full_page=False)
        assert page.locator("#holdoutProbabilityChart").is_visible()
        assert page.locator("#holdoutPriceChart").is_visible()
        assert "0.175239" in page.locator("#holdoutScoreTable").inner_text()
        page.locator('button[data-holdout-threshold="20"]').click()
        assert "38 actual" in page.locator("#holdoutSample").inner_text()
        page.locator('button[data-holdout-threshold="35"]').click()
        assert page.locator("#holdoutFindLoss").is_disabled()
        page.locator('button[data-holdout-threshold="10"]').click()
        assert page.locator("#holdoutFindLoss").is_enabled()
        page.locator("#holdoutFindLoss").click()
        assert page.evaluate("""() => {
          const h=window.CRLHoldout2026;return h.rows[h.state.index].events[10]===1;
        }""")
        print("PASS: 2026 threshold-dependent probabilities, loss event filtering and six-model scores", flush=True)
        page.locator("#holdoutDateSlider").evaluate(
          "(e)=>{e.value=273;e.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert page.locator("#holdoutDate").inner_text()=="2026-10-01"
        assert "2026-10-31" in page.locator("#holdoutTarget").inner_text()
        assert page.locator("#holdoutFinalPrice").inner_text()=="Hidden"
        page.locator("#holdoutReplaySlider").evaluate(
          "(e)=>{e.value=15;e.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert "Day 15 / 30" in page.locator("#holdoutDay").inner_text()
        assert page.locator("#holdoutFinalPrice").inner_text()=="Hidden"
        page.locator("#holdoutReveal").click()
        assert "Hidden" not in page.locator("#holdoutFinalPrice").inner_text()
        assert "Day 30 / 30" in page.locator("#holdoutDay").inner_text()
        actual_2026 = page.evaluate("""() => {
          const h=window.CRLHoldout2026,row=h.rows[h.state.index];
          return {day:h.state.day,close:row.future,source:h.getHistoricalClose(row.target)};
        }""")
        assert actual_2026["day"]==30
        assert abs(actual_2026["close"]-actual_2026["source"])<.011
        page.locator("#holdoutPriceChart").scroll_into_view_if_needed()
        page.screenshot(path="browser-verification-2026-replay.png",full_page=False)
        page.locator("#holdoutHide").click()
        assert page.locator("#holdoutFinalPrice").inner_text()=="Hidden"
        page.locator("#holdoutPlay").click()
        page.wait_for_function("() => window.CRLHoldout2026.state.day >= 2", timeout=7000)
        page.locator("#holdoutPlay").click()
        assert page.evaluate("() => !window.CRLHoldout2026.state.playing")
        page.locator("#holdoutHide").click()
        assert page.evaluate("() => window.CRLHoldout2026.state.day === 0")
        print("PASS: Observed 2026 daily-close replay advances, pauses and resets", flush=True)
        page.locator("#holdoutProbabilityChart").scroll_into_view_if_needed()
        page.screenshot(path="browser-verification-2026.png",full_page=False)
        assert not page.evaluate("() => !!window.CRL_EVIDENCE_2026.candles"), "Must not fabricate 2026 OHLC candles"
        assert "0.151176" in page.locator("#rvScoreTable").inner_text()
        print("PASS: 2026 observed UTC daily close replay and untouched 2025 original evaluation", flush=True)
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

        # Preserve the three original frozen notebook models while displaying
        # two independently generated post-hoc 2025 research candidates.
        extra2025=page.evaluate("""() => {
          const base=window.CRL_VALIDATION,ext=window.CRL_EXPLORATORY_2025,v=window.CRLValidation;
          const score=(m,t)=>v.rows.reduce((x,r)=>x+(r.p[m][[10,20,35].indexOf(t)]-
                       r.events[[10,20,35].indexOf(t)])**2,0)/v.rows.length;
          return {
            status:ext.meta.status,n:ext.rows.length,
            originalModels:Object.keys(base.rows[0].p).sort(),
            visibleModels:Object.keys(v.rows[0].p).sort(),
            originalMarkov:base.scores["10"].models.markov.brier,
            garch:ext.scores["10"].models.garch.brier,
            adaptive:ext.scores["10"].models.adaptive_gbm.brier,
            garchCalculated:score("garch",10),
            adaptiveCalculated:score("adaptive_gbm",10),
            firstGarch:ext.rows[0].p.garch,lastAdaptive:ext.rows.at(-1).p.adaptive_gbm,
            garchSource:ext.meta.garch_fit_source,
            actualEvents:ext.scores["10"].events,
          };
        }""")
        assert extra2025["n"]==335 and extra2025["actualEvents"]==62
        assert extra2025["originalModels"]==["ewma","gbm","historical","markov"]
        assert extra2025["visibleModels"]==["adaptive_gbm","ewma","garch","gbm","historical","markov"]
        assert "EXPLORATORY POST-HOC" in extra2025["status"]
        assert abs(extra2025["originalMarkov"]-0.15117624634268656)<1e-12
        assert abs(extra2025["garch"]-extra2025["garchCalculated"])<1e-11
        assert abs(extra2025["adaptive"]-extra2025["adaptiveCalculated"])<1e-11
        assert abs(extra2025["garch"]-0.15162250197761193)<1e-11
        assert abs(extra2025["adaptive"]-0.15491189554586093)<1e-11
        assert all(0<=x<=1 for x in extra2025["firstGarch"])
        assert all(0<=x<=1 for x in extra2025["lastAdaptive"])
        assert extra2025["garchSource"].endswith("metrics_2026.json")
        assert page.locator("#rvPredictionBars .rv-bar-row").count()==6
        assert page.locator("#rvFrequencyTable tbody tr").count()==3
        assert page.locator("#rvScoreTable tbody tr").count()==6
        assert "0.154912" in page.locator("#rvScoreTable").inner_text()
        assert "0.151623" in page.locator("#rvScoreTable").inner_text()
        assert "Post-hoc 2025 candidates" in page.locator("#rvExtensionText").inner_text()
        print("PASS: All five 2025 models, original 335-day notebook intact and separate exploratory scoring", flush=True)

        # Both added historical models must produce valid price-percentile fans,
        # anchored to the observed origin, without borrowing future actual closes.
        new_fans=page.evaluate("""() => {
           const v=window.CRLValidation,r=v.rows[0],b=v.getForecastBands(0);
           return {startingPrice:r.price,
                   models:Object.keys(b),
                   starts:["adaptive_gbm","garch"].map(m=>b[m][0]),
                   ends:["adaptive_gbm","garch"].map(m=>b[m][30])};
        }""")
        assert all(m in new_fans["models"] for m in ("adaptive_gbm","garch"))
        for arr in new_fans["starts"]:
            assert all(abs(p-new_fans["startingPrice"])<.01 for p in arr)
        for arr in new_fans["ends"]:
            assert all(0<arr[k]<=arr[k+1] for k in range(4))
            assert arr[-1]>0
        for model in ("adaptive_gbm","garch"):
            tab=page.locator(f'button[data-rv-model="{model}"]')
            tab.click()
            assert tab.get_attribute("aria-pressed")=="true"
            assert page.locator("#rvReplayChart").is_visible()
        page.locator('button[data-rv-model="all"]').click()
        print("PASS: Adaptive GBM/GARCH illustrated future-price percentile envelopes and 2025 replay tabs", flush=True)

        page.locator('button[data-rv-threshold="20"]').click()
        assert "0.024159" in page.locator("#rvScoreTable").inner_text()
        assert "0.024071" in page.locator("#rvScoreTable").inner_text()
        assert "0.024677" in page.locator("#rvScoreTable").inner_text()
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
        page.locator('button[data-rv-model="garch"]').click()
        page.screenshot(path="browser-verification-2025-garch-range.png",full_page=False)
        page.locator('button[data-rv-model="all"]').click()
        page.locator("#rvReveal").click()
        page.locator("#rvReplayChart").scroll_into_view_if_needed()
        page.screenshot(path="browser-verification-validation-replay.png", full_page=False)
        page.locator("#rvHide").click()
        print("PASS: Simulation percentile envelopes are positive, ordered and match origin", flush=True)
        page.evaluate("() => window.scrollTo({top:0,behavior:'instant'})")
        page.locator("#mainChart").scroll_into_view_if_needed()
        page.wait_for_timeout(100)
        # Verify the price-level crosshair numerically, not merely the OHLC tooltip.
        box = page.locator("#mainChart").bounding_box()
        assert box is not None
        hover_x, hover_y = box["width"] * .59, box["height"] * .44
        page.locator("#mainChart").hover(position={"x": hover_x, "y": hover_y})
        box = page.locator("#mainChart").bounding_box()  # Hover can change scroll position
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
        assert page.evaluate("() => window.CRLApp.result.models.adaptive_gbm.n") == 1000
        assert page.evaluate("() => window.CRLApp.result.models.garch.n") == 1000
        assert "%" in page.locator("#kpiAdaptive").inner_text()
        assert "%" in page.locator("#kpiGarch").inner_text()
        assert page.locator("#riskTable [data-model='adaptive_gbm'][data-metric='p10']").inner_text().endswith("%")
        assert page.locator("#riskTable [data-model='garch'][data-metric='p10']").inner_text().endswith("%")
        table_fits=page.evaluate("""() => {
          const tbl=document.querySelector("#riskTable"),outer=tbl.closest(".table-scroll");
          return tbl.getBoundingClientRect().width <= outer.getBoundingClientRect().width + 2;
        }""")
        assert table_fits, "Five-model research risk table overflows desktop comparison card"

        first_new = {model: page.evaluate(f"() => window.CRLApp.result.models['{model}'].prob['0.100'].p")
                     for model in ("gbm","markov","ewma","adaptive_gbm","garch")}

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
        for model,expected in first_new.items():
            observed=page.evaluate(f"() => window.CRLApp.result.models['{model}'].prob['0.100'].p")
            assert observed == expected, "Seeded five-model scenario changed for "+model

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
        page.evaluate("() => window.scrollTo({top:0,behavior:'instant'})")
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
