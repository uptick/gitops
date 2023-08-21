REPO ?= 305686791668.dkr.ecr.ap-southeast-2.amazonaws.com
ECR_REPO ?= gitops
TAG ?= $(shell git rev-parse --short HEAD)
IMAGE ?= ${REPO}/${ECR_REPO}:${TAG}
LATEST_IMAGE ?= ${REPO}/${ECR_REPO}:latest

# Print this help message
help:
	@echo
	@awk '/^#/ {c=substr($$0,3); next} c && /^([a-zA-Z].+):/{ print "  \033[32m" $$1 "\033[0m",c }{c=0}' $(MAKEFILE_LIST) |\
        sort |\
        column -s: -t |\
        less -R

# Test helm chart
helm/lint:
	helm install --dry-run --debug -f charts/gitops/values.yaml debug charts/gitops

# Bump release versions across all files
release:
	python release.py