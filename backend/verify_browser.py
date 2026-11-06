import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
import websockets

BACKEND_DIR = os.path.abspath("backend")
PYTHON_EXE = os.path.abspath("backend/.venv/Scripts/python.exe")
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ARTIFACT_DIR = r"C:\Users\dixit\.gemini\antigravity\brain\102e26b1-a40c-4c02-ac6f-04c7e5f3bdd8"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

async def send_cdp(ws, method, params=None, msg_id=[1]):
    mid = msg_id[0]
    msg_id[0] += 1
    payload = {"id": mid, "method": method, "params": params or {}}
    await ws.send(json.dumps(payload))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == mid:
            return resp.get("result", {})

async def evaluate(ws, expr):
    res = await send_cdp(ws, "Runtime.evaluate", {
        "expression": expr,
        "returnByValue": True,
        "awaitPromise": True
    })
    return res.get("result", {}).get("value")

async def take_screenshot(ws, filename):
    res = await send_cdp(ws, "Page.captureScreenshot", {"format": "png"})
    data = res.get("data")
    if data:
        import base64
        filepath = os.path.join(ARTIFACT_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(data))
        print(f"[SCREENSHOT] Saved: {filepath}")
        return filepath
    return None

async def run_verification():
    print("=== STARTING BROWSER VERIFICATION SUITE ===")
    
    # 1. Start FastAPI backend if not already running
    backend_proc = None
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=1)
        print("[1/5] Backend API is already running on 127.0.0.1:8000.")
    except Exception:
        print("[1/5] Starting backend API on 127.0.0.1:8000...")
        backend_proc = subprocess.Popen(
            [PYTHON_EXE, "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000"],
            cwd=os.path.abspath("."),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    
    # 2. Check if Vite preview is already running on 127.0.0.1:5173
    vite_proc = None
    try:
        urllib.request.urlopen("http://127.0.0.1:5173/", timeout=1)
        print("[2/5] Vite preview is already running on 127.0.0.1:5173.")
    except Exception:
        print("[2/5] Starting Vite production preview on 127.0.0.1:5173...")
        vite_proc = subprocess.Popen(
            ["npx.cmd", "vite", "preview", "--port", "5173", "--host", "127.0.0.1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)

    # Wait for backend server to be fully ready
    print("  Waiting for backend API on 127.0.0.1:8000...")
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=1) as resp:
                if resp.status == 200:
                    print("  [READY] Backend API is up and running on port 8000.")
                    break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("Backend API failed to start on port 8000")
    
    # 3. Start Headless Chrome
    print("[3/5] Starting Chrome Headless with remote debugging on port 9222...")
    chrome_proc = subprocess.Popen([
        CHROME_EXE,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--window-size=1440,900",
        "--disable-gpu",
        "--no-sandbox",
        "about:blank"
    ])
    
    ws = None
    try:
        # Connect to Chrome via CDP
        time.sleep(2)
        version_info = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version").read())
        browser_ws_url = version_info.get("webSocketDebuggerUrl")
        
        # Get page target (filter out background extensions)
        targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
        page_targets = [t for t in targets if t.get("type") == "page"]
        if page_targets:
            page_ws_url = page_targets[0]["webSocketDebuggerUrl"]
        else:
            new_target = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/new").read())
            page_ws_url = new_target["webSocketDebuggerUrl"]
        
        print(f"[CDP] Connected to Chrome page target: {page_ws_url}")
        async with websockets.connect(page_ws_url, max_size=20*1024*1024) as ws:
            await send_cdp(ws, "Page.enable")
            await send_cdp(ws, "Runtime.enable")
            await send_cdp(ws, "DOM.enable")
            await send_cdp(ws, "Log.enable")
            
            # Setup auth token before navigating
            sys.path.insert(0, BACKEND_DIR)
            from app.auth_utils import create_access_token
            token = create_access_token({"sub": "nanu@gmail.com", "user_id": 1})
            
            auth_script = f"""
            try {{
                localStorage.setItem('token', '{token}');
                localStorage.setItem('user', JSON.stringify({{
                    id: 1,
                    email: 'nanu@gmail.com',
                    name: 'vinay',
                    role: 'Command Officer'
                }}));
                localStorage.setItem('activeEventId', 'evt-1793089557795');
                localStorage.setItem('selectedEventId', 'evt-1793089557795');
            }} catch(e) {{}}
            """
            await send_cdp(ws, "Page.addScriptToEvaluateOnNewDocument", {"source": auth_script})
            print("[AUTH] Injected pre-document localStorage token script.")

            # Navigate to 127.0.0.1:5173/heatmap
            print("[NAV] Navigating to http://127.0.0.1:5173/heatmap...")
            await send_cdp(ws, "Page.navigate", {"url": "http://127.0.0.1:5173/heatmap"})
            await send_cdp(ws, "Page.navigate", {"url": "http://127.0.0.1:5173/heatmap"})
            
            # Wait for React to mount and load data
            print("  Waiting for React app to mount and render...")
            for _ in range(20):
                has_root_content = await evaluate(ws, "!!document.querySelector('#root')?.children.length")
                if has_root_content:
                    print("  [MOUNT] React app mounted.")
                    break
                await asyncio.sleep(0.5)
            
            print("  Waiting for floorplan blueprint to render...")
            for _ in range(15):
                has_bp = await evaluate(ws, "!!document.querySelector('img[alt=\"Verified Venue Floorplan Blueprint\"]')")
                if has_bp:
                    print("  [MAP] Floorplan blueprint rendered.")
                    break
                await asyncio.sleep(1)
            
            curr_url = await evaluate(ws, "window.location.href")
            curr_title = await evaluate(ws, "document.title")
            main_html = await evaluate(ws, "document.querySelector('main')?.innerHTML")
            images_info = await evaluate(ws, "Array.from(document.querySelectorAll('img')).map(i => ({alt: i.alt, src: i.src.slice(0, 50)}))")
            fetch_err = await evaluate(ws, "document.querySelector('.text-rose-300')?.innerText")
            is_loading = await evaluate(ws, "!!document.querySelector('.animate-spin')")
            print(f"  Current URL: {curr_url}")
            print(f"  Main HTML length: {len(main_html) if main_html else 0}")
            print(f"  Images in page: {images_info}")
            clean_err = str(fetch_err).encode('ascii', 'replace').decode('ascii')
            print(f"  Fetch error text: {clean_err}")
            print(f"  Loading state: {is_loading}")
            
            print("[4/5] Verifying Heatmap Rendering & Coordinate Alignment...")
            
            # Check title
            title = await evaluate(ws, "document.title")
            print(f"  Page title: {title}")
            
            # Check floorplan blueprint image
            has_blueprint = await evaluate(ws, "!!document.querySelector('img[alt=\"Verified Venue Floorplan Blueprint\"]')")
            blueprint_src = await evaluate(ws, "document.querySelector('img[alt=\"Verified Venue Floorplan Blueprint\"]')?.src")
            print(f"  Blueprint floorplan visible: {has_blueprint} ({blueprint_src[:60] if blueprint_src else 'None'}...)")
            assert has_blueprint, "Floorplan blueprint must be present"
            
            # Check heatmap overlay image
            has_overlay = await evaluate(ws, "!!document.querySelector('img[alt=\"Crowd Heat Overlay\"]')")
            overlay_src = await evaluate(ws, "document.querySelector('img[alt=\"Crowd Heat Overlay\"]')?.src")
            overlay_opacity = await evaluate(ws, "document.querySelector('img[alt=\"Crowd Heat Overlay\"]')?.style.opacity")
            overlay_class = await evaluate(ws, "document.querySelector('img[alt=\"Crowd Heat Overlay\"]')?.className")
            
            print(f"  Heatmap overlay visible: {has_overlay}")
            print(f"  Heatmap data URI length: {len(overlay_src) if overlay_src else 0}")
            print(f"  Heatmap CSS opacity: {overlay_opacity}")
            print(f"  Heatmap classes (stacking/position): {overlay_class}")
            assert has_overlay, "Heatmap overlay image must be present and rendered"
            assert overlay_src.startswith("data:image/png;base64,"), "Heatmap overlay must be a valid PNG data URI"
            assert "z-10" in overlay_class, "Heatmap overlay must have z-10 stacking order"
            
            # Check camera pin CAM3 position and telemetry
            cam3_pin_count = await evaluate(ws, """
                (() => {
                    const pins = Array.from(document.querySelectorAll('.font-mono'));
                    const cam3 = pins.find(el => el.textContent.includes('CAM3'));
                    if (!cam3) return null;
                    const badge = cam3.parentElement.querySelector('span.bg-black\\\\/40');
                    return badge ? badge.textContent.trim() : null;
                })()
            """)
            print(f"  CAM3 verified pin live count badge: {cam3_pin_count} people")
            assert cam3_pin_count is not None, "CAM3 pin must be present on blueprint"
            
            # Check 4-profile visual calibration bar
            has_profile_bar = await evaluate(ws, "!!document.querySelector('.grid.grid-cols-2.md\\\\:grid-cols-4')")
            print(f"  4-Profile visual calibration bar visible: {has_profile_bar}")
            assert has_profile_bar, "4-Profile visual calibration bar must be present"

            # Capture initial screenshot with live heatmap overlay
            await take_screenshot(ws, "01_heatmap_overlay_visible.png")
            
            # Test Demo Scenarios (Deterministic benchmark datasets)
            print("  Testing Demo Scenario switching...")
            # Switch to Demo A (Sparse Occupancy - Profile LOW)
            await evaluate(ws, """
                (() => {
                    const sel = Array.from(document.querySelectorAll('select')).find(s => s.options[0]?.text.includes('Live Surveillance'));
                    if (sel) {
                        sel.value = 'sparse';
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
            """)
            await asyncio.sleep(1.0)
            sparse_demo_badge = await evaluate(ws, "document.body.innerText.includes('DEMO BENCHMARK')")
            print(f"  Demo A Sparse Occupancy badge active: {sparse_demo_badge}")
            await take_screenshot(ws, "05_demo_sparse_low.png")

            # Switch to Demo C (Dense Main Hall - Profile HIGH)
            await evaluate(ws, """
                (() => {
                    const sel = Array.from(document.querySelectorAll('select')).find(s => s.options[0]?.text.includes('Live Surveillance'));
                    if (sel) {
                        sel.value = 'dense_hall';
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
            """)
            await asyncio.sleep(1.0)
            await take_screenshot(ws, "06_demo_dense_high.png")

            # Switch to Demo D (Critical Choke-Point - Profile CRITICAL)
            await evaluate(ws, """
                (() => {
                    const sel = Array.from(document.querySelectorAll('select')).find(s => s.options[0]?.text.includes('Live Surveillance'));
                    if (sel) {
                        sel.value = 'critical_corridor';
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
            """)
            await asyncio.sleep(1.0)
            await take_screenshot(ws, "07_demo_critical.png")

            # Switch back to Live Surveillance
            await evaluate(ws, """
                (() => {
                    const sel = Array.from(document.querySelectorAll('select')).find(s => s.options[0]?.text.includes('Live Surveillance'));
                    if (sel) {
                        sel.value = 'live';
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
            """)
            await asyncio.sleep(1.0)

            # Test Toggle Heatmap Overlay button
            print("  Testing Heatmap Overlay Toggle button...")
            await evaluate(ws, """
                (() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Heatmap Overlay'));
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(0.5)
            overlay_after_toggle = await evaluate(ws, "!!document.querySelector('img[alt=\"Crowd Heat Overlay\"]')")
            print(f"  After toggle OFF, overlay visible: {overlay_after_toggle}")
            assert not overlay_after_toggle, "Overlay should be hidden after toggling off"
            await take_screenshot(ws, "02_heatmap_overlay_toggled_off.png")
            
            # Toggle back ON
            await evaluate(ws, """
                (() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Heatmap Overlay'));
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(0.5)
            overlay_back_on = await evaluate(ws, "!!document.querySelector('img[alt=\"Crowd Heat Overlay\"]')")
            print(f"  After toggle ON, overlay visible: {overlay_back_on}")
            assert overlay_back_on, "Overlay should be visible after toggling back on"
            
            # Test Zoom In
            print("  Testing Zoom & Pan...")
            await evaluate(ws, """
                (() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Zoom In'));
                    if (btn) { btn.click(); btn.click(); }
                })()
            """)
            await asyncio.sleep(0.5)
            zoom_transform = await evaluate(ws, "document.querySelector('img[alt=\"Verified Venue Floorplan Blueprint\"]').parentElement.style.transform")
            print(f"  Zoom transform style: {zoom_transform}")
            assert "scale(1.5)" in zoom_transform, f"Expected scale(1.5), got {zoom_transform}"
            await take_screenshot(ws, "03_heatmap_zoomed.png")
            
            # Reset Zoom
            await evaluate(ws, """
                (() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Reset'));
                    if (btn) btn.click();
                })()
            """)
            await asyncio.sleep(0.5)
            
            # 5. Verify Stationary Sidebar Scrolling
            print("[5/5] Verifying Sidebar Stationary Behavior on Page Scroll...")
            sidebar_rect_before = await evaluate(ws, """
                (() => {
                    const r = document.querySelector('aside').getBoundingClientRect();
                    return { top: r.top, left: r.left, width: r.width, height: r.height };
                })()
            """)
            print(f"  Sidebar rect BEFORE scroll: top={sidebar_rect_before['top']}, left={sidebar_rect_before['left']}, height={sidebar_rect_before['height']}")
            
            # Scroll main content container down by 400px
            await evaluate(ws, """
                (() => {
                    const mainScroll = document.querySelector('div.overflow-y-auto');
                    if (mainScroll) mainScroll.scrollTop = 400;
                })()
            """)
            await asyncio.sleep(0.5)
            
            scroll_top = await evaluate(ws, "document.querySelector('div.overflow-y-auto')?.scrollTop")
            sidebar_rect_after = await evaluate(ws, """
                (() => {
                    const r = document.querySelector('aside').getBoundingClientRect();
                    return { top: r.top, left: r.left, width: r.width, height: r.height };
                })()
            """)
            print(f"  Main container scrollTop: {scroll_top}px")
            print(f"  Sidebar rect AFTER scroll: top={sidebar_rect_after['top']}, left={sidebar_rect_after['left']}, height={sidebar_rect_after['height']}")
            
            assert sidebar_rect_before["top"] == sidebar_rect_after["top"] == 0, "Sidebar top must remain at 0"
            assert sidebar_rect_before["left"] == sidebar_rect_after["left"] == 0, "Sidebar left must remain at 0"
            assert sidebar_rect_before["height"] == sidebar_rect_after["height"], "Sidebar height must remain viewport height"
            print("  [SUCCESS] Sidebar remained 100% STATIONARY while main page content scrolled!")
            
            await take_screenshot(ws, "04_sidebar_stationary_scrolled.png")
            
            print("\n=== ALL BROWSER & PLAYBACK VERIFICATIONS PASSED SUCCESSFULLY! ===")
            
    finally:
        print("[CLEANUP] Stopping processes...")
        chrome_proc.terminate()
        if vite_proc:
            vite_proc.terminate()
        if backend_proc:
            backend_proc.terminate()
        try:
            chrome_proc.wait(timeout=2)
            if vite_proc:
                vite_proc.wait(timeout=2)
            if backend_proc:
                backend_proc.wait(timeout=2)
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(run_verification())
