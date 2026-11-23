"""Headless Chromium smoke tests for all primary CryptoRisk Lab interactions."""
import contextlib
import json
import pathlib
import socket
import subprocess
import time
from playwright.sync_api import sync_playwright

PORT = 8765
server = subprocess.Popen(
    ["python", "-m", "http.server", str(PORT), "--directory", "docs"],
    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
)
try:
    for attempt in range(60):
        with contextlib.closing(socket.socket()) as sock:
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                break
        time.sleep(0.25)
    else:
        raise RuntimeError("Could not start local website server")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="load")
        page.locator("#historicalCandles").wait_for()
        page.wait_for_function(
            "() => document.querySelector('#historicalStatus').textContent.includes('Binance spot')",
            timeout=30000
        )
        print("PASS: Verified Binance OHLC historical chart loaded", flush=True)
        page.wait_for_function(
            "() => document.querySelector('#day30Regime').textContent.includes('Calm')"
        )
        assert "92.41%" in page.locator("#calmStay").inner_text()
        print("PASS: Markov theoretical explorer loaded", flush=True)
        page.locator('input[name="pathCount"][value="1000"]').check(force=True)
        page.locator("#startBtn").click()
        page.wait_for_function(
            "() => typeof simulation !== 'undefined' && simulation && simulation.completed >= 1000 && simulation.returns",
            timeout=90000
        )
        page.wait_for_function("() => document.querySelector('#replayPlay').disabled === false", timeout=10000)
        p10 = page.locator("#gbmP10").inner_text()
        assert "%" in p10
        print("PASS: 1000-path GBM and Markov simulation finished", p10, flush=True)
        page.locator("#replayPlay").click()
        page.wait_for_timeout(900)
        current_day = int(page.locator("#replayDay").input_value())
        assert current_day > 0
        page.locator("#replayPlay").click()
        page.locator("#replayDay").evaluate("(el) => { el.value = 12; el.dispatchEvent(new Event('input', {bubbles:true})); }")
        assert "Day 12" in page.locator("#replayDayText").inner_text()
        assert "Investment:" in page.locator("#replayDescription").inner_text()
        print("PASS: Genuine simulated price and regime replay", flush=True)
        assert "0.151631" in page.locator("#validationPanel").inner_text()
        assert "62/335" in page.locator("#validationPanel").inner_text()
        print("PASS: Historical evaluation table displays", flush=True)
        pathlib.Path("browser-verification.png").parent.mkdir(exist_ok=True)
        page.screenshot(path="browser-verification.png", full_page=True)
        page.locator("#resetBtn").click()
        assert "Ready:" in page.locator("#simulationStatus").inner_text()
        print("PASS: Reset works", flush=True)
        assert not errors, "Javascript console errors: " + json.dumps(errors)
        print("PASS: No uncaught JavaScript page errors", flush=True)
        browser.close()
finally:
    server.terminate()
    with contextlib.suppress(Exception):
        server.wait(timeout=5)
