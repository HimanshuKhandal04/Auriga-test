const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL;

function getApiBaseUrl(): string {
  if (configuredApiUrl) return configuredApiUrl;

  if (typeof window !== "undefined") {
    const { hostname, protocol } = window.location;
    if (hostname.endsWith("-3000.app.github.dev")) {
      return `${protocol}//${hostname.replace(/-3000\.app\.github\.dev$/, "-8000.app.github.dev")}`;
    }
  }

  return "http://localhost:8000";
}

export type VehicleType = "COMPACT" | "STANDARD" | "EV";
export type SpotType = "COMPACT" | "STANDARD" | "EV";
export type TokenResponse = { access_token: string; token_type: string };
export type SessionItem = { session_id: number; license_plate: string; vehicle_type: VehicleType; spot_number: string; floor: number; check_in: string; check_out: string | null; fee: string | number | null; status: string };
export type SpotItem = { spot_id: number; spot_number: string; floor: number; spot_type: SpotType; is_occupied: boolean; created_at: string };
export type Paginated<T> = { items: T[]; pagination: { page: number; page_size: number; total: number; total_pages: number } };
export type EvAvailability = { total_ev_spots: number; occupied_ev_spots: number; available_ev_spots: number };
export type CheckInResponse = { session_id: number; license_plate: string; vehicle_type: VehicleType; spot_number: string; floor: number; check_in: string };
export type CheckOutResponse = { license_plate: string; spot_number: string; check_in: string; check_out: string; billable_hours: number; fee: string | number };

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${getApiBaseUrl()}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `API request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string | Array<{ msg?: string }> };
      if (typeof body.detail === "string") message = body.detail;
      if (Array.isArray(body.detail)) message = body.detail.map((item) => item.msg ?? "Invalid request").join(", ");
    } catch { /* Keep the status-based message. */ }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export function jsonBody(value: unknown): RequestInit { return { method: "POST", body: JSON.stringify(value) }; }
