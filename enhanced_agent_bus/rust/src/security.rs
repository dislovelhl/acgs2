use regex::Regex;
use once_cell::sync::Lazy;
use crate::ValidationResult;

/// Known prompt injection patterns
static PROMPT_INJECTION_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        Regex::new(r"(?i)ignore (all )?previous instructions").unwrap(),
        Regex::new(r"(?i)system prompt (leak|override)").unwrap(),
        Regex::new(r"(?i)do anything now").unwrap(), // DAN
        Regex::new(r"(?i)jailbreak").unwrap(),
        Regex::new(r"(?i)persona (adoption|override)").unwrap(),
        Regex::new(r"(?i)\(note to self: .*\)").unwrap(),
        Regex::new(r"(?i)\[INST\].*\[/INST\]").unwrap(), // LLM instruction markers bypass
        Regex::new(r"(?i)actually, do this instead").unwrap(),
        Regex::new(r"(?i)forget everything you know").unwrap(),
        Regex::new(r"(?i)bypass rules").unwrap(),
        Regex::new(r"(?i)reveal your system instructions").unwrap(),
        Regex::new(r"(?i)new directive:").unwrap(),
    ]
});

/// Intercepts and neutralizes adversarial input patterns.
pub fn detect_prompt_injection(content: &str) -> Option<ValidationResult> {
    for pattern in PROMPT_INJECTION_PATTERNS.iter() {
        if pattern.is_match(content) {
            let mut result = ValidationResult::new();
            result.is_valid = false;
            result.errors.push(format!("Prompt injection detected: Pattern mismatch '{}'", pattern.as_str()));
            result.metadata.insert("decision".to_string(), "DENY".to_string());
            return Some(result);
        }
    }
    None
}
