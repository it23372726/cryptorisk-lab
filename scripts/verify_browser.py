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
        assert page.evaluate("() => window.CRL_HISTORY.candles.length") == 62
        print("PASS: Offline-bundled observed 62 daily Binance candles render", flush=True)
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
        page.locator("#revealBtn").click()
        assert page.locator("#revealBtn").get_attribute("aria-pressed") == "true"
        print("PASS: Forecast scrubber, regime, overlays and actual-outcome reveal", flush=True)
        page.locator("#helpOpen").click()
        assert page.locator("#helpDialog").evaluate("(e) => e.open")
        page.locator("#helpClose").click()
        assert not page.locator("#helpDialog").evaluate("(e) => e.open")
        print("PASS: Compact how-to-use dialog opens and closes", flush=True)
        page.locator("#startBtn").click()
        page.wait_for_function("() => window.CRLApp.result && window.CRLApp.result.models.gbm.n === 1000", timeout=30000)
        assert first == page.locator("#kpiGbm").inner_text(), "Same seed/settings did not reproduce GBM output"
        print("PASS: Reproducible Monte Carlo probabilities", flush=True)
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
