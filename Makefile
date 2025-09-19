# Defaults (override on the command line: `make update-apps APPS="tenant redis" DEST_DIR="..."`)
APPS       ?= tenant clickhouse redis ferretdb rabbitmq postgres nats kafka mysql
K8S       ?= kubernetes
VMS       ?= virtual-machine vm-disk vm-instance
NETWORKING       ?= vpn http-cache tcp-balancer
SERVICES       ?= bootbox etcd ingress monitoring seaweedfs
APPS_DEST_DIR   ?= content/en/docs/applications
K8S_DEST_DIR   ?= content/en/docs
VMS_DEST_DIR   ?= content/en/docs/virtualization
NETWORKING_DEST_DIR   ?= content/en/docs/networking
SERVICES_DEST_DIR   ?= content/en/docs/operations/services
BRANCH     ?= main

.PHONY: update-apps update-vms update-networking update-k8s update-services update-all template-apps template-vms template-networking template-k8s template-services template-all
update-apps:
	./hack/update_apps.sh --apps "$(APPS)" --dest "$(APPS_DEST_DIR)" --branch "$(BRANCH)"

update-vms:
	./hack/update_apps.sh --apps "$(VMS)" --dest "$(VMS_DEST_DIR)" --branch "$(BRANCH)"

update-networking:
	./hack/update_apps.sh --apps "$(NETWORKING)" --dest "$(NETWORKING_DEST_DIR)" --branch "$(BRANCH)"

update-k8s:
	./hack/update_apps.sh --index --apps "$(K8S)" --dest "$(K8S_DEST_DIR)" --branch "$(BRANCH)"

update-services:
	./hack/update_apps.sh --apps "$(SERVICES)" --dest "$(SERVICES_DEST_DIR)" --branch "$(BRANCH)" --pkgdir extra

# requires cluster authentication
# to be replaced with downloading a build/release artifact from github.com/cozystack/cozystack
update-api:
	kubectl get --raw '/openapi/v3/apis/apps.cozystack.io/v1alpha1' > content/en/docs/cozystack-api/api.json

# doesn't include update-api, because it can't run in CI yet
update-all:
	$(MAKE) update-apps
	$(MAKE) update-vms
	$(MAKE) update-networking
	$(MAKE) update-k8s
	$(MAKE) update-services

template-apps:
	./hack/fill_templates.sh --apps "$(APPS)" --dest "$(APPS_DEST_DIR)" --branch "$(BRANCH)"

template-vms:
	./hack/fill_templates.sh --apps "$(VMS)" --dest "$(VMS_DEST_DIR)" --branch "$(BRANCH)"

template-networking:
	./hack/fill_templates.sh --apps "$(NETWORKING)" --dest "$(NETWORKING_DEST_DIR)" --branch "$(BRANCH)"
template-k8s:
	./hack/fill_templates.sh --apps "$(K8S)" --dest "$(K8S_DEST_DIR)" --branch "$(BRANCH)"

template-services:
	./hack/fill_templates.sh --apps "$(SERVICES)" --dest "$(SERVICES_DEST_DIR)" --branch "$(BRANCH)" --pkgdir extra

template-all:
	$(MAKE) template-apps
	$(MAKE) template-vms
	$(MAKE) template-networking
	$(MAKE) template-k8s
	$(MAKE) template-services

serve:
	echo http://localhost:1313/docs
	rm -rf public && hugo serve
