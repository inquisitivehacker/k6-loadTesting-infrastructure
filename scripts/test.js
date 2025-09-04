import http from 'k6/http';
import { sleep, check } from 'k6';
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";
import { textSummary } from "https://jslib.k6.io/k6-summary/0.0.1/index.js";

// Get all generic variables from the environment
const testType = __ENV.TEST_TYPE;
const baseUrl = __ENV.BASE_URL;
const endpoint = __ENV.ENDPOINT;
const requestMethod = __ENV.REQUEST_METHOD.toUpperCase();
const authToken = __ENV.AUTH_TOKEN;
const requestPayload = __ENV.REQUEST_PAYLOAD;
const contentType = __ENV.CONTENT_TYPE;
const expectedStatus = parseInt(__ENV.EXPECTED_STATUS);
const peakVUs = parseInt(__ENV.PEAK_VUS);
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
  soak: { executor: 'constant-vus', vus: Math.round(peakVUs * 0.8), duration: '1h' },
};

export const options = profiles[testType];

export default function () {
  let res;
  const tags = { name: targetUrl, test_type: testType };
  
  let payloadObject = {};
  if (requestPayload && requestPayload !== '{}') {
    payloadObject = JSON.parse(requestPayload);
  }

  let body = null;
  let headers = { ...requestHeaders };
  if (contentType === 'application/json') {
    body = JSON.stringify(payloadObject);
    headers['Content-Type'] = 'application/json';
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
  } else if (contentType.includes('form')) {  // Handles multipart or urlencoded
    if (authToken) {
      payloadObject.token = authToken;
    }
    body = payloadObject;  // k6 handles form encoding
    if (contentType === 'application/x-www-form-urlencoded') {
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
    }  // multipart is default, no Content-Type needed
  } else {
    // Other types: assume raw body, set Content-Type
    body = JSON.stringify(payloadObject);  // Or handle as string if needed
    headers['Content-Type'] = contentType;
  }

  const params = { headers, tags };

  // Use generic http.request for any method
  res = http.request(requestMethod, targetUrl, body, params);
  
  // DEBUGGING: Log the response status and body on the first iteration
  if (__ITER === 0) {
    console.log(`-- Response Debug Info --`);
    console.log(`Response status: ${res.status}`);
    console.log(`Response body: ${res.body}`);
  }

  check(res, {
    [`status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
  });
  
  sleep(1);
}

export function handleSummary(data) {
  const testName = `${testType}_${requestMethod}`.toLowerCase();
  return {
    '/results/latest_results.csv': jsonToCsv(data),
    [`/results/${testName}-report-${Date.now()}.html`]: htmlReport(data),
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