import http from 'k6/http';
import { sleep, check } from 'k6';
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";
import { textSummary } from "https://jslib.k6.io/k6-summary/0.0.1/index.js";
import { jUnit } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js';

// Get all generic variables from the environment
const testType = __ENV.TEST_TYPE;
const baseUrl = __ENV.BASE_URL;
const endpoint = __ENV.ENDPOINT;
const requestMethod = __ENV.REQUEST_METHOD.toUpperCase();
const requestName = __ENV.REQUEST_NAME;
const authToken = __ENV.AUTH_TOKEN;
const requestPayload = __ENV.REQUEST_PAYLOAD;
const contentType = __ENV.CONTENT_TYPE;
const expectedStatus = parseInt(__ENV.EXPECTED_STATUS);
const peakVUs = parseInt(__ENV.PEAK_VUS);
const customThresholds = JSON.parse(__ENV.THRESHOLDS || '{}');
const requestHeaders = JSON.parse(__ENV.REQUEST_HEADERS || '{}');
const queryParams = JSON.parse(__ENV.QUERY_PARAMS || '{}');

let targetUrl = `${baseUrl}${endpoint}`;
if (Object.keys(queryParams).length > 0) {
  const paramsStr = Object.entries(queryParams).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
  targetUrl += `?${paramsStr}`;
}

const profiles = {
  smoke: { executor: 'constant-vus', vus: 1, duration: '10s' },
  load: { executor: 'ramping-vus', stages: [ { duration: '2m', target: peakVUs }, { duration: '5m', target: peakVUs }, { duration: '1m', target: 0 } ] },
  stress: { executor: 'ramping-vus', stages: [ { duration: '2m', target: peakVUs }, { duration: '3m', target: peakVUs }, { duration: '2m', target: Math.round(peakVUs * 1.5) }, { duration: '3m', target: Math.round(peakVUs * 1.5) }, { duration: '2m', target: Math.round(peakVUs * 2) }, { duration: '3m', target: Math.round(peakVUs * 2) }, { duration: '5m', target: 0 } ] },
  spike: { executor: 'ramping-vus', stages: [ { duration: '1m', target: Math.round(peakVUs * 0.25) }, { duration: '2m', target: Math.round(peakVUs * 0.25) }, { duration: '10s', target: Math.round(peakVUs * 2.5) }, { duration: '2m', target: Math.round(peakVUs * 2.5) }, { duration: '10s', target: Math.round(peakVUs * 0.25) }, { duration: '2m', target: Math.round(peakVUs * 0.25) }, { duration: '10s', target: 0 } ] },
  soak: { executor: 'constant-vus', vus: Math.round(peakVUs * 0.8), duration: '3m' },
};

export const options = {
  ...profiles[testType],
  thresholds: {
    http_req_failed: ['rate<0.01'], // Global Safety: Fail if >1% errors
    ...customThresholds // Merge project specific overrides
  }
};

export default function () {
  const tags = { name: targetUrl, test_type: testType };
  const payloadObject = JSON.parse(requestPayload || '{}');

  let body = null;
  let headers = { ...requestHeaders };
  if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
  }
  
  if (contentType === 'application/json') {
    body = JSON.stringify(payloadObject);
    headers['Content-Type'] = 'application/json';
  } else { // Handles multipart/form-data and urlencoded
    body = payloadObject;
  }

  const params = { headers, tags };
  const res = http.request(requestMethod, targetUrl, body, params);
  
  check(res, {
    [`status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
  });
  
  sleep(1);
}

export function handleSummary(data) {
  const sanitizedName = requestName.replace(/[^a-z0-9_.-]/gi, '_').toLowerCase();
  const reportFilename = `${sanitizedName}-${requestMethod.toLowerCase()}-${testType}`;

  const metadata = {
    baseUrl: baseUrl,
    requestName: requestName,
    requestMethod: requestMethod,
    endpoint: endpoint,
    testType: testType,
    timestamp: new Date().toISOString(),
  };

  return {
    [`/results/${reportFilename}-results.csv`]: jsonToCsv(data),
    [`/results/${reportFilename}-metadata.json`]: JSON.stringify(metadata, null, 2),
    [`/results/${reportFilename}.html`]: htmlReport(data, { title: `${requestName} - ${testType.charAt(0).toUpperCase() + testType.slice(1)} Test` }),
    [`/results/${reportFilename}.xml`]: jUnit(data),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function jsonToCsv(jsonData) {
  const metrics = Object.keys(jsonData.metrics);
  let csv = 'metric,type,value\n';
  metrics.forEach(metric => {
    const metricData = jsonData.metrics[metric];
    const type = metricData.type;
    if (metricData.values) {
      Object.keys(metricData.values).forEach(valueKey => {
        csv += `${metric},${type},"${valueKey}=${metricData.values[valueKey]}"\n`;
      });
    }
  });
  return csv;
}