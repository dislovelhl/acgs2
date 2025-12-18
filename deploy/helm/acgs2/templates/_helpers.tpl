{{/*
ACGS-2 Helm Chart Helpers
Constitutional Hash: cdd01ef066bc6cf2
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "acgs2.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
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
acgs.io/constitutional-hash: {{ .Values.global.constitutionalHash | quote }}
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
Constitutional Service name
*/}}
{{- define "acgs2.constitutionalService.fullname" -}}
{{- printf "%s-constitutional" (include "acgs2.fullname" .) }}
{{- end }}

{{/*
Policy Registry name
*/}}
{{- define "acgs2.policyRegistry.fullname" -}}
{{- printf "%s-policy-registry" (include "acgs2.fullname" .) }}
{{- end }}

{{/*
Agent Bus name
*/}}
{{- define "acgs2.agentBus.fullname" -}}
{{- printf "%s-agent-bus" (include "acgs2.fullname" .) }}
{{- end }}

{{/*
API Gateway name
*/}}
{{- define "acgs2.apiGateway.fullname" -}}
{{- printf "%s-api-gateway" (include "acgs2.fullname" .) }}
{{- end }}

{{/*
Audit Service name
*/}}
{{- define "acgs2.auditService.fullname" -}}
{{- printf "%s-audit" (include "acgs2.fullname" .) }}
{{- end }}

{{/*
OPA name
*/}}
{{- define "acgs2.opa.fullname" -}}
{{- printf "%s-opa" (include "acgs2.fullname" .) }}
{{- end }}

{{/*
PostgreSQL host
*/}}
{{- define "acgs2.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "acgs2.fullname" .) }}
{{- else }}
{{- .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "acgs2.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" (include "acgs2.fullname" .) }}
{{- else }}
{{- .Values.externalRedis.host }}
{{- end }}
{{- end }}

{{/*
Kafka bootstrap servers
*/}}
{{- define "acgs2.kafka.bootstrapServers" -}}
{{- if .Values.kafka.enabled }}
{{- printf "%s-kafka:9092" (include "acgs2.fullname" .) }}
{{- else }}
{{- .Values.agentBus.kafka.bootstrapServers }}
{{- end }}
{{- end }}

{{/*
Common environment variables for constitutional compliance
*/}}
{{- define "acgs2.constitutionalEnv" -}}
- name: CONSTITUTIONAL_HASH
  value: {{ .Values.global.constitutionalHash | quote }}
- name: CONSTITUTIONAL_ENFORCEMENT
  value: "strict"
- name: AUDIT_LEVEL
  value: "comprehensive"
{{- end }}

{{/*
Database environment variables
*/}}
{{- define "acgs2.databaseEnv" -}}
- name: DATABASE_HOST
  value: {{ include "acgs2.postgresql.host" . }}
- name: DATABASE_PORT
  value: "5432"
- name: DATABASE_NAME
  value: {{ .Values.postgresql.auth.database | quote }}
- name: DATABASE_USER
  valueFrom:
    secretKeyRef:
      name: {{ include "acgs2.fullname" . }}-db-credentials
      key: username
- name: DATABASE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "acgs2.fullname" . }}-db-credentials
      key: password
{{- end }}

{{/*
Redis environment variables
*/}}
{{- define "acgs2.redisEnv" -}}
- name: REDIS_HOST
  value: {{ include "acgs2.redis.host" . }}
- name: REDIS_PORT
  value: "6379"
{{- if .Values.redis.auth.enabled }}
- name: REDIS_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "acgs2.fullname" . }}-redis-credentials
      key: password
{{- end }}
{{- end }}

{{/*
Kafka environment variables
*/}}
{{- define "acgs2.kafkaEnv" -}}
- name: KAFKA_BOOTSTRAP_SERVERS
  value: {{ include "acgs2.kafka.bootstrapServers" . }}
- name: KAFKA_CONSUMER_GROUP_ID
  value: {{ .Values.agentBus.kafka.consumer.groupId | quote }}
- name: KAFKA_AUTO_OFFSET_RESET
  value: {{ .Values.agentBus.kafka.consumer.autoOffsetReset | quote }}
- name: KAFKA_PRODUCER_ACKS
  value: {{ .Values.agentBus.kafka.producer.acks | quote }}
{{- end }}

{{/*
Pod security context
*/}}
{{- define "acgs2.podSecurityContext" -}}
runAsNonRoot: {{ .Values.podSecurityContext.runAsNonRoot }}
runAsUser: {{ .Values.podSecurityContext.runAsUser }}
runAsGroup: {{ .Values.podSecurityContext.runAsGroup }}
fsGroup: {{ .Values.podSecurityContext.fsGroup }}
{{- end }}

{{/*
Container security context
*/}}
{{- define "acgs2.securityContext" -}}
allowPrivilegeEscalation: {{ .Values.securityContext.allowPrivilegeEscalation }}
readOnlyRootFilesystem: {{ .Values.securityContext.readOnlyRootFilesystem }}
capabilities:
  drop:
    {{- range .Values.securityContext.capabilities.drop }}
    - {{ . }}
    {{- end }}
{{- end }}

{{/*
Image pull secrets
*/}}
{{- define "acgs2.imagePullSecrets" -}}
{{- if .Values.global.imagePullSecrets }}
imagePullSecrets:
  {{- range .Values.global.imagePullSecrets }}
  - name: {{ . }}
  {{- end }}
{{- end }}
{{- end }}

{{/*
Render image with optional registry
*/}}
{{- define "acgs2.image" -}}
{{- $registry := .registry | default "" -}}
{{- $repository := .repository -}}
{{- $tag := .tag | default "latest" -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repository $tag -}}
{{- else -}}
{{- printf "%s:%s" $repository $tag -}}
{{- end -}}
{{- end -}}
