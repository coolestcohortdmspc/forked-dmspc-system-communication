import http from 'k6/http';
import { check, fail } from 'k6';

export const options = {
  scenarios: {
    authenticated_smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
    },
  },

  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000'],
    checks: ['rate>0.99'],
  },

  tags: {
    test_type: 'authenticated_smoke',
    service: 'ngradar_website',
  },
};

const baseUrl = __ENV.K6_BASE_URL || 'http://ngradar-website:8000';
const username = __ENV.K6_USERNAME;
const password = __ENV.K6_PASSWORD;

export default function () {
  if (!username || !password) {
    fail('K6_USERNAME and K6_PASSWORD must be provided');
  }

  const loginPage = http.get(`${baseUrl}/login/`, {
    tags: { endpoint: 'login_page' },
  });

  check(loginPage, {
    'login page returns 200': (r) => r.status === 200,
  });

  const csrfMatch = loginPage.body.match(
    /name=["']csrfmiddlewaretoken["'][^>]*value=["']([^"']+)["']/
  );

  if (!csrfMatch) {
    fail('Could not find Django CSRF token in login page');
  }

  const csrfToken = csrfMatch[1];

  const loginResponse = http.post(
    `${baseUrl}/login/`,
    {
      username: username,
      password: password,
      csrfmiddlewaretoken: csrfToken,
      next: '/home/',
    },
    {
      headers: {
        Referer: `${baseUrl}/login/`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      redirects: 0,
      tags: { endpoint: 'login_submit' },
    }
  );

  check(loginResponse, {
    'login redirects after success': (r) =>
      r.status === 302 || r.status === 303,
    'login sets Django session cookie': (r) =>
      Boolean(r.cookies.sessionid),
  });

  const homeResponse = http.get(`${baseUrl}/home/`, {
    tags: { endpoint: 'home' },
  });

  check(homeResponse, {
    'home returns 200': (r) => r.status === 200,
    'home does not redirect to login': (r) =>
      !r.url.includes('/login/'),
  });
}
