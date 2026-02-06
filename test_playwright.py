"""
Playwright E2E test for J.A.R.V.I.S. Gradio app.
Tests: page load, UI structure, JARVIS theme, tabs, buttons, WebRTC component.
"""
import asyncio
from playwright.async_api import async_playwright

URL = "http://localhost:7860"


async def run_tests():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # ── Test 1: Page loads ──
        try:
            resp = await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
            status = resp.status if resp else 0
            results.append(("Page loads", status == 200, f"HTTP {status}"))
        except Exception as e:
            results.append(("Page loads", False, str(e)))
            await browser.close()
            return results

        await page.wait_for_timeout(3000)

        # ── Test 2: JARVIS header present ──
        try:
            title = await page.query_selector(".jarvis-title")
            title_text = await title.inner_text() if title else ""
            results.append(("JARVIS header", "J.A.R.V.I.S." in title_text, title_text))
        except Exception as e:
            results.append(("JARVIS header", False, str(e)))

        # ── Test 3: Arc Reactor present ──
        try:
            reactor = await page.query_selector(".arc-reactor")
            results.append(("Arc Reactor", reactor is not None, "Found" if reactor else "Not found"))
        except Exception as e:
            results.append(("Arc Reactor", False, str(e)))

        # ── Test 4: Arc Reactor shows OFFLINE initially ──
        try:
            reactor = await page.query_selector(".arc-reactor.disconnected")
            label = await page.query_selector(".reactor-label")
            label_text = await label.inner_text() if label else ""
            results.append(("Reactor OFFLINE state", reactor is not None, label_text))
        except Exception as e:
            results.append(("Reactor OFFLINE state", False, str(e)))

        # ── Test 5: CONNECT button present ──
        try:
            btns = await page.query_selector_all("button")
            connect_found = False
            for btn in btns:
                text = await btn.inner_text()
                if "CONNECT" in text.upper() and "DISCONNECT" not in text.upper():
                    connect_found = True
                    break
            results.append(("CONNECT button", connect_found, ""))
        except Exception as e:
            results.append(("CONNECT button", False, str(e)))

        # ── Test 6: DISCONNECT button present ──
        try:
            disconnect_found = False
            for btn in btns:
                text = await btn.inner_text()
                if "DISCONNECT" in text.upper():
                    disconnect_found = True
                    break
            results.append(("DISCONNECT button", disconnect_found, ""))
        except Exception as e:
            results.append(("DISCONNECT button", False, str(e)))

        # ── Test 7: Tabs exist (VOICE MODE, TEXT MODE) ──
        try:
            tabs = await page.query_selector_all('button[role="tab"]')
            tab_texts = [await t.inner_text() for t in tabs]
            voice_tab = any("VOICE" in t.upper() for t in tab_texts)
            text_tab = any("TEXT" in t.upper() for t in tab_texts)
            results.append(("VOICE MODE tab", voice_tab, str(tab_texts)))
            results.append(("TEXT MODE tab", text_tab, str(tab_texts)))
        except Exception as e:
            results.append(("Tabs", False, str(e)))

        # ── Test 8: WebRTC component in VOICE MODE ──
        try:
            # Click VOICE MODE tab first
            for t in tabs:
                text = await t.inner_text()
                if "VOICE" in text.upper():
                    await t.click()
                    break
            await page.wait_for_timeout(1000)
            # Check for WebRTC-related elements (video/audio element or webrtc button)
            webrtc_el = await page.query_selector("[data-testid='webrtc']")
            # Also look for any button with microphone/start
            audio_elements = await page.query_selector_all("audio, video, [class*='webrtc'], [id*='webrtc']")
            # Check for the WebRTC start button
            start_btns = await page.query_selector_all("button")
            webrtc_btns = []
            for btn in start_btns:
                text = await btn.inner_text()
                if any(kw in text.lower() for kw in ["start", "record", "microphone", "▶"]):
                    webrtc_btns.append(text)

            found = webrtc_el is not None or len(audio_elements) > 0 or len(webrtc_btns) > 0
            detail = f"webrtc_el={webrtc_el is not None}, audio_els={len(audio_elements)}, webrtc_btns={webrtc_btns}"
            results.append(("WebRTC component", found, detail))
        except Exception as e:
            results.append(("WebRTC component", False, str(e)))

        # ── Test 9: TEXT MODE - Textbox and TRANSMIT button ──
        try:
            for t in tabs:
                text = await t.inner_text()
                if "TEXT" in text.upper():
                    await t.click()
                    break
            await page.wait_for_timeout(1000)
            textbox = await page.query_selector("textarea")
            transmit_btn = None
            all_btns = await page.query_selector_all("button")
            for btn in all_btns:
                text = await btn.inner_text()
                if "TRANSMIT" in text.upper():
                    transmit_btn = btn
                    break
            results.append(("TEXT MODE textbox", textbox is not None, ""))
            results.append(("TRANSMIT button", transmit_btn is not None, ""))
        except Exception as e:
            results.append(("TEXT MODE", False, str(e)))

        # ── Test 10: Communication Log (Chatbot) ──
        try:
            chatbot = await page.query_selector("#jarvis-log")
            results.append(("Communication Log", chatbot is not None, ""))
        except Exception as e:
            results.append(("Communication Log", False, str(e)))

        # ── Test 11: CSS theme applied (dark background) ──
        try:
            bg = await page.evaluate("""
                () => {
                    const el = document.querySelector('.gradio-container');
                    return el ? getComputedStyle(el).background : 'not found';
                }
            """)
            is_dark = "06080f" in bg.lower() or "0a0f1a" in bg.lower() or "rgb(6" in bg.lower() or "rgb(10" in bg.lower()
            results.append(("Dark JARVIS theme", is_dark, bg[:80]))
        except Exception as e:
            results.append(("Dark JARVIS theme", False, str(e)))

        # ── Test 12: Grid overlay ──
        try:
            grid = await page.query_selector(".jarvis-grid-overlay")
            results.append(("Grid overlay", grid is not None, ""))
        except Exception as e:
            results.append(("Grid overlay", False, str(e)))

        # ── Test 13: Scan line ──
        try:
            scanline = await page.query_selector(".jarvis-scanline")
            results.append(("Scan line", scanline is not None, ""))
        except Exception as e:
            results.append(("Scan line", False, str(e)))

        # ── Test 14: Member database accordion ──
        try:
            accordion = await page.query_selector(".jarvis-accordion")
            results.append(("Member DB accordion", accordion is not None, ""))
        except Exception as e:
            results.append(("Member DB accordion", False, str(e)))

        # ── Take screenshot ──
        await page.screenshot(path="/Users/ggls03/Documents/real-timeAPI/test_screenshot.png", full_page=True)
        results.append(("Screenshot saved", True, "test_screenshot.png"))

        await browser.close()

    return results


async def main():
    print("=" * 60)
    print("  J.A.R.V.I.S. Playwright E2E Test")
    print("=" * 60)

    results = await run_tests()

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)

    for name, ok, detail in results:
        icon = "PASS" if ok else "FAIL"
        det = f" ({detail})" if detail else ""
        print(f"  [{icon}] {name}{det}")

    print()
    print(f"  Results: {passed} passed, {failed} failed, {len(results)} total")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
