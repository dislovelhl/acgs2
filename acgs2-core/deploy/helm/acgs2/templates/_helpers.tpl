{{/*
Expand the name of the chart.
*/}}
{{- define "acgs2.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "acgs2.fullname" -}}
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
{{- define "acgs2.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "acgs2.labels" -}}
helm.sh/chart: {{ include "acgs2.chart" . }}
{{ include "acgs2.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: acgs2
acgs2/constitutional-hash: {{ .Values.global.constitutionalHash }}
acgs2/tenant-id: {{ .Values.global.tenantId }}
acgs2/environment: {{ .Values.global.env }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "acgs2.selectorLabels" -}}
app.kubernetes.io/name: {{ include "acgs2.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "acgs2.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "acgs2.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the proper image name
*/}}
{{- define "acgs2.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- end }}

{{/*
Return the proper image pull policy
*/}}
{{- define "acgs2.imagePullPolicy" -}}
{{- .Values.image.pullPolicy | default "IfNotPresent" }}
{{- end }}

{{/*
Create a default fully qualified postgresql name.
*/}}
{{- define "acgs2.postgresql.fullname" -}}
{{- printf "%s-%s" .Release.Name "postgresql" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified redis name.
*/}}
{{- define "acgs2.redis.fullname" -}}
{{- printf "%s-%s" .Release.Name "redis" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified kafka name.
*/}}
{{- define "acgs2.kafka.fullname" -}}
{{- printf "%s-%s" .Release.Name "kafka" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified opa name.
*/}}
{{- define "acgs2.opa.fullname" -}}
{{- printf "%s-%s" .Release.Name "opa" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified prometheus name.
*/}}
{{- define "acgs2.prometheus.fullname" -}}
{{- printf "%s-%s" .Release.Name "prometheus" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified grafana name.
*/}}
{{- define "acgs2.grafana.fullname" -}}
{{- printf "%s-%s" .Release.Name "grafana" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common tenant labels
*/}}
{{- define "acgs2.tenantLabels" -}}
acgs2/tenant-id: {{ .Values.global.tenantId }}
acgs2/constitutional-hash: {{ .Values.global.constitutionalHash }}
{{- end }}

{{/*
Security context helper
*/}}
{{- define "acgs2.securityContext" -}}
runAsNonRoot: true
runAsUser: 1000
runAsGroup: 1000
allowPrivilegeEscalation: false
capabilities:
  drop:
  - ALL
readOnlyRootFilesystem: true
{{- end }}

{{/*
Resource limits helper for high-performance services
*/}}
{{- define "acgs2.resources.highPerformance" -}}
limits:
  cpu: 2000m
  memory: 4Gi
requests:
  cpu: 1000m
  memory: 2Gi
{{- end }}

{{/*
Resource limits helper for standard services
*/}}
{{- define "acgs2.resources.standard" -}}
limits:
  cpu: 1000m
  memory: 2Gi
requests:
  cpu: 500m
  memory: 1Gi
{{- end }}

{{/*
Resource limits helper for lightweight services
*/}}
{{- define "acgs2.resources.lightweight" -}}
limits:
  cpu: 500m
  memory: 1Gi
requests:
  cpu: 250m
  memory: 512Mi
{{- end }}

{{/*
Generate random password
*/}}
{{- define "acgs2.generatePassword" -}}
{{- randAlphaNum 32 | b64enc }}
{{- end }}

{{/*
Database URL helper
*/}}
{{- define "acgs2.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "postgresql://%s:%s@%s-postgresql:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password (include "acgs2.postgresql.fullname" .) .Values.postgresql.auth.database }}
{{- else }}
{{- .Values.externalDatabase.url }}
{{- end }}
{{- end }}

{{/*
Redis URL helper
*/}}
{{- define "acgs2.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://%s-redis-master:6379" (include "acgs2.redis.fullname" .) }}
{{- else }}
{{- .Values.externalRedis.url }}
{{- end }}
{{- end }}

{{/*
Kafka bootstrap servers helper
*/}}
{{- define "acgs2.kafkaBootstrapServers" -}}
{{- if .Values.kafka.enabled }}
{{- printf "%s-kafka:9092" (include "acgs2.kafka.fullname" .) }}
{{- else }}
{{- .Values.externalKafka.bootstrapServers }}
{{- end }}
{{- end }}
