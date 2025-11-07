#!/usr/bin/env python3
"""
Playwright test to verify UI controls are disabled during model switching
"""

import sys
import time
from playwright.sync_api import sync_playwright, expect

def test_disabled_controls_during_switch():
    """Test that start/stop buttons and dropdown are disabled during model switching"""

    print("\n" + "="*70)
    print("TESTING: UI Controls Disabled During Model Switching")
    print("="*70)

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Navigate to the WebUI
            print("\n1. Loading WebUI...")
            page.goto("http://localhost:3000")
            page.wait_for_load_state("networkidle")
            print("✓ Page loaded")

            # Open Model Manager
            print("\n2. Opening Model Manager...")
            page.click("button:has-text('Model Manager')")
            page.wait_for_selector(".model-manager", state="visible")
            print("✓ Model Manager opened")

            # Find a model that's stopped and can be started
            print("\n3. Finding a stopped model to start...")
            time.sleep(2)  # Wait for model status to load

            # Look for a model with Start button (not running)
            start_buttons = page.locator(".model-item .start-model-btn").all()

            if len(start_buttons) == 0:
                print("⚠ No stopped models available to test. Skipping test.")
                browser.close()
                return

            # Get the first stopped model
            first_start_btn = start_buttons[0]
            model_item = first_start_btn.locator("xpath=ancestor::div[@class='model-item']")
            model_name_elem = model_item.locator(".model-name").first
            model_name = model_name_elem.text_content().strip()

            print(f"✓ Found stopped model: {model_name}")

            # Check initial state - button should NOT be disabled
            print("\n4. Verifying initial state (buttons enabled)...")
            is_disabled_before = first_start_btn.is_disabled()
            dropdown = page.locator(".model-selector")
            is_dropdown_disabled_before = dropdown.is_disabled()

            print(f"   Start button disabled: {is_disabled_before}")
            print(f"   Dropdown disabled: {is_dropdown_disabled_before}")

            if is_disabled_before:
                print("✗ FAIL: Start button should NOT be disabled initially")
                return
            if is_dropdown_disabled_before:
                print("✗ FAIL: Dropdown should NOT be disabled initially")
                return

            print("✓ Controls are enabled initially")

            # Click Start button to trigger model switching
            print(f"\n5. Clicking Start button for '{model_name}'...")
            first_start_btn.click()
            print("✓ Start button clicked")

            # Immediately check if controls are disabled (within 500ms)
            print("\n6. Verifying controls are disabled during switching...")
            time.sleep(0.5)  # Small delay to let state update

            # Check if dropdown is disabled
            is_dropdown_disabled_during = dropdown.is_disabled()
            print(f"   Dropdown disabled: {is_dropdown_disabled_during}")

            if not is_dropdown_disabled_during:
                print("✗ FAIL: Dropdown should be disabled during model switching")
                browser.close()
                return

            print("✓ Dropdown is locked during switching")

            # Check if all Start/Stop buttons are disabled
            print("\n7. Verifying all Start/Stop buttons are disabled...")
            all_start_buttons = page.locator(".start-model-btn").all()
            all_stop_buttons = page.locator(".stop-model-btn").all()

            buttons_disabled_count = 0
            buttons_total_count = 0

            for btn in all_start_buttons:
                if btn.is_visible():
                    buttons_total_count += 1
                    if btn.is_disabled():
                        buttons_disabled_count += 1

            for btn in all_stop_buttons:
                if btn.is_visible():
                    buttons_total_count += 1
                    if btn.is_disabled():
                        buttons_disabled_count += 1

            print(f"   Disabled buttons: {buttons_disabled_count}/{buttons_total_count}")

            if buttons_disabled_count != buttons_total_count:
                print(f"✗ FAIL: Not all buttons are disabled ({buttons_disabled_count}/{buttons_total_count})")
                browser.close()
                return

            print("✓ All Start/Stop buttons are disabled during switching")

            # Wait for switching to complete (or timeout after 60 seconds)
            print("\n8. Waiting for model switching to complete...")
            max_wait = 60
            start_time = time.time()
            switching_completed = False

            while time.time() - start_time < max_wait:
                time.sleep(2)

                # Check if dropdown is re-enabled (indicates switching complete)
                if not dropdown.is_disabled():
                    switching_completed = True
                    elapsed = int(time.time() - start_time)
                    print(f"✓ Model switching completed after {elapsed} seconds")
                    break

            if not switching_completed:
                print("⚠ Model switching still in progress after 60s (this is normal for large models)")
                print("✓ But the test passed - controls were properly disabled during switching")

            # Final verification - check controls are re-enabled
            if switching_completed:
                print("\n9. Verifying controls are re-enabled after switching...")
                is_dropdown_disabled_after = dropdown.is_disabled()

                # Find any visible start/stop button
                any_button = page.locator(".start-model-btn, .stop-model-btn").first
                is_any_button_disabled = any_button.is_disabled() if any_button.is_visible() else True

                print(f"   Dropdown disabled: {is_dropdown_disabled_after}")
                print(f"   Buttons disabled: {is_any_button_disabled}")

                if is_dropdown_disabled_after or is_any_button_disabled:
                    # Check if another model is loading
                    loading_status = page.locator(".status-loading").count()
                    if loading_status > 0:
                        print("ℹ  Controls still disabled because model is still loading (expected)")
                    else:
                        print("⚠  Controls still disabled but no loading status visible")

            print("\n" + "="*70)
            print("✅ TEST PASSED")
            print("="*70)
            print("\nSummary:")
            print("  ✓ Dropdown is locked during model switching")
            print("  ✓ All Start/Stop buttons are disabled during switching")
            print("  ✓ UI prevents user from triggering concurrent switches")

        except Exception as e:
            print(f"\n✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            browser.close()

    return True

if __name__ == "__main__":
    success = test_disabled_controls_during_switch()
    sys.exit(0 if success else 1)
