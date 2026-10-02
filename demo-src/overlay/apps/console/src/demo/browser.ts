import { setupWorker } from "msw/browser"
import { handlers } from "./handlers.ts"

// Only ever started in a demo build (VITE_DEMO=1). Unhandled requests are let
// through silently — the Kubernetes UI asks for some paths optionally.
export async function startDemo() {
  restoreRoute()
  const worker = setupWorker(...handlers)
  // The worker and its scope have to live under the base path (e.g. /demo-app/),
  // otherwise nothing is intercepted on sub-paths.
  await worker.start({
    onUnhandledRequest: "bypass",
    quiet: true,
    serviceWorker: { url: `${import.meta.env.BASE_URL}mockServiceWorker.js` },
  })
}

// GitHub Pages answers a reload on an inner screen with the site 404, which
// sends the route back as ?demoRoute= (see layouts/404.html). Put it back in
// the address bar before the router reads it.
function restoreRoute() {
  const route = new URLSearchParams(window.location.search).get("demoRoute")
  if (!route?.startsWith("/")) return
  const base = import.meta.env.BASE_URL.replace(/\/$/, "")
  window.history.replaceState(null, "", base + route)
}
