const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

async function get(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json();
}

export function getDestinations() {
  return get("/destinations");
}

export function getPlaces(destinationId) {
  const query = new URLSearchParams({ destination_id: String(destinationId) });
  return get(`/places?${query.toString()}`);
}
