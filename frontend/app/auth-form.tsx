"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiRequest, jsonBody, TokenResponse } from "../lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const isRegister = mode === "register";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isRegister) await apiRequest("/api/auth/register", jsonBody({ name, email, password }));
      const token = await apiRequest<TokenResponse>("/api/auth/login", jsonBody({ email, password }));
      localStorage.setItem("parkflow_token", token.access_token);
      window.location.href = "/dashboard";
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to authenticate");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 px-6 py-10 text-slate-100">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <Link href="/" className="text-sm font-semibold text-cyan-300">← ParkFlow</Link>
        <h1 className="mt-10 text-3xl font-semibold">{isRegister ? "Create your account" : "Welcome back"}</h1>
        <p className="mt-2 text-slate-400">{isRegister ? "Set up access to the garage dashboard." : "Sign in to manage your garage."}</p>
        <form onSubmit={submit} className="mt-8 space-y-5">
          {isRegister && <label className="block text-sm text-slate-300">Name<input required value={name} onChange={(event) => setName(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 outline-none focus:border-cyan-400" /></label>}
          <label className="block text-sm text-slate-300">Email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 outline-none focus:border-cyan-400" /></label>
          <label className="block text-sm text-slate-300">Password<input required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-3 outline-none focus:border-cyan-400" /></label>
          {error && <p className="rounded-lg border border-rose-900 bg-rose-950/40 px-3 py-3 text-sm text-rose-300">{error}</p>}
          <button disabled={loading} className="w-full rounded-lg bg-cyan-400 px-4 py-3 font-semibold text-slate-950 disabled:cursor-wait disabled:opacity-60">{loading ? "Working..." : isRegister ? "Create account" : "Log in"}</button>
        </form>
        <p className="mt-7 text-center text-sm text-slate-500">{isRegister ? "Already have an account? " : "Need an account? "}<Link href={isRegister ? "/login" : "/register"} className="text-cyan-300">{isRegister ? "Log in" : "Register"}</Link></p>
      </div>
    </main>
  );
}
