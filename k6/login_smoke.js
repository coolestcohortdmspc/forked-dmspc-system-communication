import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.K6_BASE_URL || 'http://ngradar-website:8000';

export const options = {
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
    },
  },

  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.99'],
  },

  tags: {
    test_type: 'login_smoke',
    service: 'ngradar_website',
  },
};

export default function () {
  const response = http.get(`${BASE_URL}/login/`, {
    tags: {
      endpoint: 'login',
    },
  });

  check(response, {
    'health endpoint returns 2xx or 3xx': (r) =>
      r.status >= 200 && r.status < 400,
    'health endpoint responds within 500 ms': (r) =>
      r.timings.duration < 500,  });

  sleep(1);
}