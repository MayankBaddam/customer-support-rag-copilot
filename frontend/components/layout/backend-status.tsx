"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api-client";
import type { BackendStatus as Status } from "@/types/api";

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("loading");
  useEffect(() => {
    const controller = new AbortController();
    getHealth(controller.signal).then(() => setStatus("online")).catch(() => setStatus("offline"));
    return () => controller.abort();
  }, []);
  const labels = { loading: "Checking backend", online: "Backend online", offline: "Backend unavailable" };
  return <div className="status-wrap" role="status" aria-live="polite"><span className={`status-dot status-dot-${status === "online" ? "success" : status === "offline" ? "failure" : ""}`} /> <span>{labels[status]}</span></div>;
}