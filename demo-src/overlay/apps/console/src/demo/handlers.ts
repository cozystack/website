import { http, HttpResponse } from "msw"
import apis from "./fixtures/apis-discovery.json"
import appDefs from "./fixtures/applicationdefinitions.json"
import instances from "./fixtures/instances.json"
import info from "./fixtures/info.json"
import namespace from "./fixtures/namespace.json"
import nodeMetrics from "./fixtures/node-metrics.json"
import tenantNamespaces from "./fixtures/tenantnamespaces.json"
import pods from "./fixtures/pods.json"
import services from "./fixtures/services.json"
import pvcs from "./fixtures/persistentvolumeclaims.json"
import events from "./fixtures/events.json"
import resourceQuotas from "./fixtures/resourcequotas.json"
import deployments from "./fixtures/deployments.json"
import statefulSets from "./fixtures/statefulsets.json"
import daemonSets from "./fixtures/daemonsets.json"
import tenantSecrets from "./fixtures/tenantsecrets.json"
import nodes from "./fixtures/nodes.json"
import storageClasses from "./fixtures/storageclasses.json"
import backupClasses from "./fixtures/backupclasses.json"
import options from "./fixtures/options.json"
import tenantModulesNs from "./fixtures/tenantmodules-ns.json"
import tenantModulesAll from "./fixtures/tenantmodules-all.json"
import clusterResourceQuotas from "./fixtures/resourcequotas-all.json"
import taps from "./fixtures/taps.json"
import vmImportSources from "./fixtures/vmimportsources.json"
import vmImportTasks from "./fixtures/vmimporttasks.json"
import crdBackupClasses from "./fixtures/crds/backupclasses.backups.cozystack.io.json"
import crdPlans from "./fixtures/crds/plans.backups.cozystack.io.json"
import crdBackupJobs from "./fixtures/crds/backupjobs.backups.cozystack.io.json"
import crdBackups from "./fixtures/crds/backups.backups.cozystack.io.json"
import crdRestoreJobs from "./fixtures/crds/restorejobs.backups.cozystack.io.json"
import crdVMImportSources from "./fixtures/crds/vmimportsources.forklift.cozystack.io.json"
import crdVMImportTasks from "./fixtures/crds/vmimporttasks.forklift.cozystack.io.json"

// The demo runs entirely in the browser: MSW intercepts the Kubernetes REST API
// and answers from fixtures captured on a live workshop00 cluster. There is no
// backend, and therefore no auth.

const NS = "tenant-workshop00"
const COZY = "/apis/apps.cozystack.io/v1alpha1"          // instances (Postgres, Kafka, …)
const CORE = "/apis/cozystack.io/v1alpha1"               // ApplicationDefinition (the catalog)
const CORE2 = "/apis/core.cozystack.io/v1alpha1"         // tenantnamespaces, options, taps
const FORKLIFT = "/apis/forklift.cozystack.io/v1alpha1"  // VM import sources and tasks
type Obj = { kind: string; metadata: { name: string } }

// Resource plural -> kind, used to filter the shared instances.json.
const PLURAL_TO_KIND: Record<string, string> = {
  postgreses: "Postgres", kafkas: "Kafka", redises: "Redis",
  clickhouses: "ClickHouse", mongodbs: "MongoDB", natses: "NATS", buckets: "Bucket",
}

// Kind by plural for EVERY catalog type, not only the seven above. The plural
// arrives in the request; match it against the applicationdefinitions
// (spec.application.kind), otherwise Kubernetes/FoundationDB/Harbor/… get
// created as "Unknown" and hang on a spinner.
const appDefKindByName: Record<string, string> = {}
for (const a of appDefs.items as Array<{ metadata: { name: string }; spec?: { application?: { kind?: string } } }>) {
  const norm = a.metadata.name.replace(/-/g, "").toLowerCase()
  const k = a.spec?.application?.kind
  if (k) appDefKindByName[norm] = k
}
function kindForPlural(plural: string): string {
  if (PLURAL_TO_KIND[plural]) return PLURAL_TO_KIND[plural]
  const p = plural.toLowerCase()
  let best = ""
  for (const norm of Object.keys(appDefKindByName)) {
    if (p.startsWith(norm) && norm.length > best.length) best = norm
  }
  return best ? appDefKindByName[best] : plural
}

// --- Live instance store: shows a deploy actually in progress ---
// The demo is static, but a freshly created instance has to show up as
// installing and turn ready a few seconds later, or the deploy looks fake.
type Cond = { type: string; status: string; reason?: string; message?: string }
type Inst = Obj & { apiVersion?: string; spec?: Record<string, unknown>; status?: { conditions?: Cond[] } }
const liveInstances: Inst[] = JSON.parse(JSON.stringify(instances.items)) as Inst[]
const livePods = (pods.items as unknown as LabeledObj[]).slice()
const liveServices = (services.items as unknown as LabeledObj[]).slice()
const livePvcs = (pvcs.items as unknown as LabeledObj[]).slice()

// Which instances the captured fixtures actually carry workloads for. Most of
// them do not — only a handful of namespaces were captured in depth — and an
// instance created inside the demo never does. Anything missing is synthesized
// at read time (not mutated in at create time, which used to freeze the UI on
// Deploy), so every detail page has populated Pods/Services/Volumes tabs.
const ownerLabel = "apps.cozystack.io/application.name"
const ownersOf = (items: LabeledObj[]) =>
  new Set(items.map((i) => i.metadata.labels?.[ownerLabel]).filter(Boolean) as string[])
const fixturePodOwners = ownersOf(livePods)
const fixtureSvcOwners = ownersOf(liveServices)
const fixturePvcOwners = ownersOf(livePvcs)

// A rough service port per kind, so a synthesized Service is at least plausible
// for the application it belongs to.
const PORT_BY_KIND: Record<string, number> = {
  Postgres: 5432, MariaDB: 3306, MySQL: 3306, Redis: 6379, Valkey: 6379,
  Kafka: 9092, ClickHouse: 8123, MongoDB: 27017, NATS: 4222, RabbitMQ: 5672,
  OpenSearch: 9200, Qdrant: 6333, FoundationDB: 4500, Harbor: 80, Bucket: 8333,
}

// A VMInstance is one virt-launcher Pod and no Service of its own; a VMDisk is
// a volume with neither. Everything else is a replicated application.
const isVM = (kind: string) => kind === "VMInstance"
const isDisk = (kind: string) => kind === "VMDisk"

// Power state of the VirtualMachine behind a VMInstance, flipped by the
// start/stop/restart buttons. Imported machines start out stopped: the demo has
// no VM to attach to, and a stopped VM is a real state the console renders
// properly ("not running — start it to use the VNC console") rather than a
// running one whose console cannot connect.
const vmPower: Record<string, string> = {}
const vmName = (inst: Inst) => `vm-instance-${inst.metadata.name}`
const vmIsRunning = (inst: Inst) => (vmPower[vmName(inst)] ?? "Stopped") === "Running"

function labelsFor(inst: Inst): Record<string, string> {
  const k = inst.kind.toLowerCase()
  return {
    "apps.cozystack.io/application.kind": inst.kind,
    "apps.cozystack.io/application.name": inst.metadata.name,
    "app.kubernetes.io/instance": `${k}-${inst.metadata.name}`,
    "app.kubernetes.io/name": k,
  }
}
function isReady(inst: Inst): boolean {
  return inst.status?.conditions?.find((c) => c.type === "Ready")?.status === "True"
}
function createdAt(inst: Inst): string {
  return (inst.metadata as { creationTimestamp?: string }).creationTimestamp || new Date().toISOString()
}

function synthPodsFor(inst: Inst): LabeledObj[] {
  if (isDisk(inst.kind)) return []
  // A stopped VM has no VirtualMachineInstance and therefore no pod.
  if (isVM(inst.kind) && !vmIsRunning(inst)) return []
  const k = inst.kind.toLowerCase()
  const nm = inst.metadata.name
  const ready = isReady(inst)
  const names = isVM(inst.kind) ? [`virt-launcher-${nm}`] : [`${nm}-0`, `${nm}-1`]
  const container = isVM(inst.kind) ? "compute" : k
  return names.map((podName, i) => ({
    apiVersion: "v1", kind: "Pod",
    metadata: { name: podName, namespace: NS, uid: `synth-${nm}-${i}`, labels: { ...labelsFor(inst) } },
    spec: { containers: [{ name: container, image: `${k}:latest` }] },
    status: ready
      ? { phase: "Running", containerStatuses: [{ name: container, ready: true, restartCount: 0, state: { running: { startedAt: createdAt(inst) } } }] }
      : { phase: "Pending", containerStatuses: [{ name: container, ready: false, restartCount: 0, state: { waiting: { reason: "ContainerCreating" } } }] },
  })) as unknown as LabeledObj[]
}

function synthSvcFor(inst: Inst): LabeledObj[] {
  if (isVM(inst.kind) || isDisk(inst.kind)) return []
  const port = PORT_BY_KIND[inst.kind] ?? 80
  return [{
    apiVersion: "v1", kind: "Service",
    metadata: { name: inst.metadata.name, namespace: NS, uid: `synth-svc-${inst.metadata.name}`, labels: { ...labelsFor(inst) } },
    spec: { type: "ClusterIP", clusterIP: "10.96.120.10", ports: [{ name: "main", port, protocol: "TCP", targetPort: port }] },
  }] as unknown as LabeledObj[]
}

function synthPvcFor(inst: Inst): LabeledObj[] {
  const size = (inst.spec?.storage as string) || (inst.spec?.size as string)
  if (!size) return []
  const nm = inst.metadata.name
  return [{
    apiVersion: "v1", kind: "PersistentVolumeClaim",
    metadata: { name: `data-${nm}`, namespace: NS, uid: `synth-pvc-${nm}`, labels: { ...labelsFor(inst) } },
    spec: {
      accessModes: ["ReadWriteOnce"],
      resources: { requests: { storage: size } },
      storageClassName: (inst.spec?.storageClass as string) || "replicated",
      volumeMode: "Filesystem",
    },
    status: { phase: isReady(inst) ? "Bound" : "Pending", accessModes: ["ReadWriteOnce"], capacity: { storage: size } },
  }] as unknown as LabeledObj[]
}

// The full set of pods/services/volumes, fixtures plus whatever has to be
// synthesized for the instances the fixtures do not cover.
const allPods = () =>
  livePods.concat(liveInstances.filter((i) => !fixturePodOwners.has(i.metadata.name)).flatMap(synthPodsFor))
const allServices = () =>
  liveServices.concat(liveInstances.filter((i) => !fixtureSvcOwners.has(i.metadata.name)).flatMap(synthSvcFor))
const allPvcs = () =>
  livePvcs.concat(liveInstances.filter((i) => !fixturePvcOwners.has(i.metadata.name)).flatMap(synthPvcFor))

const list = (items: Obj[], kind: string) => ({
  apiVersion: "apps.cozystack.io/v1alpha1",
  kind: `${kind}List`,
  metadata: { resourceVersion: "1" },
  items,
})

// watch=1 -> a stream of {type, object} lines; send everything as ADDED, then
// hold the connection open.
function watchStream(items: Obj[]) {
  const enc = new TextEncoder()
  const body = new ReadableStream({
    start(c) {
      for (const o of items) c.enqueue(enc.encode(JSON.stringify({ type: "ADDED", object: o }) + "\n"))
      c.enqueue(enc.encode(JSON.stringify({ type: "BOOKMARK", object: { metadata: { resourceVersion: "1" } } }) + "\n"))
      // never closed: the watch layer treats the connection as alive
    },
  })
  return new HttpResponse(body, { headers: { "content-type": "application/json" } })
}

const isWatch = (req: Request) => new URL(req.url).searchParams.has("watch")

// an empty list of a resource (for kinds the demo has nothing of)
const emptyList = (kind: string, apiVersion: string) => ({
  apiVersion, kind: `${kind}List`, metadata: { resourceVersion: "1" }, items: [] as Obj[],
})

// CRDs by name — the create forms need them (use-crd-schema)
const CRD_BY_NAME: Record<string, unknown> = {
  "backupclasses.backups.cozystack.io": crdBackupClasses,
  "plans.backups.cozystack.io": crdPlans,
  "backupjobs.backups.cozystack.io": crdBackupJobs,
  "backups.backups.cozystack.io": crdBackups,
  "restorejobs.backups.cozystack.io": crdRestoreJobs,
  "vmimportsources.forklift.cozystack.io": crdVMImportSources,
  "vmimporttasks.forklift.cozystack.io": crdVMImportTasks,
}

// labelSelector "k1=v1,k2=v2" -> every pair has to match metadata.labels.
type LabeledObj = Obj & { metadata: { name: string; labels?: Record<string, string> } }
function filterByLabels(items: LabeledObj[], req: Request): LabeledObj[] {
  const sel = new URL(req.url).searchParams.get("labelSelector")
  if (!sel) return items
  const pairs = sel.split(",").map((p) => p.split("=")).filter((p) => p.length === 2)
  return items.filter((i) => pairs.every(([k, v]) => i.metadata.labels?.[k] === v))
}
// fieldSelector "spec.type=LoadBalancer" — supports exactly what the UI sends (ExternalIpsPage)
function filterByFields(items: LabeledObj[], req: Request): LabeledObj[] {
  const sel = new URL(req.url).searchParams.get("fieldSelector")
  if (!sel) return items
  const pairs = sel.split(",").map((p) => p.split("=")).filter((p) => p.length === 2)
  return items.filter((i) =>
    pairs.every(([k, v]) => {
      const path = k.split(".")
      let cur: unknown = i
      for (const seg of path) cur = (cur as Record<string, unknown> | undefined)?.[seg]
      return cur === v
    }),
  )
}

// a resource list with labelSelector filtering and watch support
function labeled(fixture: { items: unknown[] }, kind: string, apiVersion: string) {
  return ({ request }: { request: Request }) => {
    const items = filterByLabels(fixture.items as unknown as LabeledObj[], request)
    if (isWatch(request)) return watchStream(items)
    return HttpResponse.json({ apiVersion, kind: `${kind}List`, metadata: { resourceVersion: "1" }, items })
  }
}

// --- Migration (forklift.cozystack.io) and marketplace taps ---
// Both are live stores like the instances above, so the create/delete actions
// on their pages do something rather than erroring out.
type Named = { apiVersion?: string; kind?: string; metadata: { name: string; namespace?: string; creationTimestamp?: string } }
const liveMigration: Record<string, Named[]> = {
  vmimportsources: JSON.parse(JSON.stringify(vmImportSources.items)) as Named[],
  vmimporttasks: JSON.parse(JSON.stringify(vmImportTasks.items)) as Named[],
}
const MIGRATION_KIND: Record<string, string> = {
  vmimportsources: "VMImportSource",
  vmimporttasks: "VMImportTask",
}
const liveTaps: Named[] = JSON.parse(JSON.stringify(taps.items)) as Named[]

// --- KubeVirt: the VirtualMachine behind each VMInstance ---
// The detail page reads power state from kubevirt.io/virtualmachines, named
// "<release prefix><instance>", and drives start/stop/restart through the
// subresources.kubevirt.io aggregated API. Derived from the instance list on
// read, so a VMInstance created inside the demo gets one too.
function allVMs(): LabeledObj[] {
  return liveInstances
    .filter((i) => isVM(i.kind))
    .map((i) => ({
      apiVersion: "kubevirt.io/v1", kind: "VirtualMachine",
      metadata: { name: vmName(i), namespace: NS, uid: `kubevirt-${i.metadata.name}`, labels: { ...labelsFor(i) } },
      spec: { runStrategy: "Always" },
      status: { printableStatus: vmPower[vmName(i)] ?? "Stopped" },
    })) as unknown as LabeledObj[]
}

// --- Option sources behind the form dropdowns (core.cozystack.io Options) ---
// Most come straight from the captured fixture. Three are computed here: the
// captured cluster had no vSphere connections and no VM disks, and the machines
// a connection can see are a parameterised source ("vmimportvm.<connection>")
// the server computes per connection, so there is nothing to capture at all.
type OptionItem = { value: string; label?: string; description?: string; default?: boolean }
type OptionObj = { apiVersion: string; kind: string; metadata: { name: string; namespace: string }; spec: { items: OptionItem[] } }

// What the demo's vCenter "sees" — the machines not imported yet.
const VSPHERE_INVENTORY: OptionItem[] = [
  { value: "vm-5211", label: "crm-app-01 (vm-5211)" },
  { value: "vm-5212", label: "crm-app-02 (vm-5212)" },
  { value: "vm-5240", label: "crm-db-01 (vm-5240)" },
  { value: "vm-5318", label: "fileserver-01 (vm-5318)" },
  { value: "vm-5402", label: "jenkins-legacy (vm-5402)" },
]

function computedOptionItems(name: string): OptionItem[] | null {
  if (name === "vmimportsource")
    return (liveMigration.vmimportsources ?? []).map((s) => ({ value: s.metadata.name }))
  if (name === "vmdisk")
    return liveInstances.filter((i) => i.kind === "VMDisk").map((i) => ({ value: i.metadata.name }))
  if (name.startsWith("vmimportvm.")) return VSPHERE_INVENTORY
  return null
}
const makeOption = (name: string, items: OptionItem[]): OptionObj => ({
  apiVersion: "core.cozystack.io/v1alpha1", kind: "Option",
  metadata: { name, namespace: NS }, spec: { items },
})
function allOptions(): OptionObj[] {
  const out = (options.items as unknown as OptionObj[]).map((o) => {
    const computed = computedOptionItems(o.metadata.name)
    return computed ? makeOption(o.metadata.name, computed) : o
  })
  // sources that postdate the capture
  if (!out.some((o) => o.metadata.name === "vmimportsource"))
    out.push(makeOption("vmimportsource", computedOptionItems("vmimportsource")!))
  return out
}

function migrationList(plural: string) {
  return {
    apiVersion: "forklift.cozystack.io/v1alpha1",
    kind: `${MIGRATION_KIND[plural] ?? "VMImport"}List`,
    metadata: { resourceVersion: "1" },
    items: liveMigration[plural] ?? [],
  }
}
function removeByName(items: Named[], name: string) {
  const at = items.findIndex((i) => i.metadata.name === name)
  if (at >= 0) items.splice(at, 1)
}

export const handlers = [
  // discovery
  http.get("/apis", () => HttpResponse.json(apis)),
  http.get("/api/v1", () => HttpResponse.json({ kind: "APIResourceList", groupVersion: "v1", resources: [] })),

  // catalog: ApplicationDefinition (group cozystack.io, cluster-scoped)
  http.get(`${CORE}/applicationdefinitions`, ({ request }) =>
    isWatch(request) ? watchStream(appDefs.items as Obj[]) : HttpResponse.json(appDefs)),

  // the user's tenants (one in the demo, workshop00)
  http.get(`${CORE2}/tenantnamespaces`, ({ request }) =>
    isWatch(request) ? watchStream(tenantNamespaces.items as Obj[]) : HttpResponse.json(tenantNamespaces)),

  // the info resource (cozystack "info" module — the tenant summary); a snapshot
  http.get(`${COZY}/namespaces/:ns/infos`, ({ request }) =>
    isWatch(request)
      ? watchStream([info as Obj])
      : HttpResponse.json({ apiVersion: "apps.cozystack.io/v1alpha1", kind: "InfoList", metadata: { resourceVersion: "1" }, items: [info] })),
  http.get(`${COZY}/namespaces/:ns/infos/:name`, () => HttpResponse.json(info)),

  // Marketplace -> Repositories: the External-Apps repositories tapped by the
  // cluster. Cluster-scoped, so no namespace in the path.
  http.get(`${CORE2}/taps`, ({ request }) =>
    isWatch(request)
      ? watchStream(liveTaps as unknown as Obj[])
      : HttpResponse.json({ apiVersion: "core.cozystack.io/v1alpha1", kind: "TapList", metadata: { resourceVersion: "1" }, items: liveTaps })),
  http.post(`${CORE2}/taps`, async ({ request }) => {
    const sent = (await request.json()) as Named & { spec?: Record<string, unknown> }
    const tap = {
      apiVersion: "core.cozystack.io/v1alpha1", kind: "Tap",
      metadata: { name: sent.metadata?.name ?? "tap-new", creationTimestamp: new Date().toISOString() },
      // A freshly connected repository is pending until its index is pulled;
      // the packages it exposes are only known after that.
      spec: { ...(sent.spec ?? {}), community: true, ready: false, message: "Pulling the repository index", packages: [] },
    } as unknown as Named
    liveTaps.push(tap)
    return HttpResponse.json(tap, { status: 201 })
  }),
  http.delete(`${CORE2}/taps/:name`, ({ params }) => {
    removeByName(liveTaps, params.name as string)
    return HttpResponse.json({ kind: "Status", apiVersion: "v1", status: "Success" })
  }),

  // Console -> Migration: vSphere connections and the import tasks run from them
  http.get(`${FORKLIFT}/namespaces/:ns/:resource`, ({ params, request }) => {
    const plural = params.resource as string
    const items = (liveMigration[plural] ?? []) as unknown as Obj[]
    return isWatch(request) ? watchStream(items) : HttpResponse.json(migrationList(plural))
  }),
  http.get(`${FORKLIFT}/namespaces/:ns/:resource/:name`, ({ params }) => {
    const obj = (liveMigration[params.resource as string] ?? []).find((i) => i.metadata.name === params.name)
    return obj ? HttpResponse.json(obj) : new HttpResponse(null, { status: 404 })
  }),
  http.post(`${FORKLIFT}/namespaces/:ns/:resource`, async ({ params, request }) => {
    const plural = params.resource as string
    const sent = (await request.json()) as Named & { spec?: Record<string, unknown> }
    const obj = {
      apiVersion: "forklift.cozystack.io/v1alpha1",
      kind: MIGRATION_KIND[plural] ?? "VMImport",
      metadata: {
        name: sent.metadata?.name ?? `new-${plural}`, namespace: NS,
        creationTimestamp: new Date().toISOString(), uid: crypto.randomUUID(),
      },
      spec: sent.spec ?? {},
      status: plural === "vmimporttasks"
        ? { phase: "Pending", message: "Waiting for the connection to be ready", vms: [] }
        : { conditions: [{ type: "Ready", status: "False", reason: "Connecting", message: "Verifying credentials against the endpoint" }] },
    } as unknown as Named
    ;(liveMigration[plural] ??= []).push(obj)
    return HttpResponse.json(obj, { status: 201 })
  }),
  http.put(`${FORKLIFT}/namespaces/:ns/:resource/:name`, async ({ params, request }) => {
    const items = liveMigration[params.resource as string] ?? []
    const sent = (await request.json()) as Named
    const at = items.findIndex((i) => i.metadata.name === params.name)
    if (at < 0) return new HttpResponse(null, { status: 404 })
    items[at] = { ...items[at], ...sent, metadata: { ...items[at].metadata, ...sent.metadata } }
    return HttpResponse.json(items[at])
  }),
  http.delete(`${FORKLIFT}/namespaces/:ns/:resource/:name`, ({ params }) => {
    removeByName(liveMigration[params.resource as string] ?? [], params.name as string)
    return HttpResponse.json({ kind: "Status", apiVersion: "v1", status: "Success" })
  }),

  // the VirtualMachine behind a VMInstance (power state), and its action endpoints
  http.get("/apis/kubevirt.io/v1/namespaces/:ns/virtualmachines", ({ request }) => {
    const items = filterByFields(filterByLabels(allVMs(), request), request)
    return isWatch(request)
      ? watchStream(items)
      : HttpResponse.json({ apiVersion: "kubevirt.io/v1", kind: "VirtualMachineList", metadata: { resourceVersion: "1" }, items })
  }),
  http.put("/apis/subresources.kubevirt.io/v1/namespaces/:ns/virtualmachines/:name/:action", ({ params }) => {
    vmPower[params.name as string] = params.action === "stop" ? "Stopped" : "Running"
    return HttpResponse.json({})
  }),

  // instances of one type inside a namespace
  http.get(`${COZY}/namespaces/:ns/:resource`, ({ params, request }) => {
    const kind = kindForPlural(params.resource as string)
    const items = liveInstances.filter((i) => i.kind === kind)
    return isWatch(request) ? watchStream(items) : HttpResponse.json(list(items, kind ?? "Unknown"))
  }),

  // the same instances listed cluster-wide — the VM disk picker asks for every
  // VMDisk rather than the ones in the current namespace
  http.get(`${COZY}/:resource`, ({ params, request }) => {
    const kind = kindForPlural(params.resource as string)
    const items = liveInstances.filter((i) => i.kind === kind)
    return isWatch(request) ? watchStream(items) : HttpResponse.json(list(items, kind ?? "Unknown"))
  }),

  // a single instance
  http.get(`${COZY}/namespaces/:ns/:resource/:name`, ({ params }) => {
    const kind = kindForPlural(params.resource as string)
    const obj = liveInstances.find((i) => i.kind === kind && i.metadata.name === params.name)
    return obj ? HttpResponse.json(obj) : new HttpResponse(null, { status: 404 })
  }),

  // namespace
  http.get(`/api/v1/namespaces/${NS}`, () => HttpResponse.json(namespace)),
  // form options (storageClass, image, instancetype, backupclass, …)
  http.get(`${CORE2}/namespaces/:ns/options`, ({ request }) => {
    const items = allOptions()
    return isWatch(request)
      ? watchStream(items as unknown as Obj[])
      : HttpResponse.json({ apiVersion: "core.cozystack.io/v1alpha1", kind: "OptionList", metadata: { resourceVersion: "1" }, items })
  }),
  // a single option by name — how a parameterised source is fetched, e.g. the
  // machines visible through one vSphere connection ("vmimportvm.vcenter-hq")
  http.get(`${CORE2}/namespaces/:ns/options/:name`, ({ params }) => {
    const name = params.name as string
    const found = allOptions().find((o) => o.metadata.name === name)
    if (found) return HttpResponse.json(found)
    const computed = computedOptionItems(name)
    return computed ? HttpResponse.json(makeOption(name, computed)) : new HttpResponse(null, { status: 404 })
  }),

  // an instance's workloads/services/volumes/secrets/events (the detail tabs) — filtered by labelSelector
  http.get(`/api/v1/namespaces/:ns/pods`, ({ request }) => {
    const items = filterByLabels(allPods(), request)
    return isWatch(request) ? watchStream(items as unknown as Obj[]) : HttpResponse.json({ apiVersion: "v1", kind: "PodList", metadata: { resourceVersion: "1" }, items })
  }),
  http.get("/api/v1/pods", ({ request }) =>
    isWatch(request) ? watchStream(pods.items as Obj[]) : HttpResponse.json(pods)),

  http.get(`/api/v1/namespaces/:ns/services`, ({ request }) => {
    const items = filterByFields(filterByLabels(allServices(), request), request)
    return isWatch(request)
      ? watchStream(items)
      : HttpResponse.json({ apiVersion: "v1", kind: "ServiceList", metadata: { resourceVersion: "1" }, items })
  }),
  http.get(`/api/v1/namespaces/:ns/persistentvolumeclaims`, ({ request }) => {
    const items = filterByLabels(allPvcs(), request)
    return isWatch(request)
      ? watchStream(items)
      : HttpResponse.json({ apiVersion: "v1", kind: "PersistentVolumeClaimList", metadata: { resourceVersion: "1" }, items })
  }),
  http.get("/api/v1/persistentvolumeclaims", ({ request }) =>
    isWatch(request) ? watchStream(pvcs.items as Obj[]) : HttpResponse.json(pvcs)),

  http.get(`/api/v1/namespaces/:ns/events`, ({ request }) =>
    isWatch(request) ? watchStream(events.items as Obj[]) : HttpResponse.json(events)),
  http.get(`/api/v1/namespaces/:ns/resourcequotas`, ({ request }) =>
    isWatch(request) ? watchStream(resourceQuotas.items as Obj[]) : HttpResponse.json(resourceQuotas)),
  http.get(`/apis/apps/v1/namespaces/:ns/deployments`, labeled(deployments, "Deployment", "apps/v1")),
  http.get(`/apis/apps/v1/namespaces/:ns/statefulsets`, labeled(statefulSets, "StatefulSet", "apps/v1")),
  http.get(`/apis/apps/v1/namespaces/:ns/daemonsets`, labeled(daemonSets, "DaemonSet", "apps/v1")),
  http.get(`${CORE2}/namespaces/:ns/tenantsecrets`, labeled(tenantSecrets, "TenantSecret", "core.cozystack.io/v1alpha1")),
  http.get(`/apis/networking.k8s.io/v1/namespaces/:ns/ingresses`, ({ request }) =>
    isWatch(request)
      ? watchStream([])
      : HttpResponse.json({ apiVersion: "networking.k8s.io/v1", kind: "IngressList", metadata: { resourceVersion: "1" }, items: [] })),

  // namespaced backup resources (Console → Backups: Plans/BackupJobs/Backups/RestoreJobs) — empty in the demo
  http.get(`/apis/backups.cozystack.io/v1alpha1/namespaces/:ns/:resource`, ({ params, request }) => {
    const kindMap: Record<string, string> = { plans: "Plan", backupjobs: "BackupJob", backups: "Backup", restorejobs: "RestoreJob" }
    const kind = kindMap[params.resource as string] ?? "Backup"
    return isWatch(request) ? watchStream([]) : HttpResponse.json(emptyList(kind, "backups.cozystack.io/v1alpha1"))
  }),

  // tenant modules (Admin → Administration → Modules)
  http.get(`${CORE2}/namespaces/:ns/tenantmodules`, ({ request }) =>
    isWatch(request) ? watchStream(tenantModulesNs.items as Obj[]) : HttpResponse.json(tenantModulesNs)),
  // cluster-wide modules + the tenant list (Admin → Administration → Tenants)
  http.get(`${CORE2}/tenantmodules`, ({ request }) =>
    isWatch(request) ? watchStream(tenantModulesAll.items as Obj[]) : HttpResponse.json(tenantModulesAll)),
  http.get(`/api/v1/resourcequotas`, ({ request }) =>
    isWatch(request) ? watchStream(clusterResourceQuotas.items as Obj[]) : HttpResponse.json(clusterResourceQuotas)),

  // CRD schemas behind the create forms (use-crd-schema)
  http.get(`/apis/apiextensions.k8s.io/v1/customresourcedefinitions/:name`, ({ params }) => {
    const crd = CRD_BY_NAME[params.name as string]
    return crd ? HttpResponse.json(crd) : new HttpResponse(null, { status: 404 })
  }),

  // dashboard config and the user name (both degrade gracefully, but answer sensibly)
  http.get("/api/v1/namespaces/cozy-dashboard/configmaps/cozy-dashboard-console-config", () =>
    new HttpResponse(null, { status: 404 })),
  http.get("/oauth2/userinfo", () => HttpResponse.json({ email: "demo@cozystack.io", user: "demo" })),

  // permissions: everything is allowed in the demo
  http.post("/apis/authorization.k8s.io/v1/selfsubjectaccessreviews", async ({ request }) => {
    const body = (await request.json()) as { spec?: unknown }
    return HttpResponse.json({ apiVersion: "authorization.k8s.io/v1", kind: "SelfSubjectAccessReview", spec: body.spec ?? {}, status: { allowed: true } })
  }),

  // node metrics
  http.get("/api/v1/nodes", ({ request }) =>
    isWatch(request) ? watchStream(nodes.items as Obj[]) : HttpResponse.json(nodes)),
  http.get("/apis/storage.k8s.io/v1/storageclasses", ({ request }) =>
    isWatch(request) ? watchStream(storageClasses.items as Obj[]) : HttpResponse.json(storageClasses)),
  http.get("/apis/backups.cozystack.io/v1alpha1/backupclasses", ({ request }) =>
    isWatch(request) ? watchStream(backupClasses.items as Obj[]) : HttpResponse.json(backupClasses)),
  http.get("/apis/backups.cozystack.io/v1alpha1/backupclasses/:name", ({ params }) => {
    const bc = (backupClasses.items as Obj[]).find((i) => i.metadata.name === params.name)
    return bc ? HttpResponse.json(bc) : new HttpResponse(null, { status: 404 })
  }),
  http.get("/apis/backups.cozystack.io/v1alpha1/backups", ({ request }) =>
    isWatch(request)
      ? watchStream([])
      : HttpResponse.json({ apiVersion: "backups.cozystack.io/v1alpha1", kind: "BackupList", metadata: { resourceVersion: "1" }, items: [] })),
  http.get("/apis/metrics.k8s.io/v1beta1/nodes", () => HttpResponse.json(nodeMetrics)),
  http.get("/apis/metrics.k8s.io/v1beta1/namespaces/:ns/pods", () =>
    HttpResponse.json({ kind: "PodMetricsList", apiVersion: "metrics.k8s.io/v1beta1", items: [] })),

  // Creating an instance: it shows up installing and turns ready after ~9s.
  http.post(`${COZY}/namespaces/:ns/:resource`, async ({ params, request }) => {
    const kind = kindForPlural(params.resource as string)
    const sent = (await request.json()) as { metadata?: { name?: string }; spec?: Record<string, unknown> }
    const name = sent?.metadata?.name || `new-${kind.toLowerCase()}`
    const obj: Inst = {
      apiVersion: "apps.cozystack.io/v1alpha1", kind,
      metadata: { name, namespace: NS,
        creationTimestamp: new Date().toISOString(),
        uid: crypto.randomUUID(),
        labels: { "apps.cozystack.io/application.kind": kind, "apps.cozystack.io/application.name": name },
      } as Obj["metadata"],
      spec: sent?.spec ?? {},
      status: { conditions: [{ type: "Ready", status: "False", reason: "Installing", message: "Deploying…" }] },
    }
    liveInstances.push(obj)
    // after ~9s the install "finishes".
    setTimeout(() => {
      const c = obj.status?.conditions?.find((x) => x.type === "Ready")
      if (c) { c.status = "True"; c.reason = "InstallSucceeded"; c.message = "" }
    }, 9000)
    return HttpResponse.json(obj, { status: 201 })
  }),

  // anything else under apps.cozystack.io — an empty list, so the UI does not break
  http.get(`${COZY}/namespaces/:ns/:resource`, () => HttpResponse.json(list([], "Unknown"))),
]
