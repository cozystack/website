# Defaults (override on the command line: `make update-apps APPS="tenant redis" DEST_DIR="..."`)
APPS       ?= tenant clickhouse redis ferretdb rabbitmq postgres nats kafka mysql
K8S       ?= kubernetes
VMS       ?= virtual-machine vm-disk vm-instance
NETWORKING       ?= vpn http-cache tcp-balancer
APPS_DEST_DIR   ?= content/en/docs/applications
K8S_DEST_DIR   ?= content/en/docs/
VMS_DEST_DIR   ?= content/en/docs/virtualization
NETWORKING_DEST_DIR   ?= content/en/docs/networking
BRANCH     ?= main

.PHONY: update-apps update-vms update-networking update-k8s update-all template-apps template-vms template-networking template-k8s template-all
update-apps:
	./hack/update_apps.sh --apps "$(APPS)" --dest "$(APPS_DEST_DIR)" --branch "$(BRANCH)"

update-vms:
	./hack/update_apps.sh --apps "$(VMS)" --dest "$(VMS_DEST_DIR)" --branch "$(BRANCH)"

update-networking:
	./hack/update_apps.sh --apps "$(NETWORKING)" --dest "$(NETWORKING_DEST_DIR)" --branch "$(BRANCH)"
update-k8s:
	./hack/update_apps.sh --apps "$(K8S)" --dest "$(K8S_DEST_DIR)" --branch "$(BRANCH)"

update-all:
	$(MAKE) update-apps
	$(MAKE) update-vms
	$(MAKE) update-networking
	$(MAKE) update-k8s

template-apps:
	./hack/fill_templates.sh --apps "$(APPS)" --dest "$(APPS_DEST_DIR)" --branch "$(BRANCH)"

template-vms:
	./hack/fill_templates.sh --apps "$(VMS)" --dest "$(VMS_DEST_DIR)" --branch "$(BRANCH)"

template-networking:
	./hack/fill_templates.sh --apps "$(NETWORKING)" --dest "$(NETWORKING_DEST_DIR)" --branch "$(BRANCH)"
template-k8s:
	./hack/fill_templates.sh --apps "$(K8S)" --dest "$(K8S_DEST_DIR)" --branch "$(BRANCH)"

template-all:
	$(MAKE) template-apps
	$(MAKE) template-vms
	$(MAKE) template-networking
	$(MAKE) template-k8s