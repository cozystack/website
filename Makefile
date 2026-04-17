# Docs versioning with a permanent `next/` trunk.
#
# RELEASE_TAG drives routing between `next/` and released version directories:
#   - No RELEASE_TAG            → target `next/`, BRANCH=main
#   - RELEASE_TAG=vX.Y.Z and vX.Y/ already exists as a released (non-hidden)
#     version in hugo.yaml      → target `vX.Y/` (patch release, update in place)
#   - RELEASE_TAG=vX.Y.Z and vX.Y/ does not exist as a released version
#                               → target `next/` (upcoming release, still
#                                 accumulating in the trunk)
#
# When RELEASE_TAG is set, BRANCH is pinned to the exact tag for reproducible builds.
RELEASE_TAG ?=

# Derive the minor version (e.g., v1.2.1 → v1.2, v0.30.0 → v0) from RELEASE_TAG
ifdef RELEASE_TAG
  _ver := $(patsubst v%,%,$(RELEASE_TAG))
  _major := $(word 1,$(subst ., ,$(_ver)))
  _minor := $(word 2,$(subst ., ,$(_ver)))
  _release_version := $(if $(filter 0,$(_major)),v0,v$(_major).$(_minor))
  override BRANCH := $(RELEASE_TAG)
else
  _release_version :=
  BRANCH ?= main
endif

# Routing: DOC_VERSION is either a real vX.Y directory (patch releases of an
# already-released version) or `next` (everything else).
#
# A directory qualifies as "already released" iff it exists on disk AND is
# registered in hugo.yaml without hidden: true. The check uses yq when available
# and falls back to directory-existence-only when not (ok, since hidden entries
# other than `next` are not part of the new design).
ifdef RELEASE_TAG
  _routed_version := $(shell \
    if [ -d "content/en/docs/$(_release_version)" ]; then \
      if command -v yq >/dev/null 2>&1; then \
        hidden=$$(yq '.params.versions[] | select(.id == "$(_release_version)") | .hidden // false' hugo.yaml 2>/dev/null); \
        if [ "$$hidden" = "false" ]; then echo "$(_release_version)"; else echo "next"; fi; \
      else \
        echo "$(_release_version)"; \
      fi; \
    else \
      echo "next"; \
    fi)
  DOC_VERSION := $(_routed_version)
else
  DOC_VERSION ?= next
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
        init-version init-next release-next download-openapi download-openapi-all serve show-target

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

# (Re)create content/en/docs/next/ from the latest released version
init-next:
	rm -rf content/en/docs/next
	./hack/init_version.sh --version "next"

# Promote content/en/docs/next/ to a new released version (vX.Y/).
# Requires RELEASE_TAG; fails hard if next/ is empty or vX.Y/ already exists.
release-next:
ifndef RELEASE_TAG
	$(error RELEASE_TAG is required for release-next (e.g., make release-next RELEASE_TAG=v1.3.0))
endif
	./hack/release_next.sh --release-tag "$(RELEASE_TAG)"

# Print the resolved target directory for debugging
show-target:
	@echo "RELEASE_TAG=$(RELEASE_TAG)"
	@echo "DOC_VERSION=$(DOC_VERSION)"
	@echo "BRANCH=$(BRANCH)"

# Update the target directory in place. Routing rules above determine whether
# this writes into next/ or an existing released version directory.
# Does not include download-openapi (handled separately at build time).
update-all:
	$(MAKE) init-version
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
