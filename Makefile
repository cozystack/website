# Version derivation from RELEASE_TAG (e.g., v1.2.1 → DOC_VERSION=v1.2, BRANCH=v1.2.1)
# When RELEASE_TAG is set, BRANCH is pinned to the exact tag for reproducible builds.
RELEASE_TAG ?=
ifdef RELEASE_TAG
  _ver := $(patsubst v%,%,$(RELEASE_TAG))
  _major := $(word 1,$(subst ., ,$(_ver)))
  _minor := $(word 2,$(subst ., ,$(_ver)))
  DOC_VERSION := $(if $(filter 0,$(_major)),v0,v$(_major).$(_minor))
  # Next minor version for draft creation (v1.2 → v1.3); not computed for v0
  NEXT_DOC_VERSION := $(if $(filter 0,$(_major)),,v$(_major).$(shell echo $$(($(_minor)+1))))
  override BRANCH := $(RELEASE_TAG)
else
  DOC_VERSION ?= v1.2
  BRANCH ?= main
endif

# App lists (override on the command line: `make update-apps APPS="tenant redis"`)
APPS       ?= tenant clickhouse foundationdb harbor redis mongodb openbao rabbitmq postgres nats kafka mariadb qdrant
K8S       ?= kubernetes
VMS       ?= vm-disk vm-instance
NETWORKING       ?= vpc vpn http-cache tcp-balancer
SERVICES       ?= bootbox etcd ingress monitoring seaweedfs
APPS_DEST_DIR   ?= content/en/docs/$(DOC_VERSION)/applications
K8S_DEST_DIR   ?= content/en/docs/$(DOC_VERSION)
VMS_DEST_DIR   ?= content/en/docs/$(DOC_VERSION)/virtualization
NETWORKING_DEST_DIR   ?= content/en/docs/$(DOC_VERSION)/networking
SERVICES_DEST_DIR   ?= content/en/docs/$(DOC_VERSION)/operations/services

.PHONY: update-apps update-vms update-networking update-k8s update-services update-oss-health update-all \
        template-apps template-vms template-networking template-k8s template-services template-all \
        init-version register-version release-version add-draft download-openapi download-openapi-all serve

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

update-oss-health:
	./hack/update_oss_health.py

# Download openapi.json for a specific version from GitHub release
download-openapi:
ifndef RELEASE_TAG
	$(error RELEASE_TAG is required for download-openapi (e.g., make download-openapi RELEASE_TAG=v1.2.1))
endif
	@mkdir -p static/docs/$(DOC_VERSION)/cozystack-api
	@echo "Downloading openapi.json for $(RELEASE_TAG)..."
	@curl -fsSL -o static/docs/$(DOC_VERSION)/cozystack-api/api.json \
	  "https://github.com/cozystack/cozystack/releases/download/$(RELEASE_TAG)/openapi.json" \
	  && echo "✓ Downloaded openapi.json for $(DOC_VERSION)" \
	  || echo "⚠️  openapi.json not available for $(RELEASE_TAG)"

# Download openapi.json for all versions at build time
download-openapi-all:
	./hack/download_openapi.sh

# Initialize a new version directory from the previous version
init-version:
	./hack/init_version.sh --version "$(DOC_VERSION)"

# Register/update a version entry in hugo.yaml (used by other targets)
register-version:
	./hack/register_version.sh --release "$(DOC_VERSION)"

# Manually publish a hidden draft version (unhide + set as latest)
release-version:
	./hack/register_version.sh --release "$(DOC_VERSION)"

# Manually add a hidden draft version (content dir + hugo.yaml entry)
add-draft:
	./hack/init_version.sh --version "$(DOC_VERSION)"
	./hack/register_version.sh --draft "$(DOC_VERSION)"

# doesn't include download-openapi (handled separately at build time)
# When RELEASE_TAG is set: publishes DOC_VERSION and creates NEXT_DOC_VERSION as hidden draft
update-all:
	$(MAKE) init-version
	$(MAKE) update-apps
	$(MAKE) update-vms
	$(MAKE) update-networking
	$(MAKE) update-k8s
	$(MAKE) update-services
ifdef RELEASE_TAG
	$(MAKE) register-version
  ifneq ($(NEXT_DOC_VERSION),)
	$(MAKE) add-draft DOC_VERSION=$(NEXT_DOC_VERSION)
  endif
endif

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
