import os
import subprocess
import sys
import json
import re
import asyncio
import shutil
import json
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

async def generate_pdf_from_dashboard(dashboard_url, pdf_path):
    if not PLAYWRIGHT_AVAILABLE:
        print("\n--- ⚠️ PDF Generation Skipped ---")
        print("--- Please run 'pip install playwright' and 'playwright install' to enable this feature. ---")
        return

    try:
        print(f"\n--- Generating PDF from dashboard at {dashboard_url} ---")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            context = await browser.new_context(viewport={"width": 1440, "height": 1056})
            page = await context.new_page()

            # Emulate print media and inject CSS for layout fixes
            await page.emulate_media(media="print")
            await page.add_style_tag(content="""
                @media print {
    body { 
        margin: 0; 
        padding: 0; 
        font-size: 9pt; 
        background: #fff !important; 
        color: #000 !important;
    }

    /* Generic grid */
    .grid { 
        display: grid !important;
        gap: 5mm;
    }

    /* KPIs: 4 per row */
    .grid.kpi { 
        grid-template-columns: repeat(4, 1fr) !important; 
    }

    /* Charts: 2 side by side */
    .grid.two { 
        grid-template-columns: repeat(2, 1fr) !important;
        page-break-inside: avoid;
    }

    /* APIs: 3 per row (clean grid like screenshot) */
    .grid.three { 
        grid-template-columns: repeat(3, 1fr) !important;
        gap: 6mm !important;
        page-break-inside: avoid;
    }

    /* Section & card adjustments */
    section, .card { 
        page-break-inside: avoid;
        page-break-after: auto;
        margin: 2mm 0;
        padding: 3mm; 
        box-shadow: none; 
        border: 1px solid #ddd;
        border-radius: 6px;
    }

    /* Chart size */
    canvas { 
        width: 100% !important; 
        height: auto !important; 
        max-height: 95mm;
    }

    /* API card compact styling */
    .api-card {
        padding: 6px 8px !important;
        font-size: 9pt !important;
        border: 1px solid #ddd;
        border-radius: 6px;
        height: auto;
        break-inside: avoid;
    }

    .api-card h3 {
        font-size: 11pt !important;
        margin: 0 0 4px 0 !important;
    }

    .api-card .kpi {
        display: flex;
        justify-content: space-between;
        margin: 2px 0;
        padding: 0;
    }

    .api-card .kpi .label {
        font-size: 8pt !important;
        color: #666;
    }

    .api-card .kpi .value {
        font-size: 10pt !important;
        font-weight: 600;
    }

    /* Alternate shading for readability */
    .api-card:nth-child(even) {
        background: #f9f9f9 !important;
    }

    /* Hide non-essentials */
    .chip, .subtitle, .filter, input { 
        display: none !important;
    }

    /* Page size/orientation */
    @page { 
        size: A4 landscape;
        margin: 8mm;
    }

    /* Avoid orphan/widow headers */
    h1, h2, h3 { 
        page-break-after: avoid; 
    }
}

    /* Force break before API details if needed */
    .api-details-section { /* Add this class to the APIs detail container in HTML if possible */
        page-break-before: always;
    }
}
            """)

            await page.goto(dashboard_url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(10000)  # Longer for JS/charts to settle
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
        print(f"\n--- ❌ An error occurred during PDF generation: {e} ---")
        if 'page' in locals() and page:
            try:
                await page.screenshot(path='debug.png', timeout=10000)
                print("--- Debug screenshot saved to debug.png ---")
            except Exception as se:
                print(f"--- ❌ Screenshot failed: {se} ---")
        print("--- Ensure the web-server container is running. ---")
        
def generate_comprehensive_dashboard(report_list, output_path):
    report_json = json.dumps(report_list)

    template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Comprehensive Performance Report</title>
  <link rel="icon" type="image/png" href="/favicon.png" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>
    :root {
      --bg: #ffffff;
      --panel: #ffffff;
      --card: #ffffff;
      --muted: #475569;
      --text: #0f172a;
      --accent: #2563eb;
      --success: #4088d9;
      --warn: #d97706;
      --error: #dc2626;
      --link: #2563eb;
      --chip: #eef2f7;
      --border: #e6e6e6;
      --shadow: none;
    }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 12px/1.4 system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica, Arial; /* Slightly smaller font */
    }
    .wrap { max-width:1180px; margin:12px auto 24px; padding:0 8px; } /* Reduced margins and padding */
    header {
      position: sticky; top: 0; z-index: 10;
      backdrop-filter: saturate(180%) blur(10px);
      background: var(--panel);
      border-bottom: 1px solid var(--border);
    }
    .bar { max-width:1180px; margin:0 auto; display:flex; gap:8px; align-items:center; padding:8px 12px; } /* Reduced padding and gap */
    .title { font-weight:700; letter-spacing:.1px; font-size: 18px; } /* Slightly smaller title */
    .subtitle { color: var(--muted); font-size:11px; }
    .chip { background: var(--chip); border: 1px solid var(--border); color: var(--text); padding:4px 8px; border-radius:999px; font-size:10px; } /* Reduced padding and font */
    .grid { display:grid; gap:8px; } /* Reduced gap */
    .grid.kpi { grid-template-columns: repeat(4, minmax(0,1fr)); }
    .grid.two { grid-template-columns: repeat(2, minmax(0,1fr)); }
    .grid.three { grid-template-columns: repeat(3, minmax(0,1fr)); }
    @media (max-width:1100px) {
      .grid.kpi { grid-template-columns: repeat(2, minmax(0,1fr)); }
      .grid.two, .grid.three { grid-template-columns: repeat(1, minmax(0,1fr)); }
    }
    section {
      background: var(--panel); border:1px solid var(--border); border-radius:8px; padding:8px 8px 6px; /* Reduced padding and radius */
    }
    .kpi {
      background: var(--card); border:1px solid var(--border); border-radius:8px;
      padding:8px 8px 6px; display:flex; align-items:baseline; justify-content:space-between; gap:4px; /* Reduced padding and gap */
    }
    .kpi .label { color: var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:.05em; } /* Smaller font */
    .kpi .value { font-size:18px; font-weight:700; } /* Slightly smaller value */
    .chip { display:inline-block; }
    .toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom: 10px; } /* Reduced gap and margin */
    .toolbar input {
      background: var(--card); border:1px solid var(--border); border-radius:8px;
      padding:6px 8px; color: var(--text); outline:none; min-width:200px; /* Reduced padding and width */
    }
    h1,h2,h3{ margin:0; }
    h2{ font-size:16px; margin-bottom:6px; } /* Reduced font and margin */
    .card {
      background: #fff;
      border: 1px solid var(--border);
      border-radius:8px;
      padding:8px 8px 6px;
      box-shadow: var(--shadow);
    }
    @media print {
  body { 
    margin: 0; 
    padding: 0; 
    font-size: 9pt; 
  }

  /* KPIs: keep 4 per row */
  .grid.kpi { 
    grid-template-columns: repeat(4, 1fr) !important; 
    gap: 4mm !important;
  }

  /* Graphs: don't force side by side, keep natural layout (stacked) */
  .grid.two { 
    display: block !important; 
    gap: 6mm !important;
  }

  /* API cards: enforce 3 per row (grid view) */
  .grid.three { 
    display: grid !important; 
    grid-template-columns: repeat(3, 1fr) !important; 
    gap: 6mm !important;
  }

  /* Cards and sections */
  section, .card { 
    break-inside: avoid; 
    margin: 2mm 0; 
    padding: 3mm; 
    box-shadow: none; 
    border: 1px solid #ddd;
    border-radius: 6px;
  }

  /* Charts */
  canvas { 
    width: 100% !important; 
    height: auto !important; 
    max-height: 80mm !important; 
  }

  /* Hide UI elements not needed in PDF */
  .chip, .subtitle, .toolbar, input { 
    display: none !important; 
  }

  /* Header */
  .bar, header { 
    position: relative !important; 
    padding: 2mm !important; 
    border-bottom: 1px solid #ddd;
  }

  @page { 
    size: A4 landscape; 
    margin: 8mm; 
  }
}
    section, .card { 
        break-inside: avoid; 
        margin: 2mm 0; padding: 2mm; /* Reduced margins and padding */
        box-shadow: none; border: none;
    }
    .chip, .subtitle { display: none; }
    .bar, header { position: relative !important; padding: 1mm !important; } /* Tighter header */
    canvas { width: 100% !important; height: auto !important; max-height: 80mm !important; } /* Limit chart height */
    @page { margin: 5mm; } /* Reduced page margins */
    .toolbar { height: 0 !important; margin: 0 !important; padding: 0 !important; overflow: hidden !important; } /* Collapse toolbar */
    .api-card { display: flex; flex-direction: column; gap:6px; } /* Reduced gap */
    .api-head { display: flex; justify-content: space-between; align-items: center; gap:6px; } /* Reduced gap */
  </style>
</head>
<body>
  <header>
    <div class="bar">
      <img src="./logo.png" alt="Company Logo" class="logo" onerror="this.style.display='none';" width="80px" height="80px" /> <!-- Reduced size -->
      <h1 class="title">Comprehensive Performance Report</h1>
    </div>
  </header>
  <div class="wrap">
    <section class="toolbar">
      <input type="text" id="filter" placeholder="Filter by API name or endpoint...">
      <p class="subtitle">Use the search bar to browse API tests.</p>
    </section>
    <div class="grid two">
      <div class="card">
        <h2>Latency comparison</h2>
        <canvas id="latencyChart"></canvas>
        <div class="chip">
          Avg <span style="color:var(--accent)">●</span>
          P90 <span style="color:var(--success)">●</span>
          P95 <span style="color:var(--error)">●</span>
        </div>
      </div>
      <div class="card">
        <h2>Reliability and throughput</h2>
        <canvas id="reliabilityChart"></canvas>
        <div class="chip">
          Error rate <span style="color:var(--error)">●</span>
          RPS <span style="color:var(--success)">●</span>
        </div>
      </div>
    </div>
    <br>
    <section>
      <h2>APIs detail</h2>
      <div id="apiCards" class="grid three"></div>
    </section>
    <p class="subtitle">Created by Third Eye Creative, All rights reserved.</p>
  </div>

  <script>
    const reportList = """ + report_json + """;

    let latencyChart;
    let reliabilityChart;

    async function loadData() {
      const data = [];
      for (const r of reportList) {
        try {
          const metaResp = await fetch(r.meta);
          const meta = await metaResp.json();
          const csvResp = await fetch(r.csv);
          const csvText = await csvResp.text();
          const metrics = parseCsv(csvText);
          data.push({ meta, metrics });
        } catch (e) {
          console.error(`Failed to load ${r.csv} or ${r.meta}:`, e);
        }
      }
      return data;
    }

    function parseCsv(text) {
      const lines = text.split('\\n').slice(1).filter(line => line.trim());
      const result = {};
      lines.forEach(line => {
        const [metric, type, valueStr] = line.split(',', 3);
        const cleanedValue = valueStr.trim().replace(/^"|"$/g, '');
        if (!result[metric]) result[metric] = { type };
        const [key, val] = cleanedValue.split('=');
        result[metric][key] = isNaN(parseFloat(val)) ? val : parseFloat(val);
      });
      return result;
    }

    function renderCharts(filteredData) {
      const labels = filteredData.map(d => `${d.meta.requestName} (${d.meta.testType})`);

      if (latencyChart) latencyChart.destroy();
      const latencyCtx = document.getElementById('latencyChart').getContext('2d');
      latencyChart = new Chart(latencyCtx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            { label: 'Avg', data: filteredData.map(d => d.metrics.http_req_duration.avg), backgroundColor: '#2563eb' },
            { label: 'P90', data: filteredData.map(d => d.metrics.http_req_duration['p(90)']), backgroundColor: '#4088d9' },
            { label: 'P95', data: filteredData.map(d => d.metrics.http_req_duration['p(95)']), backgroundColor: '#ef4444' }
          ]
        },
        options: {
          responsive: true,
          scales: { y: { beginAtZero: true, title: { display: true, text: 'ms' } } }
        }
      });

      if (reliabilityChart) reliabilityChart.destroy();
      const reliabilityCtx = document.getElementById('reliabilityChart').getContext('2d');
      reliabilityChart = new Chart(reliabilityCtx, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            { label: 'Error Rate (%)', data: filteredData.map(d => (d.metrics.http_req_failed ? d.metrics.http_req_failed.rate * 100 : 0)), backgroundColor: '#ef4444' },
            { label: 'RPS', data: filteredData.map(d => d.metrics.http_reqs.rate), backgroundColor: '#2563eb' }
          ]
        },
        options: {
          responsive: true,
          scales: { y: { beginAtZero: true } }
        }
      });
    }

    function renderCards(filteredData) {
      const container = document.getElementById('apiCards');
      container.innerHTML = '';
      filteredData.forEach(d => {
        const card = document.createElement('div');
        card.className = 'card api-card';
        card.innerHTML = `
          <div class="api-head">
            <h3>${d.meta.requestName} (${d.meta.testType})</h3>
            <span class="chip">${d.meta.requestMethod} ${d.meta.endpoint}</span>
          </div>
            <div class="kpi">
              <div class="label">Total Requests</div>
              <div class="value">${Math.round(d.metrics.http_reqs.count || 0)}</div>
            </div>
            <div class="kpi">
              <div class="label">Avg Response (ms)</div>
              <div class="value">${d.metrics.http_req_duration.avg.toFixed(2)}</div>
            </div>
            <div class="kpi">
              <div class="label">Failure Rate</div>
              <div class="value">${(d.metrics.http_req_failed ? (d.metrics.http_req_failed.rate * 100).toFixed(2) : 0)}%</div>
            </div>
            <div class="kpi">
              <div class="label">Max VUs</div>
              <div class="value">${d.metrics.vus_max.value || 'N/A'}</div>
            </div>
        `;
        container.appendChild(card);
      });
    }

    window.onload = async () => {
      const data = await loadData();
      if (data.length === 0) {
        console.error('No data loaded from reports');
        return;
      }
      renderCharts(data);
      renderCards(data);

      const filterInput = document.getElementById('filter');
      filterInput.addEventListener('input', () => {
        const term = filterInput.value.toLowerCase();
        const filtered = data.filter(d =>
          d.meta.requestName.toLowerCase().includes(term) ||
          d.meta.endpoint.toLowerCase().includes(term)
        );
        renderCharts(filtered);
        renderCards(filtered);
      });
    };
  </script>
</body>
</html>
    """

    with open(output_path, 'w') as f:
        f.write(template)
    os.chmod(output_path, 0o644)
def main():
    clear_screen()

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        requests = config.get('requests', [])
        base_url = config.get('baseUrl')
        peak_users = config.get('peakUsers', 10)
        if not requests or not base_url:
            print("Error: 'config.json' must contain 'baseUrl' and a 'requests' list. Exiting.")
            sys.exit(1)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading 'config.json': {e}. Exiting.")
        sys.exit(1)

    print(f"✅ Base URL loaded from config: {base_url}")
    print(f"✅ Peak Users: {peak_users}")
    print(f"✅ Total Requests to Test: {len(requests)}\n")

    is_single_request = len(requests) == 1

    print("\n--- Starting web server... ---")
    try:
        subprocess.run(["docker", "compose", "up", "-d", "--build", "web-server"], check=True)
        print(f"Web server is running on http://localhost:8069/")
    except subprocess.CalledProcessError as e:
        print(f"Error starting web server: {e}. Exiting.")
        sys.exit(1)

    report_list = []

    for req_idx, chosen_request in enumerate(requests):
        test_types = chosen_request.get('testTypes', ['smoke'])
        auth_token = chosen_request.get('authToken', '')

        for test_type in test_types:
            print("\n=========================================================")
            print(f"  🚀 Starting: {test_type.title()} Test on '{chosen_request['name']}' (Request {req_idx+1}/{len(requests)})")
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
                
                sanitized_name = re.sub(r'[^a-z0-9_.-]', '_', chosen_request['name'].lower())
                report_base_name = f"{sanitized_name}-{chosen_request['method'].lower()}-{test_type}"
                csv_path = f"{report_base_name}-results.csv"
                meta_path = f"{report_base_name}-metadata.json"
                
                report_list.append({
                    "csv": csv_path,
                    "meta": meta_path
                })

                if is_single_request:
                    shutil.copy(os.path.join(results_dir, csv_path), os.path.join(results_dir, 'latest_results.csv'))
                    shutil.copy(os.path.join(results_dir, meta_path), os.path.join(results_dir, 'metadata.json'))
                    
                    pdf_path = os.path.join(results_dir, f"{report_base_name}.pdf")
                    dashboard_url = "http://localhost:8069/dashboardgenerator.html"
                    asyncio.run(generate_pdf_from_dashboard(dashboard_url, pdf_path))
                    print("--- Dashboard data updated for single request. Refresh your browser at http://localhost:8069/dashboardgenerator.html ---")

            except subprocess.CalledProcessError as e:
                print(f"\n--- ❌ Error during {test_type.title()} Test on '{chosen_request['name']}': {e} ---")
                print("--- Skipping this test and continuing... ---")
                continue

    if not is_single_request and report_list:
        comp_html_path = os.path.join('./results', 'comprehensive_dashboard.html')
        generate_comprehensive_dashboard(report_list, comp_html_path)
        print("\n--- ✅ Comprehensive dashboard generated at results/comprehensive_dashboard.html ---")
        
        pdf_path = os.path.join('./results', 'comprehensive_report.pdf')
        dashboard_url = "http://localhost:8069/comprehensive_dashboard.html"
        asyncio.run(generate_pdf_from_dashboard(dashboard_url, pdf_path))
        print("--- View comprehensive dashboard at http://localhost:8069/comprehensive_dashboard.html ---")

    print("\nAll tests have finished. Stopping web server...")
    try:
        subprocess.run(["docker", "compose", "down"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error stopping web server: {e}. Server may still be running.")

if __name__ == "__main__":
    main()