{{/*
Expand the name of the chart.
*/}}
{{- define "ollama-local-serve.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ollama-local-serve.fullname" -}}
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
{{- define "ollama-local-serve.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ollama-local-serve.labels" -}}
helm.sh/chart: {{ include "ollama-local-serve.chart" . }}
{{ include "ollama-local-serve.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ollama-local-serve.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ollama-local-serve.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ollama-local-serve.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ollama-local-serve.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Ollama service name
*/}}
{{- define "ollama-local-serve.ollama.fullname" -}}
{{- printf "%s-ollama" (include "ollama-local-serve.fullname" .) }}
{{- end }}

{{/*
API service name
*/}}
{{- define "ollama-local-serve.api.fullname" -}}
{{- printf "%s-api" (include "ollama-local-serve.fullname" .) }}
{{- end }}

{{/*
Frontend service name
*/}}
{{- define "ollama-local-serve.frontend.fullname" -}}
{{- printf "%s-frontend" (include "ollama-local-serve.fullname" .) }}
{{- end }}

{{/*
ClickHouse host - use simple name if Bitnami chart disabled
*/}}
{{- define "ollama-local-serve.clickhouse.host" -}}
{{- if .Values.clickhouse.enabled }}
{{- printf "%s-clickhouse" .Release.Name }}
{{- else }}
{{- "clickhouse" }}
{{- end }}
{{- end }}

{{/*
PostgreSQL host - use simple name if Bitnami chart disabled
*/}}
{{- define "ollama-local-serve.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" .Release.Name }}
{{- else }}
{{- "postgres" }}
{{- end }}
{{- end }}
