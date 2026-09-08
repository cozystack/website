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
import crdBackupClasses from "./fixtures/crds/backupclasses.backups.cozystack.io.json"
import crdPlans from "./fixtures/crds/plans.backups.cozystack.io.json"
import crdBackupJobs from "./fixtures/crds/backupjobs.backups.cozystack.io.json"
import crdBackups from "./fixtures/crds/backups.backups.cozystack.io.json"
import crdRestoreJobs from "./fixtures/crds/restorejobs.backups.cozystack.io.json"

// Демо крутится целиком в браузере: MSW перехватывает k8s REST, отдаёт снятые
// с живого workshop00 фикстуры. Никакого backend, поэтому и никакой auth.

const NS = "tenant-workshop00"
const COZY = "/apis/apps.cozystack.io/v1alpha1"          // инстансы (Postgres, Kafka, …)
const CORE = "/apis/cozystack.io/v1alpha1"               // ApplicationDefinition (каталог)
const CORE2 = "/apis/core.cozystack.io/v1alpha1"         // tenantnamespaces
type Obj = { kind: string; metadata: { name: string } }

// plural ресурса -> kind, чтобы отфильтровать общий instances.json.
const PLURAL_TO_KIND: Record<string, string> = {
  postgreses: "Postgres", kafkas: "Kafka", redises: "Redis",
  clickhouses: "ClickHouse", mongodbs: "MongoDB", natses: "NATS", buckets: "Bucket",
}

// Kind по plural для ВСЕХ типов каталога, а не только семи выше. Плюрал приходит
// в запросе; сопоставляем его с applicationdefinition (spec.application.kind),
// иначе Kubernetes/FoundationDB/Harbor/… создавались как "Unknown" и висли.
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

// --- Живой стор инстансов: показывает деплой «в процессе» ---
// Демо статично, но при создании инстанс должен появиться в состоянии установки
// и через несколько секунд стать Ready — иначе деплой выглядит фейково.
type Cond = { type: string; status: string; reason?: string; message?: string }
type Inst = Obj & { apiVersion?: string; spec?: unknown; status?: { conditions?: Cond[] } }
const liveInstances: Inst[] = JSON.parse(JSON.stringify(instances.items)) as Inst[]
// Живые workloads: стартуют из фикстур, при создании инстанса дополняются
// синтезированными подами/сервисами/томами — чтобы новый инстанс был «живым вглубь».
const livePods = (pods.items as unknown as LabeledObj[]).slice()
const seededInstanceNames = new Set((instances.items as Inst[]).map((i) => i.metadata.name))
// Поды/сервисы для инстансов, созданных в демо (которых нет в фикстурах),
// синтезируются на лету — так новый инстанс «живой вглубь», без мутаций при create.
function synthPodsFor(inst: Inst): LabeledObj[] {
  const k = inst.kind.toLowerCase(); const nm = inst.metadata.name
  const ready = inst.status?.conditions?.find((c) => c.type === "Ready")?.status === "True"
  const labels = { "apps.cozystack.io/application.kind": inst.kind, "apps.cozystack.io/application.name": nm,
    "app.kubernetes.io/instance": `${k}-${nm}`, "app.kubernetes.io/name": k }
  return [0, 1].map((i) => ({
    apiVersion: "v1", kind: "Pod",
    metadata: { name: `${nm}-${i}`, namespace: NS, uid: `synth-${nm}-${i}`, labels: { ...labels } },
    spec: { containers: [{ name: k, image: `${k}:latest` }] },
    status: ready
      ? { phase: "Running", containerStatuses: [{ name: k, ready: true, restartCount: 0, state: { running: { startedAt: (inst.metadata as { creationTimestamp?: string }).creationTimestamp || new Date().toISOString() } } }] }
      : { phase: "Pending", containerStatuses: [{ name: k, ready: false, restartCount: 0, state: { waiting: { reason: "ContainerCreating" } } }] },
  })) as unknown as LabeledObj[]
}
function synthSvcFor(inst: Inst): LabeledObj {
  const k = inst.kind.toLowerCase(); const nm = inst.metadata.name
  return { apiVersion: "v1", kind: "Service",
    metadata: { name: nm, namespace: NS, uid: `synth-svc-${nm}`, labels: { "apps.cozystack.io/application.kind": inst.kind, "apps.cozystack.io/application.name": nm, "app.kubernetes.io/instance": `${k}-${nm}` } },
    spec: { type: "ClusterIP", clusterIP: "10.96.120.10", ports: [{ name: "main", port: 5432, protocol: "TCP", targetPort: 5432 }] } } as unknown as LabeledObj
}
// собрать полный набор pods/services с учётом созданных инстансов
function allPods(): LabeledObj[] {
  const extra = liveInstances.filter((i) => !seededInstanceNames.has(i.metadata.name)).flatMap(synthPodsFor)
  return livePods.concat(extra)
}
function allServices(): LabeledObj[] {
  const extra = liveInstances.filter((i) => !seededInstanceNames.has(i.metadata.name)).map(synthSvcFor)
  return liveServices.concat(extra)
}
const liveServices = (services.items as unknown as LabeledObj[]).slice()
const livePvcs = (pvcs.items as unknown as LabeledObj[]).slice()

const list = (items: Obj[], kind: string) => ({
  apiVersion: "apps.cozystack.io/v1alpha1",
  kind: `${kind}List`,
  metadata: { resourceVersion: "1" },
  items,
})

// watch=1 -> стрим строк {type, object}; отдаём всё как ADDED, потом держим открытым.
function watchStream(items: Obj[]) {
  const enc = new TextEncoder()
  const body = new ReadableStream({
    start(c) {
      for (const o of items) c.enqueue(enc.encode(JSON.stringify({ type: "ADDED", object: o }) + "\n"))
      c.enqueue(enc.encode(JSON.stringify({ type: "BOOKMARK", object: { metadata: { resourceVersion: "1" } } }) + "\n"))
      // не закрываем: watch-слой считает соединение живым
    },
  })
  return new HttpResponse(body, { headers: { "content-type": "application/json" } })
}

const isWatch = (req: Request) => new URL(req.url).searchParams.has("watch")

// пустой список ресурса (для сущностей, которых в демо нет)
const emptyList = (kind: string, apiVersion: string) => ({
  apiVersion, kind: `${kind}List`, metadata: { resourceVersion: "1" }, items: [] as Obj[],
})

// CRD по имени — нужны формам создания (use-crd-schema)
const CRD_BY_NAME: Record<string, unknown> = {
  "backupclasses.backups.cozystack.io": crdBackupClasses,
  "plans.backups.cozystack.io": crdPlans,
  "backupjobs.backups.cozystack.io": crdBackupJobs,
  "backups.backups.cozystack.io": crdBackups,
  "restorejobs.backups.cozystack.io": crdRestoreJobs,
}

// labelSelector "k1=v1,k2=v2" -> все пары должны совпасть с metadata.labels.
type LabeledObj = Obj & { metadata: { name: string; labels?: Record<string, string> } }
function filterByLabels(items: LabeledObj[], req: Request): LabeledObj[] {
  const sel = new URL(req.url).searchParams.get("labelSelector")
  if (!sel) return items
  const pairs = sel.split(",").map((p) => p.split("=")).filter((p) => p.length === 2)
  return items.filter((i) => pairs.every(([k, v]) => i.metadata.labels?.[k] === v))
}
// fieldSelector "spec.type=LoadBalancer" — поддерживаем ровно то, что шлёт UI (ExternalIpsPage)
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

// список ресурсов с фильтром по labelSelector + поддержкой watch
function labeled(fixture: { items: unknown[] }, kind: string, apiVersion: string) {
  return ({ request }: { request: Request }) => {
    const items = filterByLabels(fixture.items as unknown as LabeledObj[], request)
    if (isWatch(request)) return watchStream(items)
    return HttpResponse.json({ apiVersion, kind: `${kind}List`, metadata: { resourceVersion: "1" }, items })
  }
}

export const handlers = [
  // discovery
  http.get("/apis", () => HttpResponse.json(apis)),
  http.get("/api/v1", () => HttpResponse.json({ kind: "APIResourceList", groupVersion: "v1", resources: [] })),

  // каталог: ApplicationDefinition (группа cozystack.io, cluster-scoped)
  http.get(`${CORE}/applicationdefinitions`, ({ request }) =>
    isWatch(request) ? watchStream(appDefs.items as Obj[]) : HttpResponse.json(appDefs)),

  // тенанты пользователя (в демо — один, workshop00)
  http.get(`${CORE2}/tenantnamespaces`, ({ request }) =>
    isWatch(request) ? watchStream(tenantNamespaces.items as Obj[]) : HttpResponse.json(tenantNamespaces)),

  // ресурс info (модуль cozystack «info» — сводка тенанта); отдаём снапшот
  http.get(`${COZY}/namespaces/:ns/infos`, ({ request }) =>
    isWatch(request)
      ? watchStream([info as Obj])
      : HttpResponse.json({ apiVersion: "apps.cozystack.io/v1alpha1", kind: "InfoList", metadata: { resourceVersion: "1" }, items: [info] })),
  http.get(`${COZY}/namespaces/:ns/infos/:name`, () => HttpResponse.json(info)),

  // инстансы конкретного типа в namespace
  http.get(`${COZY}/namespaces/:ns/:resource`, ({ params, request }) => {
    const kind = kindForPlural(params.resource as string)
    const items = liveInstances.filter((i) => i.kind === kind)
    return isWatch(request) ? watchStream(items) : HttpResponse.json(list(items, kind ?? "Unknown"))
  }),

  // одиночный инстанс
  http.get(`${COZY}/namespaces/:ns/:resource/:name`, ({ params }) => {
    const kind = kindForPlural(params.resource as string)
    const obj = liveInstances.find((i) => i.kind === kind && i.metadata.name === params.name)
    return obj ? HttpResponse.json(obj) : new HttpResponse(null, { status: 404 })
  }),

  // namespace
  http.get(`/api/v1/namespaces/${NS}`, () => HttpResponse.json(namespace)),
  // опции для форм (storageClass, image, instancetype, backupclass, …)
  http.get(`${CORE2}/namespaces/:ns/options`, ({ request }) =>
    isWatch(request) ? watchStream(options.items as Obj[]) : HttpResponse.json(options)),



  // workloads/сервисы/тома/секреты/события инстанса (табы карточки) — фильтр по labelSelector
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
  http.get(`/api/v1/namespaces/:ns/persistentvolumeclaims`, labeled({ items: livePvcs }, "PersistentVolumeClaim", "v1")),
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

  // namespaced backup-ресурсы (Console → Backups: Plans/BackupJobs/Backups/RestoreJobs) — в демо пусто
  http.get(`/apis/backups.cozystack.io/v1alpha1/namespaces/:ns/:resource`, ({ params, request }) => {
    const kindMap: Record<string, string> = { plans: "Plan", backupjobs: "BackupJob", backups: "Backup", restorejobs: "RestoreJob" }
    const kind = kindMap[params.resource as string] ?? "Backup"
    return isWatch(request) ? watchStream([]) : HttpResponse.json(emptyList(kind, "backups.cozystack.io/v1alpha1"))
  }),

  // модули тенанта (Console → Administration → Modules)
  http.get(`${CORE2}/namespaces/:ns/tenantmodules`, ({ request }) =>
    isWatch(request) ? watchStream(tenantModulesNs.items as Obj[]) : HttpResponse.json(tenantModulesNs)),
  // модули по кластеру + список тенантов (Console → Administration → Tenants)
  http.get(`${CORE2}/tenantmodules`, ({ request }) =>
    isWatch(request) ? watchStream(tenantModulesAll.items as Obj[]) : HttpResponse.json(tenantModulesAll)),
  http.get(`/api/v1/resourcequotas`, ({ request }) =>
    isWatch(request) ? watchStream(clusterResourceQuotas.items as Obj[]) : HttpResponse.json(clusterResourceQuotas)),

  // CRD-схемы для форм создания backup-объектов (use-crd-schema)
  http.get(`/apis/apiextensions.k8s.io/v1/customresourcedefinitions/:name`, ({ params }) => {
    const crd = CRD_BY_NAME[params.name as string]
    return crd ? HttpResponse.json(crd) : new HttpResponse(null, { status: 404 })
  }),

  // конфиг дашборда и имя пользователя (оба graceful, но отдадим осмысленное)
  http.get("/api/v1/namespaces/cozy-dashboard/configmaps/cozy-dashboard-console-config", () =>
    new HttpResponse(null, { status: 404 })),
  http.get("/oauth2/userinfo", () => HttpResponse.json({ email: "demo@cozystack.io", user: "demo" })),

  // права: в демо всё разрешено
  http.post("/apis/authorization.k8s.io/v1/selfsubjectaccessreviews", async ({ request }) => {
    const body = (await request.json()) as { spec?: unknown }
    return HttpResponse.json({ apiVersion: "authorization.k8s.io/v1", kind: "SelfSubjectAccessReview", spec: body.spec ?? {}, status: { allowed: true } })
  }),

  // метрики узлов
  http.get("/api/v1/nodes", ({ request }) =>
    isWatch(request) ? watchStream(nodes.items as Obj[]) : HttpResponse.json(nodes)),
  http.get("/apis/storage.k8s.io/v1/storageclasses", ({ request }) =>
    isWatch(request) ? watchStream(storageClasses.items as Obj[]) : HttpResponse.json(storageClasses)),
  http.get("/apis/backups.cozystack.io/v1alpha1/backupclasses", ({ request }) =>
    isWatch(request) ? watchStream(backupClasses.items as Obj[]) : HttpResponse.json(backupClasses)),
  http.get("/apis/backups.cozystack.io/v1alpha1/backups", ({ request }) =>
    isWatch(request)
      ? watchStream([])
      : HttpResponse.json({ apiVersion: "backups.cozystack.io/v1alpha1", kind: "BackupList", metadata: { resourceVersion: "1" }, items: [] })),
  http.get("/apis/metrics.k8s.io/v1beta1/nodes", () => HttpResponse.json(nodeMetrics)),
  http.get("/apis/metrics.k8s.io/v1beta1/namespaces/:ns/pods", () =>
    HttpResponse.json({ kind: "PodMetricsList", apiVersion: "metrics.k8s.io/v1beta1", items: [] })),

  // Создание инстанса: появляется в состоянии установки и через ~9 c становится Ready.
  http.post(`${COZY}/namespaces/:ns/:resource`, async ({ params, request }) => {
    const kind = kindForPlural(params.resource as string)
    const sent = (await request.json()) as { metadata?: { name?: string }; spec?: unknown }
    const name = sent?.metadata?.name || `new-${kind.toLowerCase()}`
    const obj: Inst = {
      apiVersion: "apps.cozystack.io/v1alpha1", kind,
      metadata: { name, namespace: NS,
        creationTimestamp: new Date().toISOString(),
        uid: crypto.randomUUID(),
        labels: { "apps.cozystack.io/application.kind": kind, "apps.cozystack.io/application.name": name },
      } as Obj["metadata"],
      spec: sent?.spec ?? {},
      status: { conditions: [{ type: "Ready", status: "False", reason: "Installing", message: "Разворачивается…" }] },
    }
    liveInstances.push(obj)
    // Через ~9 c установка «завершается».
    setTimeout(() => {
      const c = obj.status?.conditions?.find((x) => x.type === "Ready")
      if (c) { c.status = "True"; c.reason = "InstallSucceeded"; c.message = "" }
    }, 9000)
    return HttpResponse.json(obj, { status: 201 })
  }),

  // всё прочее из apps.cozystack.io — пустой список, чтобы UI не падал
  http.get(`${COZY}/namespaces/:ns/:resource`, () => HttpResponse.json(list([], "Unknown"))),
]
