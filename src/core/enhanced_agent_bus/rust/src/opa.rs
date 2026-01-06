use serde::{Deserialize, Serialize};
use crate::{AgentMessage, ValidationResult};
use std::time::Duration;
use moka::future::Cache;
use reqwest::Client;
use tracing::{error, warn};

#[derive(Debug, Serialize, Deserialize)]
pub struct OpaInput<T> {
    pub input: T,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ConstitutionalInput {
    pub message: AgentMessage,
    pub constitutional_hash: String,
    pub timestamp: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct OpaResponse {
    pub result: Option<serde_json::Value>,
}

#[derive(Debug, Clone)]
pub struct OpaClient {
    endpoint: String,
    client: Client,
    cache: Cache<String, ValidationResult>,
    fail_closed: bool,
}

impl OpaClient {
    pub fn new(endpoint: String) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(5))
            .pool_idle_timeout(Duration::from_secs(90))
            .build()
            .unwrap_or_default();

        let cache = Cache::builder()
            .max_capacity(10000)
            .time_to_live(Duration::from_secs(300)) // 5 minutes
            .build();

        Self {
            endpoint: endpoint.trim_end_matches('/').to_string(),
            client,
            cache,
            fail_closed: true,
        }
    }

    pub fn with_fail_closed(mut self, fail_closed: bool) -> Self {
        self.fail_closed = fail_closed;
        self
    }

    pub async fn validate_constitutional(&self, message: &AgentMessage) -> Result<ValidationResult, Box<dyn std::error::Error + Send + Sync>> {
        let cache_key = format!("constitutional:{}:{}", message.message_id, message.constitutional_hash);

        if let Some(cached) = self.cache.get(&cache_key).await {
            return Ok(cached);
        }

        let input = ConstitutionalInput {
            message: message.clone(),
            constitutional_hash: message.constitutional_hash.clone(),
            timestamp: chrono::Utc::now().to_rfc3339(),
        };

        let result = self.evaluate_policy("acgs/constitutional/validate", &input).await?;

        self.cache.insert(cache_key, result.clone()).await;
        Ok(result)
    }

    async fn evaluate_policy<T: Serialize>(&self, policy_path: &str, input: &T) -> Result<ValidationResult, Box<dyn std::error::Error + Send + Sync>> {
        let url = format!("{}/v1/data/{}", self.endpoint, policy_path);

        let opa_input = OpaInput { input };

        let response = match self.client.post(&url)
            .json(&opa_input)
            .send()
            .await {
                Ok(resp) => resp,
                Err(e) => {
                    error!("OPA connection error: {}", e);
                    return Ok(self.handle_fallback(format!("OPA connection error: {}", e)));
                }
            };

        if !response.status().is_success() {
            let status = response.status();
            error!("OPA returned error status: {}", status);
            return Ok(self.handle_fallback(format!("OPA error status: {}", status)));
        }

        let opa_resp: OpaResponse = match response.json().await {
            Ok(data) => data,
            Err(e) => {
                error!("Failed to parse OPA response: {}", e);
                return Ok(self.handle_fallback(format!("Failed to parse OPA response: {}", e)));
            }
        };

        let mut validation_result = ValidationResult::new();

        match opa_resp.result {
            Some(serde_json::Value::Bool(allowed)) => {
                validation_result.is_valid = allowed;
                if !allowed {
                    validation_result.add_error("Policy denied by OPA".to_string());
                }
            }
            Some(serde_json::Value::Object(obj)) => {
                let allowed = obj.get("allow").and_then(|v| v.as_bool()).unwrap_or(false);
                validation_result.is_valid = allowed;
                if !allowed {
                    let reason = obj.get("reason").and_then(|v| v.as_str()).unwrap_or("Policy denied by OPA");
                    validation_result.add_error(reason.to_string());
                }
                if let Some(metadata) = obj.get("metadata").and_then(|v| v.as_object()) {
                    for (k, v) in metadata {
                        validation_result.metadata.insert(k.clone(), v.to_string());
                    }
                }
            }
            _ => {
                warn!("Unexpected OPA result format for policy {}", policy_path);
                return Ok(self.handle_fallback("Unexpected OPA result format".to_string()));
            }
        }

        Ok(validation_result)
    }

    fn handle_fallback(&self, error_msg: String) -> ValidationResult {
        let mut result = ValidationResult::new();
        if self.fail_closed {
            result.is_valid = false;
            result.decision = "DENY".to_string();
            result.add_error(format!("OPA Failure (Fail-Closed): {}", error_msg));
        } else {
            result.is_valid = true;
            result.decision = "ALLOW".to_string();
            result.add_warning(format!("OPA Failure (Fail-Open): {}", error_msg));
        }
        result
    }

    pub async fn validate(&self, message: &AgentMessage) -> Result<ValidationResult, Box<dyn std::error::Error + Send + Sync>> {
        // Default validation path
        self.validate_constitutional(message).await
    }

    pub async fn health_check(&self) -> serde_json::Value {
        let url = format!("{}/health", self.endpoint);
        match self.client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => {
                serde_json::json!({"status": "healthy", "mode": "http"})
            }
            Ok(resp) => {
                serde_json::json!({"status": "unhealthy", "code": resp.status().as_u16()})
            }
            Err(e) => {
                serde_json::json!({"status": "unhealthy", "error": e.to_string()})
            }
        }
    }
}
