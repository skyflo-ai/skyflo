#!/usr/bin/env bash

# Skyflo Production-Grade Uninstall Script
# 
# A highly resilient, context-aware script to safely uninstall Skyflo from a Kubernetes cluster.
# It enforces multi-tenant cluster safety guarantees, protects against destructive ambiguity,
# and handles failing cluster operations gracefully.

set -uo pipefail

# --- Configuration & Defaults ---
NAMESPACE=${NAMESPACE:-"skyflo"}
RELEASE_NAME=${RELEASE_NAME:-"skyflo"}
LABEL_SELECTOR=${LABEL_SELECTOR:-"app.kubernetes.io/name=skyflo"}
DRY_RUN=false
FORCE=false
VERBOSE=false
TIMEOUT="90s"

# Initialization of summary arrays
SUMMARY_DELETED=()
SUMMARY_FAILED=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# --- Helper Functions ---
log_info() { echo -e "${CYAN}➜${NC} $1"; }
log_success() { echo -e "${GREEN}✔${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠ WARNING:${NC} $1"; }
log_error() { echo -e "${RED}✖ ERROR:${NC} $1"; }
log_verbose() { 
    if [[ "$VERBOSE" == "true" ]]; then 
        echo -e "${BLUE}  [DEBUG] $1${NC}"; 
    fi 
}

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run   Print actions to be performed without executing them"
    echo "  --force     Skip confirmation prompts"
    echo "  --verbose   Enable detailed debug logging"
    echo "  -h, --help  Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  NAMESPACE       (default: skyflo)"
    echo "  RELEASE_NAME    (default: skyflo)"
    echo "  LABEL_SELECTOR  (default: app.kubernetes.io/name=skyflo)"
}

# --- Resilience & State ---
retry_command() {
    local max_attempts=3
    local attempt=1
    local backoff=2
    local cmd=("$@")

    while [[ $attempt -le $max_attempts ]]; do
        log_verbose "Executing: ${cmd[*]}"
        if "${cmd[@]}" >/dev/null 2>&1; then
            return 0
        fi
        
        if [[ $attempt -lt $max_attempts ]]; then
            log_warn "Command failed (attempt $attempt/$max_attempts). Retrying in ${backoff}s..."
            sleep $backoff
        fi
        ((attempt++))
        ((backoff=backoff * 2))
    done
    
    log_verbose "Command definitively failed after $max_attempts attempts: ${cmd[*]}"
    return 1
}

# --- Prerequisite Validations ---
check_dependencies() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required but not installed."
        exit 1
    fi
    if ! command -v helm &> /dev/null; then
        log_warn "helm is not installed. Helm-specific cleanup will be skipped."
    else
        log_verbose "Helm dependency found."
    fi
}

check_cluster_context() {
    if ! CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null); then
        log_error "Cannot get current Kubernetes context. Please check your kubeconfig."
        exit 1
    fi
    
    if ! kubectl get nodes &> /dev/null; then
        log_error "Cannot connect to the Kubernetes cluster '$CURRENT_CONTEXT'. Please check your kubeconfig."
        exit 1
    fi
}

protect_critical_namespaces() {
    local critical_ns=("kube-system" "default" "kube-public" "kube-node-lease")
    for ns in "${critical_ns[@]}"; do
        if [[ "$NAMESPACE" == "$ns" ]]; then
            log_error "Refusing to operate on critical namespace: '$NAMESPACE'."
            log_error "You must explicitly remove resources from '$NAMESPACE' to prevent accidental cluster damage."
            exit 1
        fi
    done
}

# --- Safety Prompts ---
prompt_standard_confirmation() {
    if [[ "$FORCE" == "true" ]]; then return 0; fi
    # shellcheck disable=SC2162
    read -p "$(echo -e "${YELLOW}Are you sure you want to completely remove Skyflo from cluster context: [${RED}${CURRENT_CONTEXT}${YELLOW}]? (y/N): ${NC}")" confirm
    case "$confirm" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

prompt_crd_confirmation() {
    if [[ "$FORCE" == "true" ]]; then return 0; fi
    echo ""
    echo -e "${RED}================================================================${NC}"
    echo -e "${RED}⚠ DANGER ZONE: CRD DELETION ⚠${NC}"
    echo -e "${RED}CRDs may contain persistent user data shared across environments!${NC}"
    echo -e "${RED}Deleting them is IRREVERSIBLE and will destroy custom resources.${NC}"
    echo -e "${RED}================================================================${NC}"
    
    # shellcheck disable=SC2162
    read -p "$(echo -e "${YELLOW}Are you ABSOLUTELY sure you want to delete CRDs? (type 'delete-crds' to confirm): ${NC}")" confirm
    if [[ "$confirm" == "delete-crds" ]]; then
        return 0
    fi
    return 1
}

# --- Core Cleanup Operations ---

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run) DRY_RUN=true; shift ;;
            --force) FORCE=true; shift ;;
            --verbose) VERBOSE=true; shift ;;
            -h|--help) print_usage; exit 0 ;;
            *) log_error "Unknown option: $1"; print_usage; exit 1 ;;
        esac
    done
}

cleanup_helm() {
    echo ""
    log_info "STEP 1: Checking Helm Release"
    if ! command -v helm &> /dev/null; then
        log_verbose "Helm CLI not found. Skipping Helm cleanup."
        return
    fi

    if helm status "$RELEASE_NAME" -n "$NAMESPACE" &> /dev/null; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY-RUN] Will attempt to uninstall helm release '$RELEASE_NAME' in namespace '$NAMESPACE'"
            return
        fi

        log_info "Uninstalling Helm release '$RELEASE_NAME'..."
        if retry_command helm uninstall "$RELEASE_NAME" -n "$NAMESPACE"; then
            log_success "Helm release '$RELEASE_NAME' uninstalled."
            SUMMARY_DELETED+=("Helm Release: $RELEASE_NAME")
        else
            log_error "Failed to cleanly uninstall Helm release '$RELEASE_NAME'."
            SUMMARY_FAILED+=("Helm Release: $RELEASE_NAME")
        fi
    else
        log_verbose "No Helm release named '$RELEASE_NAME' found in namespace '$NAMESPACE'. Proceeding..."
    fi
}

cleanup_cluster_scoped_non_crd() {
    echo ""
    log_info "STEP 2: Scanning for Cluster-Scoped Resources (Non-CRD)"
    local res_types="clusterrole,clusterrolebinding,mutatingwebhookconfiguration,validatingwebhookconfiguration"
    
    # Only get exact matches generated by our app label
    local detected
    detected=$(kubectl get "$res_types" -l "$LABEL_SELECTOR" -o name 2>/dev/null || true)
    
    if [[ -z "$detected" ]]; then
        log_verbose "No cluster-scoped non-CRD resources found matching label '$LABEL_SELECTOR'."
        return
    fi

    log_warn "Discovered the following cluster-scoped resources:"
    for r in $detected; do echo "  - $r"; done

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Will delete above cluster-scoped resources."
        return
    fi

    log_info "Deleting detected cluster-scoped resources..."
    for res in $detected; do
        if retry_command kubectl delete "$res" --timeout="$TIMEOUT" --ignore-not-found=true; then
            log_success "Deleted resource: $res"
            SUMMARY_DELETED+=("Cluster Resource: $res")
        else
            log_error "Failed to delete: $res"
            SUMMARY_FAILED+=("Cluster Resource: $res")
        fi
    done
}

cleanup_crds() {
    echo ""
    log_info "STEP 3: Scanning for Custom Resource Definitions (CRDs)"
    
    local crds
    crds=$(kubectl get crds -l "$LABEL_SELECTOR" -o name 2>/dev/null || true)

    if [[ -z "$crds" ]]; then
        log_verbose "No CRDs found matching label '$LABEL_SELECTOR'."
        return
    fi
    
    log_warn "Discovered Skyflo CRDs:"
    for crd in $crds; do echo "  - $crd"; done

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Will prompt to safely delete above CRDs."
        return
    fi

    if prompt_crd_confirmation; then
        log_info "Proceeding with CRD destruction..."
        for crd in $crds; do
            if retry_command kubectl delete "$crd" --timeout="$TIMEOUT" --ignore-not-found=true; then
                log_success "Deleted CRD: $crd"
                SUMMARY_DELETED+=("CRD: $crd")
            else
                log_error "Failed to delete CRD: $crd"
                SUMMARY_FAILED+=("CRD: $crd")
            fi
        done
    else
        log_info "Skipping CRD deletion. Custom resources remain safe."
    fi
}

cleanup_namespace() {
    echo ""
    log_info "STEP 4: Namespace Teardown"

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_verbose "Namespace '$NAMESPACE' does not exist."
        return
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Will attempt to delete namespace '$NAMESPACE' with $TIMEOUT timeout."
        return
    fi

    log_info "Deleting namespace '$NAMESPACE' (timeout: $TIMEOUT)..."
    
    # Using direct command here instead of retry since namespace deletions have internal finalizer handling that retry won't fix
    log_verbose "Executing: kubectl delete namespace $NAMESPACE --wait=true --timeout=$TIMEOUT --ignore-not-found=true"
    if kubectl delete namespace "$NAMESPACE" --wait=true --timeout="$TIMEOUT" --ignore-not-found=true >/dev/null 2>&1; then
        log_success "Namespace '$NAMESPACE' deleted."
        SUMMARY_DELETED+=("Namespace: $NAMESPACE")
    else
        log_error "Namespace deletion timed out or failed!"
        log_error "It is highly likely stuck on a broken finalizer."
        log_warn "To forcefully remove finalizers and delete the namespace, run manually:"
        echo -e "      ${YELLOW}kubectl patch namespace $NAMESPACE -p '{\"metadata\":{\"finalizers\":[]}}' --type=merge${NC}"
        SUMMARY_FAILED+=("Namespace: $NAMESPACE (Stuck Finalizer)")
    fi
}

print_summary() {
    echo ""
    echo -e "${CYAN}==========================================${NC}"
    echo -e "${CYAN}         UNINSTALLATION SUMMARY           ${NC}"
    echo -e "${CYAN}==========================================${NC}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}Dry-run completed successfully. No changes were made.${NC}"
        return
    fi

    if [[ ${#SUMMARY_DELETED[@]} -eq 0 && ${#SUMMARY_FAILED[@]} -eq 0 ]]; then
        echo -e "${GREEN}Nothing to do. System is completely clean!${NC}"
        return
    fi

    if [[ ${#SUMMARY_DELETED[@]} -gt 0 ]]; then
        echo -e "${GREEN}Successfully Deleted:${NC}"
        for item in "${SUMMARY_DELETED[@]}"; do
            echo "  ✔ $item"
        done
        echo ""
    fi

    if [[ ${#SUMMARY_FAILED[@]} -gt 0 ]]; then
        echo -e "${RED}Failed to Delete / Needs Manual Intervention:${NC}"
        for item in "${SUMMARY_FAILED[@]}"; do
            echo "  ✖ $item"
        done
        echo ""
        log_warn "Uninstall finished with partial errors. Please review the failed items above."
    else
        log_success "Uninstall completed flawlessly! 🎉"
    fi
}

main() {
    parse_args "$@"
    
    # 0. Safety Boundaries
    check_dependencies
    protect_critical_namespaces
    check_cluster_context

    echo -e "${CYAN}==========================================${NC}"
    echo -e "         ${BLUE}Skyflo Uninstaller${NC}               "
    echo -e "${CYAN}==========================================${NC}"
    echo -e "Target Namespace:  ${YELLOW}${NAMESPACE}${NC}"
    echo -e "Target Release:    ${YELLOW}${RELEASE_NAME}${NC}"
    echo -e "Label Selector:    ${YELLOW}${LABEL_SELECTOR}${NC}"
    echo -e "Current Context:   ${RED}${CURRENT_CONTEXT}${NC}"
    echo -e "${CYAN}==========================================${NC}"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}!!! DRY-RUN MODE ENABLED - NO RESOURCES WILL BE MODIFIED !!!${NC}"
    else
        if ! prompt_standard_confirmation; then
            log_info "Uninstall aborted by user."
            exit 0
        fi
    fi

    # Best-effort execution of phases
    cleanup_helm
    cleanup_cluster_scoped_non_crd
    cleanup_crds
    cleanup_namespace
    
    print_summary
}

main "$@"
