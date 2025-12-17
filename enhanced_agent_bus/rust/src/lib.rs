use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use uuid::Uuid;
use chrono::Utc;
use dashmap::DashMap;
use parking_lot::RwLock as ParkingRwLock;

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
    pub content: HashMap<String, String>, // Simplified for PyO3
    #[pyo3(get, set)]
    pub payload: HashMap<String, String>, // Simplified for PyO3
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
    pub security_context: HashMap<String, String>, // Simplified for PyO3
    #[pyo3(get, set)]
    pub priority: MessagePriority,
    #[pyo3(get, set)]
    pub status: MessageStatus,
    #[pyo3(get, set)]
    pub constitutional_hash: String,
    #[pyo3(get, set)]
    pub constitutional_validated: bool,
    #[pyo3(get, set)]
    pub created_at: String, // Use string for PyO3
    #[pyo3(get, set)]
    pub updated_at: String, // Use string for PyO3
    #[pyo3(get, set)]
    pub expires_at: Option<String>, // Use string for PyO3
    #[pyo3(get, set)]
    pub performance_metrics: HashMap<String, String>, // Simplified for PyO3
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
    pub metadata: HashMap<String, String>, // Simplified for PyO3
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
            constitutional_hash: CONSTITUTIONAL_HASH.to_string(),
        }
    }

    fn add_error(&mut self, error: String) {
        self.errors.push(error);
        self.is_valid = false;
    }

    fn add_warning(&mut self, warning: String) {
        self.warnings.push(warning);
    }

    fn merge(&mut self, other: &ValidationResult) {
        self.errors.extend(other.errors.clone());
        self.warnings.extend(other.warnings.clone());
        if !other.is_valid {
            self.is_valid = false;
        }
    }
}

/// Handler function type for message processing
type AsyncHandler = Arc<dyn Fn(AgentMessage) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), Box<dyn std::error::Error + Send + Sync>>> + Send>> + Send + Sync>;

/// High-performance message processor with async support
#[derive(Clone)]
#[pyclass]
pub struct MessageProcessor {
    constitutional_hash: String,
    handlers: Arc<DashMap<MessageType, Vec<AsyncHandler>>>,
    processed_count: Arc<ParkingRwLock<u64>>,
    metrics: Arc<ParkingRwLock<HashMap<String, u64>>>,
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
        }
    }

    /// Register a synchronous handler (wrapped for async compatibility)
    fn register_handler(&self, message_type: MessageType, handler: PyObject) -> PyResult<()> {
        let async_handler = Arc::new(move |msg: AgentMessage| {
            let handler = handler.clone();
            Box::pin(async move {
                Python::with_gil(|py| {
                    let result = handler.call1(py, (msg,))?;
                    Ok(())
                })
            }) as std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), Box<dyn std::error::Error + Send + Sync>>> + Send>>
        });

        self.handlers.entry(message_type).or_insert_with(Vec::new).push(async_handler);
        Ok(())
    }

    /// Process a message asynchronously with parallel validation
    #[pyo3(signature = (message))]
    fn process<'py>(&self, py: Python<'py>, message: AgentMessage) -> PyResult<&'py PyAny> {
        let processor = self.clone();
        pyo3_asyncio::tokio::future_into_py(py, async move {
            processor.process_async(message).await
        })
    }

    /// Get processed message count
    #[getter]
    fn processed_count(&self) -> u64 {
        *self.processed_count.read()
    }

    /// Get metrics
    fn get_metrics(&self) -> HashMap<String, u64> {
        self.metrics.read().clone()
    }
}

impl MessageProcessor {
    /// Internal async processing method
    async fn process_async(&self, mut message: AgentMessage) -> PyResult<ValidationResult> {
        // Parallel validation using Rayon
        let validation_result = self.validate_message_parallel(&message).await?;

        if !validation_result.is_valid {
            return Ok(validation_result);
        }

        // Update message status
        message.status = MessageStatus::Processing;
        message.updated_at = Utc::now().to_rfc3339();

        // Process handlers concurrently
        let handlers = self.handlers.get(&message.message_type);
        if let Some(handlers) = handlers {
            let handler_futures: Vec<_> = handlers.iter().map(|handler| {
                let msg = message.clone();
                async move {
                    handler(msg).await
                }
            }).collect();

            // Execute all handlers concurrently
            let results = futures::future::join_all(handler_futures).await;

            // Check for errors
            for result in results {
                if let Err(e) = result {
                    message.status = MessageStatus::Failed;
                    return Ok(ValidationResult {
                        is_valid: false,
                        errors: vec![e.to_string()],
                        warnings: vec![],
                        metadata: HashMap::new(),
                        constitutional_hash: self.constitutional_hash.clone(),
                    });
                }
            }
        }

        // Success
        message.status = MessageStatus::Delivered;
        *self.processed_count.write() += 1;

        // Update metrics
        let mut metrics = self.metrics.write();
        *metrics.entry("messages_processed".to_string()).or_insert(0) += 1;

        Ok(ValidationResult {
            is_valid: true,
            errors: vec![],
            warnings: vec![],
            metadata: HashMap::new(),
            constitutional_hash: self.constitutional_hash.clone(),
        })
    }

    /// Parallel message validation using Rayon
    async fn validate_message_parallel(&self, message: &AgentMessage) -> PyResult<ValidationResult> {
        let message = message.clone();
        tokio::task::spawn_blocking(move || {
            let (result1, result2) = rayon::join(
                || Self::validate_constitutional_hash(&message),
                || Self::validate_message_structure(&message)
            );

            let mut final_result = ValidationResult::new();
            final_result.merge(&result1);
            final_result.merge(&result2);
            final_result
        }).await.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    /// Validate constitutional hash
    fn validate_constitutional_hash(message: &AgentMessage) -> ValidationResult {
        let mut result = ValidationResult::new();
        if message.constitutional_hash != CONSTITUTIONAL_HASH {
            result.add_error(format!("Constitutional hash mismatch: expected {}, got {}", CONSTITUTIONAL_HASH, message.constitutional_hash));
        }
        result
    }

    /// Validate message structure
    fn validate_message_structure(message: &AgentMessage) -> ValidationResult {
        let mut result = ValidationResult::new();
        if message.sender_id.is_empty() {
            result.add_error("Required field sender_id is empty".to_string());
        }
        if message.routing.is_none() {
            result.add_warning("Message lacks routing configuration".to_string());
        }
        result
    }
}

/// Python module initialization
#[pymodule]
fn enhanced_agent_bus(_py: Python, m: &PyModule) -> PyResult<()> {
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
