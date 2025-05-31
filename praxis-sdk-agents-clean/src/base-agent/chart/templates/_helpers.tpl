{{/*
Expand the name of the chart.
*/}}
{{- define "base-agent.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "base-agent.fullname" -}}
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
Create chart name and version as used by the chart label.
*/}}
{{- define "base-agent.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "base-agent.labels" -}}
helm.sh/chart: {{ include "base-agent.chart" . }}
{{ include "base-agent.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "base-agent.selectorLabels" -}}
app.kubernetes.io/name: {{ include "base-agent.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- /*
  generateServeConfigV2 creates the full serveConfigV2 structure with default values,
  using only the pipPackages provided by the user.
*/}}
{{- define "base-agent.serveConfigV2" -}}
http_options:
  host: 0.0.0.0
  port: 8000
applications:
- name: base-agent-app
  import_path: entrypoint:app
  route_prefix: "/api/v1"
  runtime_env:
    pip: {{ .Values.pip | default list | toYaml | nindent 6 }}
    env_vars: {{ .Values.environment | default dict | toYaml | nindent 6 }}
{{- end -}}
