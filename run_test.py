import os
import subprocess
import sys
import json
import re
import asyncio
import shutil
import argparse  
from jsonschema import validate, ValidationError

# --- 1. SETUP & UTILS ---

def load_secrets(project_dir):
    """Loads .env file from the project directory into environment variables"""
    env_path = os.path.join(project_dir, '.env')
    if os.path.exists(env_path):
        print(f"--- 🔑 Loading secrets from {env_path} ---")
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    try:
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value.strip().strip('"').strip("'")
                    except ValueError: pass

schema = {
    "type": "object",
    "properties": {
        "baseUrl": {"type": "string"},
        "peakUsers": {"type": "integer", "minimum": 1},
        "requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
                    "endpoint": {"type": "string"},
                    "expectedStatus": {"type": "integer"},
                    "testTypes": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["smoke", "load", "stress", "spike", "soak"]}
                    },
                    "payload": {"type": "object"},
                    "contentType": {"type": "string"},
                    "authToken": {"type": "string"},
                    "thresholds": {"type": "object"}
                },
                "required": ["name", "method", "endpoint"]
            }
        }
    },
    "required": ["baseUrl", "peakUsers", "requests"]
}

def validate_config(config_data):
    try:
        validate(instance=config_data, schema=schema)
        print("--- ✅ Config validated successfully ---")
    except ValidationError as e:
        print(f"--- ❌ Config validation failed: {e.message} ---")
        sys.exit(1)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# --- 2. PDF GENERATION (Playwright) ---
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

async def generate_pdf_from_dashboard(dashboard_url, pdf_path):
    if not PLAYWRIGHT_AVAILABLE:
        print("\n--- ⚠️ PDF Generation Skipped (Playwright not installed) ---")
        return

    try:
        print(f"\n--- Generating PDF from dashboard at {dashboard_url} ---")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            context = await browser.new_context(viewport={"width": 1440, "height": 1056})
            page = await context.new_page()

            await page.emulate_media(media="print")
            # Inject CSS to fix print layout
            await page.add_style_tag(content="""
                @media print {
                    body { margin: 0; padding: 0; font-size: 9pt; background: #fff !important; color: #000 !important; }
                    .grid { display: grid !important; gap: 5mm; }
                    .grid.kpi { grid-template-columns: repeat(4, 1fr) !important; }
                    .grid.two { display: block !important; page-break-inside: avoid; margin-bottom: 20px; }
                    .grid.three { display: grid !important; grid-template-columns: repeat(3, 1fr) !important; gap: 6mm !important; }
                    section, .card { break-inside: avoid; margin: 2mm 0; padding: 3mm; box-shadow: none; border: 1px solid #ddd; border-radius: 6px; }
                    canvas { width: 100% !important; height: auto !important; max-height: 80mm !important; }
                    .chip, .subtitle, .toolbar, input { display: none !important; }
                    @page { size: A4 landscape; margin: 8mm; }
                }
            """)

            await page.goto(dashboard_url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000) # Give charts time to animate
            await page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                scale=0.85,
                margin={"top": "10mm", "bottom": "10mm", "left": "8mm", "right": "8mm"},
                landscape=True
            )
            await browser.close()
        os.chmod(pdf_path, 0o644)
        print(f"--- ✅ PDF report saved to {pdf_path} ---")
    except Exception as e:
        print(f"\n--- ❌ PDF Generation Error: {e} ---")

# --- 3. HTML REPORT GENERATION ---
def generate_comprehensive_dashboard(report_list, output_path):
    template_path = 'scripts/templates/multi_report.html'
    
    if not os.path.exists(template_path):
        print(f"⚠️ Template missing: {template_path}")
        return

    try:
        with open(template_path, 'r') as f:
            html_content = f.read()
            
        # Inject data into the template placeholder
        json_data = json.dumps(report_list)
        final_html = html_content.replace('{{REPORT_LIST_JSON}}', json_data)
        
        with open(output_path, 'w') as f:
            f.write(final_html)
        os.chmod(output_path, 0o644)
        print(f"--- ✅ HTML Dashboard generated at {output_path} ---")
    except Exception as e:
        print(f"--- ❌ HTML Generation Error: {e} ---")

# --- 4. MAIN EXECUTION ---
def main():
    clear_screen()
    
    # A. Argument Parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to the config.json file")
    args = parser.parse_args()
    config_path = args.config

    # B. Environment Setup
    if not os.path.exists(config_path):
        print(f"❌ Error: Config file not found at {config_path}")
        sys.exit(1)

    project_dir = os.path.dirname(os.path.abspath(config_path))
    load_secrets(project_dir)

    # C. Restore Single Report Template (Vital for Dashboard Viewer)
    single_template = 'scripts/templates/single_report.html'
    if os.path.exists(single_template):
        if not os.path.exists('results'):
            os.makedirs('results')
        shutil.copy(single_template, 'results/dashboardgenerator.html')
    else:
        print(f"⚠️ Warning: Single report template not found at {single_template}")

    # D. Load Config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        validate_config(config)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading 'config.json': {e}. Exiting.")
        sys.exit(1)

    base_url = config.get('baseUrl')
    peak_users = config.get('peakUsers', 10)
    requests = config.get('requests', [])
    
    print(f"✅ Base URL: {base_url}")
    print(f"✅ Peak Users: {peak_users}")
    print(f"✅ Requests: {len(requests)}\n")

    # E. Ensure Web Server is Up
    print("\n--- 🐢 Checking Web Server... ---")
    try:
        subprocess.run(["docker", "compose", "up", "-d", "web-server"], check=True)
    except subprocess.CalledProcessError:
        print("Warning: Could not start web-server.")

    report_list = []
    is_single_request = len(requests) == 1

    # F. Run Tests
    for req_idx, chosen_request in enumerate(requests):
        test_types = chosen_request.get('testTypes', ['smoke'])
        
        # Security & Reliability Logic
        token_key = chosen_request.get('authToken', '')
        resolved_token = os.environ.get(token_key, token_key) 
        thresholds_json = json.dumps(chosen_request.get('thresholds', {}))

        for test_type in test_types:
            print("\n=========================================================")
            print(f"  🚀 Starting: {test_type.title()} Test on '{chosen_request['name']}' (Request {req_idx+1}/{len(requests)})")
            print(f"  Scaling for {peak_users} peak VUs")
            print("=========================================================\n")

            # 1. PRE-CALCULATE FILENAMES (Do this BEFORE running)
            sanitized_name = re.sub(r'[^a-z0-9_.-]', '_', chosen_request['name'].lower())
            report_base_name = f"{sanitized_name}-{chosen_request['method'].lower()}-{test_type}"
            csv_path = f"{report_base_name}-results.csv"
            meta_path = f"{report_base_name}-metadata.json"

            env_vars = {
                "BASE_URL": base_url,
                "ENDPOINT": chosen_request['endpoint'],
                "REQUEST_METHOD": chosen_request['method'],
                "REQUEST_NAME": chosen_request['name'],
                "AUTH_TOKEN": resolved_token,
                "THRESHOLDS": thresholds_json,
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

            # 2. RUN TEST (Allow failure)
            try:
                subprocess.run(command, check=True)
                print(f"\n--- ✅ {test_type.title()} Test Passed ---")
            except subprocess.CalledProcessError as e:
                print(f"\n--- ⚠️ {test_type.title()} Test Finished with Threshold Failures (Exit {e.returncode}) ---")
                # We do NOT continue/skip here. We proceed to check for results.

            # 3. COLLECT RESULTS (Check if files exist)
            results_dir = './results'
            full_csv_path = os.path.join(results_dir, csv_path)
            
            if os.path.exists(full_csv_path):
                # Ensure permissions
                try:
                    os.chmod(full_csv_path, 0o644)
                    os.chmod(os.path.join(results_dir, meta_path), 0o644)
                except: pass

                # Add to report list
                report_list.append({
                    "csv": csv_path,
                    "meta": meta_path
                })
                print(f"   📄 Collected results: {csv_path}")

                # Update Single Dashboard if applicable
                if is_single_request:
                    shutil.copy(full_csv_path, os.path.join(results_dir, 'latest_results.csv'))
                    shutil.copy(os.path.join(results_dir, meta_path), os.path.join(results_dir, 'metadata.json'))
                    
                    pdf_path = os.path.join(results_dir, f"{report_base_name}.pdf")
                    dashboard_url = "http://localhost:8069/dashboardgenerator.html"
                    asyncio.run(generate_pdf_from_dashboard(dashboard_url, pdf_path))
                    print("--- Dashboard updated for single request. ---")
            else:
                print(f"❌ Critical Error: No results file found at {full_csv_path}")

    # G. Generate Multi-Report
    if not is_single_request and report_list:
        comp_html_path = os.path.join('results', 'comprehensive_report.html')
        generate_comprehensive_dashboard(report_list, comp_html_path)
        
        pdf_path = os.path.join('results', 'comprehensive_report.pdf')
        dashboard_url = "http://localhost:8069/comprehensive_report.html"
        asyncio.run(generate_pdf_from_dashboard(dashboard_url, pdf_path))

    # H. Cleanup (Optional: Comment out to keep server running)
    print("\n--- 🏁 All tests complete. ---")
    # try:
    #     subprocess.run(["docker", "compose", "down"], check=True)
    # except: pass

if __name__ == "__main__":
    main()