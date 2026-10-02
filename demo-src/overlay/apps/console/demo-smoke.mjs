// Demo smoke check for the mocked console. Self-contained — it serves the built
// bundle itself (SPA fallback included) and drives a headless browser over it:
//
//   VITE_DEMO=1 pnpm --filter @cozystack/console build
//   SMOKE_DIST=apps/console/dist node apps/console/demo-smoke.mjs
//
// It crawls every destination reachable from the three top sections — list
// screens, detail tabs, create forms — and fails on any un-mocked Kubernetes
// call (4xx/5xx to /api or /apis) or any page error. Exit code is non-zero on
// failure so CI can gate a deploy on it.

import { chromium } from "@playwright/test"
import http from "node:http"
import fs from "node:fs"
import path from "node:path"

const DIST = process.env.SMOKE_DIST || "dist"
const TYPES = { ".html":"text/html", ".js":"text/javascript", ".css":"text/css", ".json":"application/json", ".svg":"image/svg+xml", ".ico":"image/x-icon", ".woff2":"font/woff2", ".png":"image/png" }
const server = http.createServer((req, res) => {
  const url = req.url.split("?")[0]
  // Kubernetes paths never fall back to index.html. MSW passes a request it has
  // no handler for straight through to the network, and with a blanket SPA
  // fallback that request would come back 200 text/html — so a screen the mock
  // layer has never heard of would look exactly like a working one. Answering
  // 404 here is what makes an un-mocked call visible to the check below.
  if (/^\/(api|apis)(\/|$)/.test(url)) {
    res.statusCode = 404
    res.end("not mocked")
    return
  }
  let file = path.join(DIST, url)
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(DIST, "index.html")
  res.setHeader("Content-Type", TYPES[path.extname(file)] || "application/octet-stream")
  fs.createReadStream(file).pipe(res)
})
await new Promise((r) => server.listen(0, r))
const PORT = server.address().port

const BASE = `http://localhost:${PORT}`
const ENTRIES = ["/marketplace", "/console", "/admin/capacity/cluster"]

// Deliberately un-mocked, handled gracefully by the app — not failures.
const ALLOWED_404 = [
  "cozy-dashboard-console-config", // config configmap, swallowed to {}
  "buckets/cozy-backups", // optional backup bucket
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

const badApi = new Set()
const pageErrors = []
page.on("response", (r) => {
  const u = new URL(r.url()).pathname
  if (!/^\/(api|apis)\b/.test(u) && !u.startsWith("/api/") && !u.startsWith("/apis/")) return
  if (r.status() < 400) return
  if (ALLOWED_404.some((a) => u.includes(a))) return
  badApi.add(`${r.status()} ${u}`)
})
page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)))

const LINK_SEL =
  "aside a, nav a, [role=tablist] a, a[href^='/console'], a[href^='/admin'], a[href^='/marketplace']"
const harvest = async () =>
  (await page.locator(LINK_SEL).evaluateAll((as) => as.map((a) => a.getAttribute("href"))))
    .filter((h) => h && h.startsWith("/") && !h.startsWith("//"))

// Crawl outwards from the three top sections rather than only one hop: a hop
// reaches the list screens, and it takes a second to reach the tabs of a detail
// page and the create forms behind a "New …" button — which is where the mock
// layer actually tends to have holes.
const seen = new Set()
let frontier = [...ENTRIES]
for (let wave = 0; wave < 3 && frontier.length; wave++) {
  console.log(`\n########## wave ${wave}: ${frontier.length} destinations\n`)
  const next = new Set()
  for (const route of [...frontier].sort()) {
    if (seen.has(route)) continue
    seen.add(route)
    console.log("   " + route)
    await page.goto(BASE + route, { waitUntil: "domcontentloaded" })
    await page.waitForTimeout(1200)
    for (const h of await harvest()) if (!seen.has(h)) next.add(h)
  }
  frontier = [...next]
}
console.log(`\n########## visited ${seen.size} destinations\n`)
// This console has no distinct "not found" screen (an unknown route just
// renders the shell), so a broken screen shows up as an un-mocked API call or
// a page error, both collected above — not as body text.

await browser.close()
server.close()

const fail = badApi.size || pageErrors.length
console.log("un-mocked API calls:", badApi.size ? [...badApi] : "none")
console.log("page errors:", pageErrors.length ? pageErrors : "none")
console.log(fail ? "\nSMOKE FAILED" : "\nsmoke OK")
process.exit(fail ? 1 : 0)
