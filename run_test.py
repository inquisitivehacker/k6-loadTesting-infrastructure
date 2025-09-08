import os
import subprocess
import sys
import json
import re
import asyncio

# Try to import the new PDF generation library
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_numeric_input(prompt):
    while True:
        try:
            value = int(input(prompt))
            if value > 0: return value
            else: print("Please enter a positive number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

async def generate_pdf_from_dashboard(report_base_path):
    """Takes a snapshot of the live dashboard and saves it as a PDF."""
    if not PLAYWRIGHT_AVAILABLE:
        print("\n--- ⚠️ PDF Generation Skipped ---")
        print("--- Please run 'pip install playwright' and 'playwright install' to enable this feature. ---")
        return

    pdf_path = f"{report_base_path}.pdf"
    dashboard_url = "http://localhost:8069/dashboardgenerator.html"

    try:
        print(f"\n---  generating PDF from dashboard at {dashboard_url} ---")
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            await page.goto(dashboard_url, wait_until="networkidle")
            
            # Give charts a moment to animate and render fully
            await page.wait_for_timeout(2000)
            
            await page.pdf(path=pdf_path, format="A4", print_background=True, margin={"top": "20mm", "bottom": "20mm"})
            await browser.close()
        
        os.chmod(pdf_path, 0o644)
        print(f"--- ✅ PDF report saved to {pdf_path} ---")
            
    except Exception as e:
        print(f"\n--- ❌ An error occurred during PDF generation: {e} ---")
        print("--- Ensure the web-server container is running. ---")


def main():
    clear_screen()

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        requests = config.get('requests', [])
        base_url = config.get('baseUrl')
        if not requests or not base_url:
            print("Error: 'config.json' must contain 'baseUrl' and a 'requests' list. Exiting.")
            sys.exit(1)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading 'config.json': {e}. Exiting.")
        sys.exit(1)

    print(f"✅ Base URL loaded from config: {base_url}\n")
    print("First, let's establish a baseline for your tests.")
    peak_users = get_numeric_input("Around how many concurrent users do you expect at your peak? ")
    auth_token = input("\nPlease paste the Bearer Token (or press Enter if none):\n> ")

    print("\nWhich API request would you like to test?")
    for i, req in enumerate(requests):
        print(f"{i + 1}) {req['name']} ({req['method']})")

    req_choice_idx = get_numeric_input(f"Enter number (1-{len(requests)}): ") - 1
    if not 0 <= req_choice_idx < len(requests):
        print("Invalid choice. Exiting.")
        sys.exit(1)
    chosen_request = requests[req_choice_idx]

    print("\nWhich type of test would you like to run?")
    print("1) Smoke  2) Load  3) Stress  4) Spike  5) Soak")
    test_choice = input("Enter number(s), separated by commas (e.g., 1,3): ")
    test_map = {"1": "smoke", "2": "load", "3": "stress", "4": "spike", "5": "soak"}
    tests_to_run = [test_map[c.strip()] for c in test_choice.split(',') if c.strip() in test_map]

    if not tests_to_run:
        print("No valid tests selected. Exiting.")
        sys.exit(1)

    print("\n--- Starting web server... ---")
    subprocess.run(["docker", "compose", "up", "-d", "--build", "web-server"], check=True)
    print(f"Web server is running on http://localhost:8069/dashboardgenerator.html")

    for test_type in tests_to_run:
        print("\n=========================================================")
        print(f"  🚀 Starting: {test_type.title()} Test on '{chosen_request['name']}'")
        print(f"  Scaling for {peak_users} peak VUs")
        print("=========================================================\n")

        env_vars = {
            "BASE_URL": base_url,
            "ENDPOINT": chosen_request['endpoint'],
            "REQUEST_METHOD": chosen_request['method'],
            "REQUEST_NAME": chosen_request['name'],
            "AUTH_TOKEN": auth_token,
            "TEST_TYPE": test_type,
            "PEAK_VUS": str(peak_users),
            "REQUEST_PAYLOAD": json.dumps(chosen_request.get('payload', {})),
            "CONTENT_TYPE": chosen_request.get('contentType', 'application/json'),
            "REQUEST_HEADERS": json.dumps(chosen_request.get('headers', {})),
            "QUERY_PARAMS": json.dumps(chosen_request.get('queryParams', {})),
            "EXPECTED_STATUS": str(chosen_request.get('expectedStatus', 200))
        }

        command = ["docker", "compose", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}"]
        for key, value in env_vars.items():
            command.extend(["-e", f"{key}={value}"])
        command.append("k6")

        try:
            subprocess.run(command, check=True)

            results_dir = './results'
            if os.path.isdir(results_dir):
                for filename in os.listdir(results_dir):
                    file_path = os.path.join(results_dir, filename)
                    if os.path.isfile(file_path):
                        os.chmod(file_path, 0o644)
            
            print(f"\n--- ✅ {test_type.title()} Test Finished ---")
            
            # Auto-generate PDF report from the live dashboard
            sanitized_name = re.sub(r'[^a-z0-9_.-]', '_', chosen_request['name'].lower())
            report_base_name = f"{sanitized_name}-{chosen_request['method'].lower()}-{test_type}"
            
            # Run the async function to generate the PDF
            asyncio.run(generate_pdf_from_dashboard(os.path.join(results_dir, report_base_name)))

            print("--- Dashboard data updated. Refresh your browser. ---")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"\n--- ❌ An error occurred during the {test_type.title()} Test ---")
            break

    print("\nAll selected tests have finished. To stop the web server, run: docker compose down")

if __name__ == "__main__":
    main()