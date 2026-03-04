{{/*
Expand the name of the chart.
*/}}
{{- define "skyflo.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name.
If the release name contains the chart name it will be used as the full name.
*/}}
{{- define "skyflo.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart name and version for the chart label.
*/}}
{{- define "skyflo.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every resource.
*/}}
{{- define "skyflo.labels" -}}
helm.sh/chart: {{ include "skyflo.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- end }}

{{/*
Default image tag: component tag > global tag > v<appVersion>.
*/}}
{{- define "skyflo.defaultTag" -}}
{{- .Values.global.imageTag | default (printf "v%s" .Chart.AppVersion) }}
{{- end }}

{{/* ---- Component full names ---- */}}

{{- define "skyflo.engine.fullname" -}}
{{- printf "%s-engine" (include "skyflo.fullname" .) }}
{{- end }}

{{- define "skyflo.mcp.fullname" -}}
{{- printf "%s-mcp" (include "skyflo.fullname" .) }}
{{- end }}

{{- define "skyflo.ui.fullname" -}}
{{- printf "%s-ui" (include "skyflo.fullname" .) }}
{{- end }}

{{- define "skyflo.controller.fullname" -}}
{{- printf "%s-controller" (include "skyflo.fullname" .) }}
{{- end }}

{{- define "skyflo.postgres.fullname" -}}
{{- printf "%s-postgres" (include "skyflo.fullname" .) }}
{{- end }}

{{- define "skyflo.redis.fullname" -}}
{{- printf "%s-redis" (include "skyflo.fullname" .) }}
{{- end }}

{{/* ---- Secret names ---- */}}

{{- define "skyflo.engine.secretName" -}}
{{- if .Values.engine.secrets.existingSecret }}
{{- .Values.engine.secrets.existingSecret }}
{{- else }}
{{- printf "%s-secrets" (include "skyflo.engine.fullname" .) }}
{{- end }}
{{- end }}

{{- define "skyflo.postgres.secretName" -}}
{{- if .Values.postgresql.auth.existingSecret }}
{{- .Values.postgresql.auth.existingSecret }}
{{- else }}
{{- printf "%s-secrets" (include "skyflo.postgres.fullname" .) }}
{{- end }}
{{- end }}

{{/* ---- ConfigMap names ---- */}}

{{- define "skyflo.engine.configMapName" -}}
{{- printf "%s-config" (include "skyflo.engine.fullname" .) }}
{{- end }}

{{- define "skyflo.mcp.configMapName" -}}
{{- printf "%s-config" (include "skyflo.mcp.fullname" .) }}
{{- end }}

{{- define "skyflo.ui.configMapName" -}}
{{- printf "%s-config" (include "skyflo.ui.fullname" .) }}
{{- end }}

{{/* ---- Auto-generated secrets (preserved across upgrades) ---- */}}

{{- define "skyflo.postgres.password" -}}
{{- if .Values.postgresql.auth.password }}
{{- .Values.postgresql.auth.password }}
{{- else }}
{{- $existing := lookup "v1" "Secret" .Release.Namespace (include "skyflo.postgres.secretName" .) }}
{{- if and $existing $existing.data (index $existing.data "POSTGRES_PASSWORD") }}
{{- index $existing.data "POSTGRES_PASSWORD" | b64dec }}
{{- else }}
{{- randAlphaNum 32 }}
{{- end }}
{{- end }}
{{- end }}

{{- define "skyflo.jwtSecret" -}}
{{- if .Values.engine.secrets.jwtSecret }}
{{- .Values.engine.secrets.jwtSecret }}
{{- else }}
{{- $secretName := include "skyflo.engine.secretName" . }}
{{- $existing := lookup "v1" "Secret" .Release.Namespace $secretName }}
{{- if and $existing $existing.data (index $existing.data "JWT_SECRET") }}
{{- index $existing.data "JWT_SECRET" | b64dec }}
{{- else }}
{{- randAlphaNum 32 }}
{{- end }}
{{- end }}
{{- end }}

{{/* ---- Internal service URLs ---- */}}

{{- define "skyflo.postgres.host" -}}
{{- if .Values.postgresql.enabled }}
{{- include "skyflo.postgres.fullname" . }}
{{- else }}
{{- required "postgresql.external.host is required when postgresql.enabled=false" .Values.postgresql.external.host }}
{{- end }}
{{- end }}

{{- define "skyflo.postgres.port" -}}
{{- if .Values.postgresql.enabled }}
{{- .Values.postgresql.auth.port }}
{{- else }}
{{- .Values.postgresql.external.port | default 5432 }}
{{- end }}
{{- end }}

{{- define "skyflo.postgres.url" -}}
{{- if and (not .Values.postgresql.enabled) .Values.postgresql.external.url }}
{{- .Values.postgresql.external.url }}
{{- else }}
{{- $host := include "skyflo.postgres.host" . }}
{{- $port := include "skyflo.postgres.port" . }}
{{- if .Values.postgresql.enabled }}
{{- printf "postgres://%s:%s@%s:%v/%s" .Values.postgresql.auth.username (include "skyflo.postgres.password" .) $host $port .Values.postgresql.auth.database }}
{{- else }}
{{- printf "postgres://%s:%s@%s:%v/%s" .Values.postgresql.external.username .Values.postgresql.external.password $host $port .Values.postgresql.external.database }}
{{- end }}
{{- end }}
{{- end }}

{{- define "skyflo.redis.url" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://%s:6379/0" (include "skyflo.redis.fullname" .) }}
{{- else }}
{{- required "redis.external.url is required when redis.enabled=false" .Values.redis.external.url }}
{{- end }}
{{- end }}

{{- define "skyflo.mcp.url" -}}
{{- if .Values.engine.secrets.mcpServerUrl }}
{{- .Values.engine.secrets.mcpServerUrl }}
{{- else }}
{{- printf "http://%s:8888/mcp" (include "skyflo.mcp.fullname" .) }}
{{- end }}
{{- end }}

{{- define "skyflo.engine.apiUrl" -}}
{{- if .Values.ui.config.apiUrl }}
{{- .Values.ui.config.apiUrl }}
{{- else }}
{{- printf "http://%s:8080/api/v1" (include "skyflo.engine.fullname" .) }}
{{- end }}
{{- end }}

{{- define "skyflo.integrationsSecretNamespace" -}}
{{- .Values.engine.secrets.integrationsSecretNamespace | default .Release.Namespace }}
{{- end }}
