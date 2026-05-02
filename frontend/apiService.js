const API_BASE = "";

async function request(url, options = {}) {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    const message = errorPayload.detail || "Request failed.";
    throw new Error(message);
  }

  return response.json();
}

export function fetchGoldMarketData(currency = "MYR", range = "5y", interval = "1d") {
  const params = new URLSearchParams({
    currency,
    range,
    interval,
  });
  return request(`/get-gold-price?${params.toString()}`);
}

export function fetchForecast(payload) {
  return request("/forecast", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchMalaysiaLivePrice() {
  return request("/malaysia-live-price");
}
