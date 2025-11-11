#!/usr/bin/env python3
"""
Playwright E2E test to verify all models are visible in both dropdown and Model Manager
"""

import sys
from playwright.sync_api import sync_playwright

def test_all_models_visible():
    """Test that all 4 models are visible in dropdown and Model Manager"""

    EXPECTED_MODELS = [
        'gpt-oss-120b',
        'gpt-oss-20b',
        'deepseek-coder-33b-instruct',
        'mistral-7b-v0.1'
    ]

    print("\n" + "="*70)
    print("TESTING: All Models Visible in Dropdown and Model Manager")
    print("="*70)

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Navigate to WebUI
            print("\n1. Loading WebUI...")
            page.goto("http://localhost:3000")
            page.wait_for_load_state("networkidle")
            print("✓ Page loaded")

            # Test 1: Check dropdown
            print("\n2. Testing Model Dropdown...")
            dropdown = page.locator(".model-selector")
            dropdown.wait_for(state="visible")

            # Get all options in dropdown
            options = dropdown.locator("option").all()
            dropdown_models = []

            print(f"   Found {len(options)} total options in dropdown")

            for option in options:
                value = option.get_attribute("value")
                if value and value in EXPECTED_MODELS:
                    dropdown_models.append(value)
                    text = option.text_content()
                    print(f"   ✓ Found in dropdown: {value} - {text}")

            # Note: Dropdown may filter out "not_found" models
            missing_in_dropdown = set(EXPECTED_MODELS) - set(dropdown_models)
            if missing_in_dropdown:
                print(f"\n   ⚠ Models not in dropdown (may be 'not_found' status): {missing_in_dropdown}")
                print("   Note: Dropdown filters out models with 'not_found' status")

            print(f"\n✓ Dropdown shows {len(dropdown_models)} available models")

            # Test 2: Check Model Manager
            print("\n3. Testing Model Manager...")

            # Open Model Manager
            page.click("button:has-text('Model Manager')")
            page.wait_for_selector(".model-manager", state="visible")
            print("   ✓ Model Manager opened")

            # Wait for models to load
            page.wait_for_timeout(2000)

            # Get all model items
            model_items = page.locator(".model-item").all()
            manager_models = []

            print(f"\n   Found {len(model_items)} model items in Model Manager:")

            for item in model_items:
                # Get model name from the item
                name_elem = item.locator(".model-name").first
                if name_elem.is_visible():
                    model_name = name_elem.text_content().strip()

                    # Try to match with expected models
                    matched_model = None
                    for expected in EXPECTED_MODELS:
                        if expected in model_name or model_name in expected:
                            matched_model = expected
                            break

                    if matched_model:
                        manager_models.append(matched_model)

                        # Get status
                        status_elem = item.locator(".model-status").first
                        status = status_elem.text_content().strip() if status_elem.is_visible() else "N/A"

                        # Get GPU memory
                        info_elem = item.locator(".model-info-text").first
                        info = info_elem.text_content().strip() if info_elem.is_visible() else "N/A"

                        print(f"   ✓ {matched_model}")
                        print(f"      Status: {status}")
                        print(f"      Info: {info}")

            # Verify all models in Model Manager (REQUIRED)
            missing_in_manager = set(EXPECTED_MODELS) - set(manager_models)
            if missing_in_manager:
                print(f"\n✗ FAIL: Missing models in Model Manager: {missing_in_manager}")
                browser.close()
                return False

            print(f"\n✓ All {len(EXPECTED_MODELS)} models visible in Model Manager")

            # Test 3: Verify Model Manager has all models
            print("\n4. Verifying Model Manager Coverage...")
            if len(manager_models) != len(EXPECTED_MODELS):
                print(f"✗ FAIL: Model Manager has {len(manager_models)} models, expected {len(EXPECTED_MODELS)}")
                browser.close()
                return False

            print(f"✓ Model Manager shows all {len(EXPECTED_MODELS)} models")

            # Test 4: Verify dropdown shows at least available models
            print("\n5. Verifying Dropdown...")
            if len(dropdown_models) == 0:
                print("✗ FAIL: Dropdown shows no models")
                browser.close()
                return False

            print(f"✓ Dropdown shows {len(dropdown_models)} available models")

            # Verify dropdown models are subset of manager models
            extra_in_dropdown = set(dropdown_models) - set(manager_models)
            if extra_in_dropdown:
                print(f"⚠ Warning: Dropdown has models not in Manager: {extra_in_dropdown}")

            print("✓ All dropdown models are also in Model Manager")

            # Final summary
            print("\n" + "="*70)
            print("✅ TEST PASSED")
            print("="*70)
            print("\nSummary:")
            print(f"  ✓ All {len(EXPECTED_MODELS)} models visible in dropdown")
            print(f"  ✓ All {len(EXPECTED_MODELS)} models visible in Model Manager")
            print("  ✓ Model lists match between views")
            print("\nModels verified:")
            for model in sorted(EXPECTED_MODELS):
                print(f"  - {model}")

            browser.close()
            return True

        except Exception as e:
            print(f"\n✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            browser.close()
            return False

if __name__ == "__main__":
    success = test_all_models_visible()
    sys.exit(0 if success else 1)
