"""End-to-end scientific browser audit for five-horizon CryptoRisk Lab v5.

Verifies all five archived models, 2025 original notebook parity, the
post-hoc 2025 candidate extensions, untouched independent 2026 validation,
single-year selector, replay controls, simulation reproducibility and mobile.
"""
import contextlib
import json
import pathlib
import socket
import subprocess
import time

from playwright.sync_api import sync_playwright

PORT=8765
server=subprocess.Popen(["python","-m","http.server",str(PORT),"--directory","docs"],
                       stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
try:
    for _ in range(80):
        with contextlib.closing(socket.socket()) as sock:
            if sock.connect_ex(("127.0.0.1",PORT))==0:break
        time.sleep(.25)
    else:raise RuntimeError("Unable to launch static docs server")
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1440,"height":980},device_scale_factor=1)
        errors=[]
        page.on("pageerror",lambda e:errors.append("page exception: "+str(e)))
        page.on("console",lambda msg:errors.append("browser console: "+msg.text) if msg.type=="error" else None)
        page.goto(f"http://127.0.0.1:{PORT}/index.html",wait_until="load")
        page.wait_for_function("() => !!window.CRLValidationUnified && !!window.CRLApp && !!window.CRLCore",
                               timeout=30000)
        assert page.locator("#mainChart").is_visible()
        assert page.locator("#validation").count()==1
        assert page.locator("#validation2026").count()==0
        assert page.locator("[data-validation-year]").count()==2
        assert page.locator("#rvOrigin").count()==0, "Legacy duplicate year-specific dashboard remains"
        assert page.evaluate("() => window.CRLCore.origin")==93576
        assert page.evaluate("() => window.CRL_HISTORY.candles.length")==396
        print("PASS: Single five-model historical dashboard, original BTC candles and scientific simulation preserved",flush=True)

        original=page.evaluate("""() => {
            const org=window.CRL_VALIDATION, unified=window.CRLValidationUnified.getYearEvidence(2025);
            const models=["historical","gbm","markov","ewma"];
            return {origins:org.rows.length,extended:unified.rows.length,
              unchanged:org.rows.every((r,i)=>models.every(m=>[10,20,35].every((t,j)=>
                r.p[m][j]===unified.rows[i].prob[m][t]))),
              first:unified.rows[0].origin,last:unified.rows.at(-1).origin,
              eventCounts:[10,20,35].map(t=>unified.rows.reduce((s,r)=>s+r.events[t],0)),
              scores:unified.data.scores,
              deltaGarch:unified.data.scores["10"].models.garch.brier,
              deltaAdaptive:unified.data.scores["10"].models.adaptive_gbm.brier};
        }""")
        assert original["origins"]==original["extended"]==335
        assert original["unchanged"]
        assert (original["first"],original["last"])==("2025-01-01","2025-12-01")
        assert original["eventCounts"]==[62,8,0]
        assert abs(original["deltaGarch"]-0.151766)<1e-6
        assert abs(original["deltaAdaptive"]-0.154912)<1e-6
        assert "0.151766" in page.locator("#holdoutScoreTable").inner_text()
        assert "Exploratory" in page.locator("#holdoutInferenceTable").inner_text()
        assert "post-hoc" in page.locator("#validationYearStatus").inner_text()
        assert page.locator("#holdoutModelBars .v3-bar-row").count()==6
        print("PASS: 335 original 2025 dates, all preserved notebook probabilities and two authentic exploratory added models",flush=True)

        page.evaluate("() => document.querySelector('#validation').scrollIntoView({block:'start',behavior:'instant'})")
        page.wait_for_timeout(150)
        page.screenshot(path="browser-verification-selector-2025.png",full_page=False)
        page.locator("#holdoutProbabilityChart").scroll_into_view_if_needed()
        page.screenshot(path="browser-verification-unified-2025.png",full_page=False)
        page.locator('button[data-holdout-threshold="20"]').click()
        assert "8 actual" in page.locator("#holdoutSample").inner_text()
        assert "≥20%" in page.locator("#holdoutEventLabel").inner_text()
        assert "≥20%" in page.locator("#holdoutBestLabel").inner_text()
        assert "8 / 335" in page.locator("#holdoutEventHeadline").inner_text()
        page.locator('button[data-holdout-threshold="35"]').click()
        assert page.locator("#holdoutFindLoss").is_disabled()
        page.locator('button[data-holdout-threshold="10"]').click()
        assert page.locator("#holdoutFindLoss").is_enabled()
        page.locator("#holdoutFindLoss").click()
        assert page.evaluate("() => window.CRLValidationUnified.rows[window.CRLValidationUnified.state.index].events[10]") == 1
        page.locator("#holdoutDateSlider").evaluate(
            "(e)=>{e.value=334;e.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert page.locator("#holdoutDate").inner_text()=="2025-12-01"
        assert "2025-12-31" in page.locator("#holdoutTarget").inner_text()
        assert page.locator("#holdoutFinalPrice").inner_text()=="Hidden"
        page.locator("#holdoutReveal").click()
        assert "Hidden" not in page.locator("#holdoutFinalPrice").inner_text()
        assert page.evaluate("""() => {
            const d=window.CRLValidationUnified,r=d.rows.at(-1);
            return Math.abs(d.getHistoricalClose(r.target)-r.future)<.01;
        }""")
        page.locator("#holdoutHide").click()
        assert page.locator("#holdoutFinalPrice").inner_text()=="Hidden"
        print("PASS: 2025 date selector, loss-event finder and real observed 30-day replay",flush=True)

        page.locator('[data-validation-year="2026"]').click()
        page.wait_for_function("() => window.CRLValidationUnified.state.year===2026")
        assert page.locator('[data-validation-year="2026"]').get_attribute("aria-pressed")=="true"
        assert page.locator('[data-validation-year="2025"]').get_attribute("aria-pressed")=="false"
        assert page.locator("#holdoutDate").inner_text()=="2026-01-01"
        assert page.locator("#holdoutDateSlider").get_attribute("max")=="273"
        assert "274 forecasts" in page.locator("#validationPeriodDates").inner_text()
        assert "0.175239" in page.locator("#holdoutScoreTable").inner_text()
        page.evaluate("() => document.querySelector('#validation').scrollIntoView({block:'start',behavior:'instant'})")
        page.wait_for_timeout(150)
        page.screenshot(path="browser-verification-selector-2026.png",full_page=False)
        assert "0.4339" in page.locator("#holdoutInferenceTable").inner_text()
        assert "Holm" in page.locator("#holdoutInferenceContext").inner_text()
        assert page.evaluate("""() => {
          const h=window.CRLValidationUnified;
          return h.rows.length===274&&h.rows[0].origin==="2026-01-01"&&
                 h.rows.at(-1).origin==="2026-10-01";
        }""")
        page.locator('button[data-holdout-threshold="20"]').click()
        assert "38 actual" in page.locator("#holdoutSample").inner_text()
        page.locator('button[data-holdout-threshold="35"]').click()
        assert page.locator("#holdoutFindLoss").is_disabled()
        page.locator('button[data-holdout-threshold="10"]').click()
        page.screenshot(path="browser-verification-unified-2026.png",full_page=False)
        page.locator("#holdoutDateSlider").evaluate(
            "(e)=>{e.value=273;e.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert page.locator("#holdoutDate").inner_text()=="2026-10-01"
        assert "2026-10-31" in page.locator("#holdoutTarget").inner_text()
        page.locator("#holdoutReplaySlider").evaluate(
            "(e)=>{e.value=15;e.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert "Day 15 / 30" in page.locator("#holdoutDay").inner_text()
        assert page.locator("#holdoutFinalPrice").inner_text()=="Hidden"
        page.locator("#holdoutReveal").click()
        assert "Hidden" not in page.locator("#holdoutFinalPrice").inner_text()
        assert page.evaluate("""() => {
          const h=window.CRLValidationUnified,r=h.rows[h.state.index];
          return h.state.day===30&&Math.abs(h.getHistoricalClose(r.target)-r.future)<.01;
        }""")
        page.locator("#holdoutPriceChart").scroll_into_view_if_needed()
        page.screenshot(path="browser-verification-unified-replay.png",full_page=False)
        page.locator("#holdoutHide").click()
        assert page.locator("#holdoutFinalPrice").inner_text()=="Hidden"
        print("PASS: Switching to 2026 updates 274 dates, model scores, uncertainty, event filtering and observed-close replay",flush=True)

        page.locator('[data-validation-year="2025"]').click()
        assert page.locator("#holdoutDate").inner_text()=="2025-01-01"
        assert page.locator("#holdoutDateSlider").get_attribute("max")=="334"
        assert "0.150874" in page.locator("#holdoutScoreTable").inner_text()
        assert "0.151766" in page.locator("#holdoutScoreTable").inner_text()
        assert "Exploratory" in page.locator("#holdoutInferenceTable").inner_text()
        assert page.locator("#holdoutFinalPrice").inner_text()=="Hidden"
        print("PASS: Bidirectional 2025/2026 year switching maintains correct model and research provenance",flush=True)


        # Each historical forecast horizon must be backed by its own genuine
        # completed-outcome observations, never derived from the 30-day scores.
        counts={2025:{7:358,14:351,30:335,60:305,90:275},
                2026:{7:297,14:290,30:274,60:244,90:214}}
        for year in (2025,2026):
            page.locator(f'[data-validation-year="{year}"]').click()
            for h in (7,14,30,60,90):
                page.locator(f'[data-validation-horizon="{h}"]').click()
                evidence=page.evaluate("""() => {
                    const a=window.CRLValidationUnified;
                    const d=a.evidence,rs=a.rows,t=a.state.threshold;
                    return {year:a.state.year,horizon:a.state.horizon,n:rs.length,
                      actualLast:rs.at(-1).target,first:rs[0].origin,
                      valid:rs.every(r=>(Date.parse(r.target)-Date.parse(r.origin))===a.state.horizon*86400000),
                      eventCount:rs.reduce((s,r)=>s+r.events[t],0),
                      sourceEventCount:d.scores[String(t)].events,
                      score:d.scores["10"].models.gbm.brier,
                      firstPrice:rs[0].close,sourceForecast:rs[0].prob.garch[10],
                      replayMax:document.getElementById("holdoutReplaySlider").max,
                      simHorizon:Number(document.getElementById("horizon").value),
                      exploratory:document.getElementById("holdoutInferenceTable").textContent.includes("Exploratory")};
                }""")
                assert evidence["n"]==counts[year][h],evidence
                assert str(counts[2025][h]) in page.locator('[data-validation-year="2025"] span').inner_text()
                assert str(counts[2026][h]) in page.locator('[data-validation-year="2026"] span').inner_text()
                assert evidence["year"]==year and evidence["horizon"]==h
                assert evidence["first"]==f"{year}-01-01"
                assert evidence["actualLast"]==("2025-12-31" if year==2025 else "2026-10-31")
                assert evidence["valid"] and evidence["eventCount"]==evidence["sourceEventCount"]
                assert evidence["replayMax"]==str(h)
                assert evidence["simHorizon"]==h
                assert 0<=evidence["sourceForecast"]<=1
                if h!=30:assert evidence["exploratory"], "Exploratory horizons must not claim Holm inference"
                if year==2025 and h==30:assert "0.150874" in page.locator("#holdoutScoreTable").inner_text()
                if year==2026 and h==30:assert "0.175239" in page.locator("#holdoutScoreTable").inner_text()
                if (year,h) in ((2025,7),(2026,90)):
                    page.evaluate("() => document.querySelector('#validation').scrollIntoView({block:'start',behavior:'instant'})")
                    page.wait_for_timeout(120)
                    page.screenshot(path=f"browser-verification-{year}-h{h}.png",full_page=False)
                    page.locator("#holdoutDateSlider").evaluate(
                        "(e)=>{e.value=e.max;e.dispatchEvent(new Event('input',{bubbles:true}));}"
                    )
                    assert page.locator("#holdoutFinalPrice").inner_text()=="Hidden"
                    page.locator("#holdoutReveal").click()
                    assert f"Day {h} / {h}" in page.locator("#holdoutDay").inner_text()
                    assert page.locator("#holdoutFinalPrice").inner_text()!="Hidden"
                    assert page.evaluate("""() => {
                      const a=window.CRLValidationUnified,r=a.rows[a.state.index];
                      return Math.abs(a.getHistoricalClose(r.target)-r.future)<.01;
                    }""")
                    page.locator("#holdoutHide").click()
            print(f"PASS: {year} five 7–90d horizons, score parity, horizon selection and exact historical H-day outcomes",flush=True)

        # Unsupported custom simulator durations must not silently be presented
        # as historical forecasts of another duration.
        page.locator('[data-validation-year="2025"]').click()
        page.locator('[data-validation-horizon="30"]').click()
        page.locator("#horizon").evaluate(
            "(e)=>{e.value=18;e.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert page.evaluate("() => window.CRLValidationUnified.state.horizon")==30
        assert "No audited historical backtest exists" in page.locator("#validationHorizonSync").inner_text()
        assert page.locator("#validationHorizonSync").get_attribute("data-mismatch")=="true"
        page.locator("#horizonNumber").evaluate(
            "(e)=>{e.value=14;e.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert page.evaluate("() => window.CRLValidationUnified.state.horizon")==14
        assert page.locator('[data-validation-horizon="14"]').get_attribute("aria-pressed")=="true"
        page.locator('[data-validation-horizon="30"]').click()
        assert page.evaluate("() => Number(document.getElementById('horizon').value)===30")
        assert page.locator("#validationHorizonSync").get_attribute("data-mismatch")=="false"
        print("PASS: Exact simulation horizon synchronization and explicit custom-horizon incompatibility warning",flush=True)
        # Original trading-style simulation must remain independent and reproducible.
        page.locator("#mainChart").scroll_into_view_if_needed()
        page.locator('input[name="paths"][value="1000"]').check(force=True)
        page.locator("#startBtn").click()
        page.wait_for_function("() => window.CRLApp.result && window.CRLApp.result.models.garch.n===1000",timeout=30000)
        assert page.evaluate("() => window.CRLCore.models.length")==5
        assert "PASS" in page.locator("#verifyStatus").inner_text()
        initial=page.evaluate("""() => Object.fromEntries(window.CRLCore.models.map(m=>
         [m,window.CRLApp.result.models[m].prob["0.100"].p]))""")
        for model in ("gbm","markov","ewma","adaptive_gbm","garch"):
            assert "%" in page.locator("#kpi"+{"gbm":"Gbm","markov":"Markov","ewma":"Ewma",
                                            "adaptive_gbm":"Adaptive","garch":"Garch"}[model]).inner_text()
        page.locator('button[data-view="garch"]').click()
        assert page.locator('button[data-view="garch"]').get_attribute("aria-pressed")=="true"
        page.locator("#dayScrub").evaluate(
            "(e)=>{e.value=30;e.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert page.evaluate("() => window.CRLApp.chart.state.day")>=29
        page.locator("#startBtn").click()
        page.wait_for_function("() => window.CRLApp.result && window.CRLApp.result.models.garch.n===1000",timeout=30000)
        again=page.evaluate("""() => Object.fromEntries(window.CRLCore.models.map(m=>
         [m,window.CRLApp.result.models[m].prob["0.100"].p]))""")
        assert initial==again
        assert "0.150874" in page.locator("#holdoutScoreTable").inner_text()
        print("PASS: All five seeded simulations, chart model selection, risk reports and immutable 2025 scores",flush=True)

        page.locator("#resetBtn").click()
        assert page.locator("#kpiGbm").inner_text()=="—"
        page.set_viewport_size({"width":390,"height":844})
        page.evaluate("() => window.scrollTo({top:0,behavior:'instant'})")
        page.wait_for_timeout(250)
        assert not page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth+2"),"Mobile horizontal overflow"
        assert page.locator("#mainChart").is_visible()
        page.screenshot(path="browser-verification-mobile.png",full_page=True)
        page.locator('[data-validation-year="2026"]').click()
        assert not page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth+2"),"Mobile year-switch overflow"
        print("PASS: Single year selector and five model UI responsive at 390px mobile width",flush=True)

        file_page=browser.new_page()
        file_page.on("pageerror",lambda e:errors.append("file mode exception: "+str(e)))
        file_page.on("console",lambda msg:errors.append("file mode console: "+msg.text) if msg.type=="error" else None)
        file_page.goto(pathlib.Path("docs/index.html").resolve().as_uri())
        file_page.wait_for_function("() => !!window.CRLValidationUnified && !!window.CRLApp")
        assert file_page.locator("#mainChart").is_visible()
        assert file_page.evaluate("() => window.CRLValidationUnified.rows.length")==335
        print("PASS: Offline file:// standalone website loads both years without network access",flush=True)
        assert not errors,"Browser JavaScript/console errors: "+json.dumps(errors)
        print("PASS: No uncaught script or browser console errors",flush=True)
        browser.close()
finally:
    server.terminate()
    with contextlib.suppress(Exception):
        server.wait(timeout=5)
