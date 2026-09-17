"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  apiRequest,
  CheckInResponse,
  CheckOutResponse,
  EvAvailability,
  jsonBody,
  Paginated,
  SessionItem,
  SpotItem,
  VehicleType,
} from "../../lib/api";

const inputClass = "mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400";
const buttonClass = "rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-wait disabled:opacity-50";

function formatDate(value: string) { return new Date(value).toLocaleString([], { dateStyle: "short", timeStyle: "short" }); }
function fee(value: string | number | null) { return value == null ? "—" : `$${Number(value).toFixed(2)}`; }

export default function DashboardPage() {
  const [token, setToken] = useState<string | null>(null);
  const [active, setActive] = useState<SessionItem[]>([]);
  const [spots, setSpots] = useState<SpotItem[]>([]);
  const [ev, setEv] = useState<EvAvailability | null>(null);
  const [searchResults, setSearchResults] = useState<SessionItem[]>([]);
  const [plate, setPlate] = useState("");
  const [vehicleType, setVehicleType] = useState<VehicleType>("STANDARD");
  const [checkInPlate, setCheckInPlate] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    setToken(localStorage.getItem("parkflow_token"));
  }, []);

  async function refresh() {
    setLoading(true);
    try {
      const [activeResponse, spotsResponse, evResponse] = await Promise.all([
        apiRequest<Paginated<SessionItem>>("/api/parking/active?page=1&page_size=100&sort=check_in&order=desc"),
        apiRequest<Paginated<SpotItem>>("/api/spots?page=1&page_size=100&sort=floor&order=asc"),
        apiRequest<EvAvailability>("/api/spots/ev/availability"),
      ]);
      setActive(activeResponse.items);
      setSpots(spotsResponse.items);
      setEv(evResponse);
      setError("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load garage data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function checkIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true); setMessage(""); setError("");
    try {
      const result = await apiRequest<CheckInResponse>("/api/parking/check-in", jsonBody({ license_plate: checkInPlate, vehicle_type: vehicleType }));
      setMessage(`${result.license_plate} assigned to ${result.spot_number} on floor ${result.floor}.`);
      setCheckInPlate("");
      await refresh();
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Check-in failed"); }
    finally { setWorking(false); }
  }

  async function checkout(sessionId: number) {
    setWorking(true); setMessage(""); setError("");
    try {
      const result = await apiRequest<CheckOutResponse>("/api/parking/check-out", jsonBody({ session_id: sessionId }));
      setMessage(`${result.license_plate} checked out. Fee: ${fee(result.fee)}.`);
      await refresh();
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Checkout failed"); }
    finally { setWorking(false); }
  }

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!plate.trim()) return;
    setWorking(true); setError("");
    try {
      const result = await apiRequest<Paginated<SessionItem>>(`/api/parking/search?plate=${encodeURIComponent(plate)}&page=1&page_size=50`);
      setSearchResults(result.items);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Search failed"); }
    finally { setWorking(false); }
  }

  function logout() { localStorage.removeItem("parkflow_token"); setToken(null); }
  if (token === null) return <main className="grid min-h-screen place-items-center bg-slate-950 px-6 text-slate-100"><div className="max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center"><h1 className="text-2xl font-semibold">Sign in to ParkFlow</h1><p className="mt-3 text-slate-400">Use an operator account to access the garage dashboard.</p><Link href="/login" className={`${buttonClass} mt-7 inline-block`}>Go to login</Link></div></main>;

  const available = spots.filter((spot) => !spot.is_occupied).length;
  const occupied = spots.filter((spot) => spot.is_occupied).length;
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100"><div className="mx-auto max-w-7xl px-5 py-6 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-800 pb-6 sm:flex-row sm:items-center sm:justify-between"><div><Link href="/" className="text-sm font-semibold text-cyan-300">ParkFlow</Link><h1 className="mt-2 text-3xl font-semibold tracking-tight">Garage dashboard</h1><p className="mt-1 text-sm text-slate-500">Live operations overview</p></div><button onClick={logout} className="self-start rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500">Log out</button></header>
      {error && <p className="mt-5 rounded-lg border border-rose-900 bg-rose-950/40 px-4 py-3 text-sm text-rose-300">{error}</p>}{message && <p className="mt-5 rounded-lg border border-emerald-900 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-300">{message}</p>}
      <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Stat label="Total spaces" value={loading ? "..." : spots.length} /><Stat label="Available" value={loading ? "..." : available} tone="text-emerald-300" /><Stat label="Occupied" value={loading ? "..." : occupied} tone="text-amber-300" /><Stat label="EV available" value={loading ? "..." : ev?.available_ev_spots ?? 0} tone="text-cyan-300" /></section>
      <section className="mt-8 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]"><div className="rounded-2xl border border-slate-800 bg-slate-900 p-5"><h2 className="text-lg font-semibold">Check in vehicle</h2><form onSubmit={checkIn} className="mt-5 space-y-4"><label className="block text-sm text-slate-300">License plate<input required value={checkInPlate} onChange={(event) => setCheckInPlate(event.target.value)} placeholder="ABC-123" className={inputClass} /></label><label className="block text-sm text-slate-300">Vehicle type<select value={vehicleType} onChange={(event) => setVehicleType(event.target.value as VehicleType)} className={inputClass}><option value="COMPACT">Compact</option><option value="STANDARD">Standard</option><option value="EV">EV</option></select></label><button disabled={working} className={buttonClass}>Assign compatible spot</button></form></div><div className="rounded-2xl border border-slate-800 bg-slate-900 p-5"><div className="flex items-center justify-between"><div><h2 className="text-lg font-semibold">Find a plate</h2><p className="mt-1 text-sm text-slate-500">Search active and completed sessions.</p></div></div><form onSubmit={search} className="mt-5 flex gap-3"><input required value={plate} onChange={(event) => setPlate(event.target.value)} placeholder="Search plate" className={inputClass.replace("mt-2 ", "mt-0 ")} /><button disabled={working} className={buttonClass}>Search</button></form><div className="mt-5">{searchResults.length > 0 ? <SessionTable sessions={searchResults} onCheckout={checkout} working={working} /> : <p className="text-sm text-slate-500">Search results will appear here.</p>}</div></div></section>
      <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-5"><div className="flex items-end justify-between"><div><h2 className="text-lg font-semibold">Active vehicles</h2><p className="mt-1 text-sm text-slate-500">{active.length} active session{active.length === 1 ? "" : "s"}</p></div></div><div className="mt-5">{active.length ? <SessionTable sessions={active} onCheckout={checkout} working={working} /> : <p className="py-8 text-center text-sm text-slate-500">No active vehicles.</p>}</div></section>
      <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-5"><div className="flex items-end justify-between"><div><h2 className="text-lg font-semibold">Parking spots</h2><p className="mt-1 text-sm text-slate-500">{ev?.total_ev_spots ?? 0} EV spaces total</p></div></div><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{spots.map((spot) => <div key={spot.spot_id} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 p-4"><div><p className="font-semibold">{spot.spot_number}</p><p className="text-xs text-slate-500">Floor {spot.floor} · {spot.spot_type}</p></div><span className={spot.is_occupied ? "text-xs text-amber-300" : "text-xs text-emerald-300"}>{spot.is_occupied ? "Occupied" : "Available"}</span></div>)}</div></section>
    </div></main>
  );
}

function Stat({ label, value, tone = "text-slate-100" }: { label: string; value: string | number; tone?: string }) { return <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5"><p className="text-sm text-slate-500">{label}</p><p className={`mt-3 text-3xl font-semibold ${tone}`}>{value}</p></div>; }

function SessionTable({ sessions, onCheckout, working }: { sessions: SessionItem[]; onCheckout: (id: number) => void; working: boolean }) { return <div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500"><tr><th className="pb-3">Plate</th><th className="pb-3">Type</th><th className="pb-3">Spot</th><th className="pb-3">Check-in</th><th className="pb-3 text-right">Action</th></tr></thead><tbody className="divide-y divide-slate-800">{sessions.map((session) => <tr key={session.session_id}><td className="py-4 font-semibold">{session.license_plate}</td><td className="py-4 text-slate-400">{session.vehicle_type}</td><td className="py-4 text-slate-400">{session.spot_number} · F{session.floor}</td><td className="py-4 text-slate-400">{formatDate(session.check_in)}</td><td className="py-4 text-right">{session.status === "ACTIVE" && <button disabled={working} onClick={() => onCheckout(session.session_id)} className="rounded-md border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:border-cyan-400">Check out</button>}</td></tr>)}</tbody></table></div>; }
