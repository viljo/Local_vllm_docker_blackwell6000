#!/usr/bin/env python3
"""
Real User Simulation - Exactly as a human would use the WebUI
Tests that the chat actually works and returns real responses
"""
from playwright.sync_api import sync_playwright
import sys

WEBUI_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"

def test_real_chat():
    """Simulate exactly what you're doing: open browser, type 'hi', press enter"""
    print("="*70)
    print("REAL USER SIMULATION TEST")
    print("Simulating: Open browser, type 'hi', click Send")
    print("="*70)

    with sync_playwright() as p:
        # Launch browser (headless=False to see it)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"\n1. Opening {WEBUI_URL}...")
        page.goto(WEBUI_URL, wait_until="networkidle")
        print("✓ Page loaded")

        # Wait for page to be ready
        page.wait_for_selector(".message-input", timeout=10000)
        print("✓ Input field visible")

        print("\n2. Typing 'hi' into input field...")
        input_field = page.locator(".message-input")
        input_field.click()  # Click to focus
        input_field.fill("hi")  # Type 'hi'
        print("✓ Typed 'hi'")

        print("\n3. Clicking Send button...")
        send_button = page.locator(".send-btn")

        # Count messages before sending
        messages_before = page.locator(".message").count()

        send_button.click()
        print("✓ Send button clicked")

        print("\n4. Waiting for response...")
        # Wait for new message to appear
        page.wait_for_function(
            f"document.querySelectorAll('.message').length > {messages_before}",
            timeout=30000
        )

        # Wait for loading to finish
        page.wait_for_selector(".loading", state="detached", timeout=30000)
        print("✓ Response received")

        print("\n5. Checking response content...")
        # Get all messages
        messages = page.locator(".message")
        message_count = messages.count()
        print(f"Total messages on page: {message_count}")

        # Get the assistant's response (last message)
        if message_count >= 2:
            user_msg = messages.nth(-2).locator(".message-content").text_content()
            assistant_msg = messages.nth(-1).locator(".message-content").text_content()

            print(f"\nYour message: {user_msg}")
            print(f"Assistant response: {assistant_msg}")

            # Check if it's an error
            if "Error" in assistant_msg or "network error" in assistant_msg.lower():
                print("\n✗ FAIL: Got error message instead of real response")
                print(f"Error text: {assistant_msg}")

                # Take screenshot
                page.screenshot(path="chat_error.png")
                print("Screenshot saved to chat_error.png")

                browser.close()
                return False

            elif len(assistant_msg.strip()) == 0:
                print("\n✗ FAIL: Response is empty")
                browser.close()
                return False

            else:
                print("\n✓ PASS: Got real response from AI!")
                print(f"Response length: {len(assistant_msg)} characters")
                browser.close()
                return True
        else:
            print(f"\n✗ FAIL: Expected at least 2 messages, got {message_count}")
            browser.close()
            return False

if __name__ == "__main__":
    success = test_real_chat()
    sys.exit(0 if success else 1)
