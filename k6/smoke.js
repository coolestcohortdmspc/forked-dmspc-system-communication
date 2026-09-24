import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const failedRequests = new Rate('failed_requests');

export const options = {
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '10s',
    },
  },

  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    failed_requests: ['rate<0.01'],
  },
};

export default function () {
  const baseUrl = __ENV.K6_BASE_URL || 'http://ngradar-website:8000';
  const url = `${baseUrl}/health/`;

  const response = http.get(url);

  console.log(
    `GET ${url} -> status=${response.status}, url=${response.url}`,
  );

  const successfulResponse = check(response, {
    'status is 2xx or 3xx': (r) => r.status >= 200 && r.status < 400,
  });

  failedRequests.add(!successfulResponse);

  sleep(1);
}
