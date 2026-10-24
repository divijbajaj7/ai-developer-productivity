const shortenForm = document.getElementById('shorten-form');
const statsForm = document.getElementById('stats-form');
const apiKeyInput = document.getElementById('api-key');
const longUrlInput = document.getElementById('long-url');
const statsCodeInput = document.getElementById('stats-code');

const shortenResult = document.getElementById('shorten-result');
const shortUrlLink = document.getElementById('short-url');
const copyButton = document.getElementById('copy-link');

const statsResult = document.getElementById('stats-result');
const statsCodeValue = document.getElementById('stats-code-value');
const statsLongUrlLink = document.getElementById('stats-long-url');
const statsClicks = document.getElementById('stats-clicks');

function getApiKey() {
  return apiKeyInput.value.trim() || 'dev-key';
}

function showMessage(element, message, type) {
  element.textContent = message;
  element.className = `status-${type}`;
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'X-API-Key': getApiKey(),
      ...(options.headers || {}),
    },
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const message = data.detail || 'Request failed';
    throw new Error(message);
  }

  return data;
}

shortenForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const url = longUrlInput.value.trim();
  if (!url) return;

  try {
    const payload = await apiRequest('/shorten', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    const shortUrl = payload.short_url;
    shortUrlLink.href = shortUrl;
    shortUrlLink.textContent = shortUrl;
    shortenResult.classList.remove('hidden');
    showMessage(document.createElement('div'), '', 'success');
  } catch (error) {
    alert(`Could not shorten URL: ${error.message}`);
  }
});

copyButton.addEventListener('click', async () => {
  const url = shortUrlLink.href;
  if (!url) return;

  try {
    await navigator.clipboard.writeText(url);
    copyButton.textContent = 'Copied!';
    setTimeout(() => {
      copyButton.textContent = 'Copy';
    }, 1200);
  } catch (error) {
    alert('Unable to copy URL automatically. You can still copy it manually.');
  }
});

statsForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const code = statsCodeInput.value.trim();
  if (!code) return;

  try {
    const payload = await apiRequest(`/stats/${encodeURIComponent(code)}`);

    statsCodeValue.textContent = payload.code;
    statsLongUrlLink.href = payload.long_url;
    statsLongUrlLink.textContent = payload.long_url;
    statsClicks.textContent = payload.clicks;
    statsResult.classList.remove('hidden');
  } catch (error) {
    alert(`Could not load stats: ${error.message}`);
  }
});
