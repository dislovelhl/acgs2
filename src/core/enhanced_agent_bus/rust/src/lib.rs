mod security;
mod deliberation;
mod opa;
mod audit;
#[cfg(test)]
mod tests;

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use uuid::Uuid;
use chrono::Utc;
use dashmap::DashMap;
use parking_lot::RwLock as ParkingRwLock;

use security::detect_prompt_injection;
use deliberation::{ImpactScorer, AdaptiveRouter};
use opa::OpaClient;
use audit::AuditClient;

/// Constitutional hash for ACGS-2 compliance
const CONSTITUTIONAL_HASH: &str = "cdd01ef066bc6cf2";

/// Message types for agent communication
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[pyclass]
pub enum MessageType {
    Command,
    Query,
    Response,
    Event,
    Notification,
    Heartbeat,
    GovernanceRequest,
    GovernanceResponse,
    ConstitutionalValidation,
    TaskRequest,
    TaskResponse,
}

/// Message priority levels
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[pyclass]
pub enum MessagePriority {
    Critical = 0,
    High = 1,
    Normal = 2,
    Low = 3,
}

/// Message processing status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[pyclass]
pub enum MessageStatus {
    Pending,
    Processing,
    Delivered,
    Failed,
    Expired,
    Deliberation,
}

/// Routing context for message delivery
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct RoutingContext {
    #[pyo3(get, set)]
    pub source_agent_id: String,
    #[pyo3(get, set)]
    pub target_agent_id: String,
    #[pyo3(get, set)]
    pub routing_key: String,
    #[pyo3(get, set)]
    pub routing_tags: Vec<String>,
    #[pyo3(get, set)]
    pub retry_count: i32,
    #[pyo3(get, set)]
    pub max_retries: i32,
    #[pyo3(get, set)]
    pub timeout_ms: i32,
    #[pyo3(get, set)]
    pub constitutional_hash: String,
}

/// Agent message structure
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct AgentMessage {
    #[pyo3(get, set)]
    pub message_id: String,
    #[pyo3(get, set)]
    pub conversation_id: String,
    #[pyo3(get, set)]
    pub content: HashMap<String, String>,
    #[pyo3(get, set)]
    pub payload: HashMap<String, String>,
    #[pyo3(get, set)]
    pub from_agent: String,
    #[pyo3(get, set)]
    pub to_agent: String,
    #[pyo3(get, set)]
    pub sender_id: String,
    #[pyo3(get, set)]
    pub message_type: MessageType,
    #[pyo3(get, set)]
    pub routing: Option<RoutingContext>,
    #[pyo3(get, set)]
    pub headers: HashMap<String, String>,
    #[pyo3(get, set)]
    pub tenant_id: String,
    #[pyo3(get, set)]
    pub security_context: HashMap<String, String>,
    #[pyo3(get, set)]
    pub priority: MessagePriority,
    #[pyo3(get, set)]
    pub status: MessageStatus,
    #[pyo3(get, set)]
    pub constitutional_hash: String,
    #[pyo3(get, set)]
    pub constitutional_validated: bool,
    #[pyo3(get, set)]
    pub created_at: String,
    #[pyo3(get, set)]
    pub updated_at: String,
    #[pyo3(get, set)]
    pub expires_at: Option<String>,
    #[pyo3(get, set)]
    pub impact_score: Option<f32>,
    #[pyo3(get, set)]
    pub performance_metrics: HashMap<String, String>,
}

#[pymethods]
impl AgentMessage {
    #[new]
    fn new() -> Self {
        let now = Utc::now().to_rfc3339();
        Self {
            message_id: Uuid::new_v4().to_string(),
            conversation_id: Uuid::new_v4().to_string(),
            content: HashMap::new(),
            payload: HashMap::new(),
            from_agent: String::new(),
            to_agent: String::new(),
            sender_id: String::new(),
            message_type: MessageType::Command,
            routing: None,
            headers: HashMap::new(),
            tenant_id: String::new(),
            security_context: HashMap::new(),
            priority: MessagePriority::Normal,
            status: MessageStatus::Pending,
            constitutional_hash: CONSTITUTIONAL_HASH.to_string(),
            constitutional_validated: false,
            created_at: now.clone(),
            updated_at: now,
            expires_at: None,
            impact_score: None,
            performance_metrics: HashMap::new(),
        }
    }

    fn to_dict(&self) -> PyResult<String> {
        serde_json::to_string(self).map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }

    #[staticmethod]
    fn from_dict(json_str: &str) -> PyResult<Self> {
        serde_json::from_str(json_str).map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }
}

/// Validation result structure
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct ValidationResult {
    #[pyo3(get, set)]
    pub is_valid: bool,
    #[pyo3(get, set)]
    pub errors: Vec<String>,
    #[pyo3(get, set)]
    pub warnings: Vec<String>,
    #[pyo3(get, set)]
    pub metadata: HashMap<String, String>,
    #[pyo3(get, set)]
    pub decision: String,
    #[pyo3(get, set)]
    pub constitutional_hash: String,
}

#[pymethods]
impl ValidationResult {
    #[new]
    fn new() -> Self {
        Self {
            is_valid: true,
            errors: Vec::new(),
            warnings: Vec::new(),
            metadata: HashMap::new(),
            decision: "ALLOW".to_string(),
            constitutional_hash: CONSTITUTIONAL_HASH.to_string(),
        }
    }

    fn add_error(&mut self, error: String) {
        self.errors.push(error);
        self.is_valid = false;
        self.decision = "DENY".to_string();
    }

    fn add_warning(&mut self, warning: String) {
        self.warnings.push(warning);
    }

    fn merge(&mut self, other: &ValidationResult) {
        self.errors.extend(other.errors.clone());
        self.warnings.extend(other.warnings.clone());
        if !other.is_valid {
            self.is_valid = false;
            self.decision = "DENY".to_string();
        }
    }
}

type AsyncHandler = Arc<dyn Fn(AgentMessage) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), Box<dyn std::error::Error + Send + Sync>>> + Send>> + Send + Sync>;

#[pyclass]
pub struct MessageProcessor {
    constitutional_hash: String,
    handlers: Arc<DashMap<MessageType, Vec<AsyncHandler>>>,
    processed_count: Arc<ParkingRwLock<u64>>,
    metrics: Arc<ParkingRwLock<HashMap<String, u64>>>,
    impact_scorer: Arc<ImpactScorer>,
    adaptive_router: Arc<AdaptiveRouter>,
    opa_client: Arc<ParkingRwLock<Option<OpaClient>>>,
    audit_client: Arc<ParkingRwLock<Option<AuditClient>>>,
}

#[pymethods]
impl MessageProcessor {
    #[new]
    fn new() -> Self {
        Self {
            constitutional_hash: CONSTITUTIONAL_HASH.to_string(),
            handlers: Arc::new(DashMap::new()),
            processed_count: Arc::new(ParkingRwLock::new(0)),
            metrics: Arc::new(ParkingRwLock::new(HashMap::new())),
            impact_scorer: Arc::new(ImpactScorer::new(None, None)),
            adaptive_router: Arc::new(AdaptiveRouter::new(0.8)),
            opa_client: Arc::new(ParkingRwLock::new(None)),
            audit_client: Arc::new(ParkingRwLock::new(None)),
        }
    }

    fn register_handler(&self, message_type: MessageType, handler: PyObject) -> PyResult<()> {
        let async_handler = Arc::new(move |msg: AgentMessage| {
            let handler = handler.clone();
            Box::pin(async move {
                Python::with_gil(|py| {
                    let _ = handler.call1(py, (msg,))?;
                    Ok(())
                })
            }) as std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), Box<dyn std::error::Error + Send + Sync>>> + Send>>
        });

        self.handlers.entry(message_type).or_insert_with(Vec::new).push(async_handler);
        Ok(())
    }

    #[pyo3(signature = (message))]
    fn process<'py>(&self, py: Python<'py>, message: AgentMessage) -> PyResult<&'py PyAny> {
        let processor = self.clone_internal();
        pyo3_asyncio::tokio::future_into_py(py, async move {
            processor.process_async(message).await
        })
    }

    #[getter]
    fn processed_count(&self) -> u64 {
        *self.processed_count.read()
    }

    fn get_metrics(&self) -> HashMap<String, u64> {
        self.metrics.read().clone()
    }

    fn enable_opa<'py>(&self, py: Python<'py>, endpoint: String) -> PyResult<&'py PyAny> {
        let opa_client = self.opa_client.clone();
        pyo3_asyncio::tokio::future_into_py(py, async move {
            *opa_client.write() = Some(OpaClient::new(endpoint));
            Ok(())
        })
    }

    fn enable_audit<'py>(&self, py: Python<'py>, service_url: String) -> PyResult<&'py PyAny> {
        let audit_client = self.audit_client.clone();
        pyo3_asyncio::tokio::future_into_py(py, async move {
            *audit_client.write() = Some(AuditClient::new(service_url));
            Ok(())
        })
    }

    fn set_impact_threshold(&self, threshold: f32) {
        self.adaptive_router.impact_threshold.store(threshold, std::sync::atomic::Ordering::Relaxed);
    }

    fn set_opa_fail_closed(&self, fail_closed: bool) {
        let mut opa_lock = self.opa_client.write();
        if let Some(opa) = opa_lock.as_ref() {
            let new_opa = opa.clone().with_fail_closed(fail_closed);
            *opa_lock = Some(new_opa);
        }
    }

    fn opa_health_check<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let opa_client = self.opa_client.clone();
        pyo3_asyncio::tokio::future_into_py(py, async move {
            let opa = opa_client.read().clone();
            if let Some(opa) = opa {
                let health = opa.health_check().await;
                Ok(health.to_string())
            } else {
                Ok("{\"status\": \"disabled\"}".to_string())
            }
        })
    }
}

impl MessageProcessor {
    fn clone_internal(&self) -> Self {
        Self {
            constitutional_hash: self.constitutional_hash.clone(),
            handlers: self.handlers.clone(),
            processed_count: self.processed_count.clone(),
            metrics: self.metrics.clone(),
            impact_scorer: self.impact_scorer.clone(),
            adaptive_router: self.adaptive_router.clone(),
            opa_client: self.opa_client.clone(),
            audit_client: self.audit_client.clone(),
        }
    }

    async fn process_async(&self, mut message: AgentMessage) -> PyResult<ValidationResult> {
        // 1. Prompt Injection Detection (Pre-flight)
        for value in message.content.values() {
            if let Some(injection_result) = detect_prompt_injection(value) {
                let audit = self.audit_client.read().clone();
                if let Some(audit) = audit {
                    let _ = audit.log_decision(&message, &injection_result).await;
                }
                return Ok(injection_result);
            }
        }

        // 2. Constitutional & Basic Validation
        let mut validation_result = self.validate_message_parallel(&message).await?;
        if !validation_result.is_valid {
            return Ok(validation_result);
        }

        // 3. Impact Scoring
        let impact_score = self.impact_scorer.calculate_impact_score(&message);
        message.impact_score = Some(impact_score);

        // 4. Dual-Path Routing
        let routing_decision = self.adaptive_router.route(&message);
        validation_result.metadata.insert("lane".to_string(), routing_decision.lane.clone());
        validation_result.metadata.insert("impact_score".to_string(), impact_score.to_string());

        if routing_decision.requires_deliberation {
            // Deliberation Path
            message.status = MessageStatus::Deliberation;
            // In a full implementation, we would enqueue message here
        } else {
            // Fast Path with OPA
            let opa = self.opa_client.read().clone();
            if let Some(opa) = opa {
                let opa_result = opa.validate(&message).await.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
                validation_result.merge(&opa_result);
            }
        }

        if !validation_result.is_valid {
            let audit = self.audit_client.read().clone();
            if let Some(audit) = audit {
                let _ = audit.log_decision(&message, &validation_result).await;
            }
            return Ok(validation_result);
        }

        // 5. Audit Reporting
        let audit = self.audit_client.read().clone();
        if let Some(audit) = audit {
            let _ = audit.log_decision(&message, &validation_result).await;
        }

        // 6. Handler Execution
        message.status = MessageStatus::Processing;
        message.updated_at = Utc::now().to_rfc3339();

        let handlers = self.handlers.get(&message.message_type);
        if let Some(handlers) = handlers {
            let handler_futures: Vec<_> = handlers.iter().map(|handler| {
                let msg = message.clone();
                async move { handler(msg).await }
            }).collect();

            let results = futures::future::join_all(handler_futures).await;
            for result in results {
                if let Err(e) = result {
                    message.status = MessageStatus::Failed;
                    let mut err_result = ValidationResult::new();
                    err_result.add_error(e.to_string());
                    return Ok(err_result);
                }
            }
        }

        message.status = MessageStatus::Delivered;
        *self.processed_count.write() += 1;

        let mut metrics = self.metrics.write();
        *metrics.entry("messages_processed".to_string()).or_insert(0) += 1;

        Ok(validation_result)
    }

    async fn validate_message_parallel(&self, message: &AgentMessage) -> PyResult<ValidationResult> {
        let msg = message.clone();
        tokio::task::spawn_blocking(move || {
            let (result1, result2) = rayon::join(
                || Self::validate_constitutional_hash(&msg),
                || Self::validate_message_structure(&msg)
            );

            let mut final_result = ValidationResult::new();
            final_result.merge(&result1);
            final_result.merge(&result2);
            final_result
        }).await.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn validate_constitutional_hash(message: &AgentMessage) -> ValidationResult {
        let mut result = ValidationResult::new();
        if message.constitutional_hash != CONSTITUTIONAL_HASH {
            result.add_error(format!("Constitutional hash mismatch: expected {}, got {}", CONSTITUTIONAL_HASH, message.constitutional_hash));
        }
        result
    }

    fn validate_message_structure(message: &AgentMessage) -> ValidationResult {
        let mut result = ValidationResult::new();
        if message.sender_id.is_empty() {
            result.add_error("Required field sender_id is empty".to_string());
        }
        result
    }
}

#[pymodule]
fn enhanced_agent_bus_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<MessageType>()?;
    m.add_class::<MessagePriority>()?;
    m.add_class::<MessageStatus>()?;
    m.add_class::<RoutingContext>()?;
    m.add_class::<AgentMessage>()?;
    m.add_class::<ValidationResult>()?;
    m.add_class::<MessageProcessor>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
