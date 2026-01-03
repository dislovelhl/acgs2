//! ACGS2 Performance-Critical Hot Path Functions
//!
//! This module provides Rust implementations of CPU-intensive operations
//! that are called frequently in the ACGS2 governance system. These functions
//! are exposed to Python via PyO3 for seamless integration.
//!
//! Target: >5x performance improvement over equivalent Python implementations

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;

/// Generate a fast hash for cache key generation.
/// Uses FNV-1a algorithm which is optimized for short strings like cache keys.
///
/// # Arguments
/// * `key` - The string to hash
///
/// # Returns
/// A 64-bit hash value as an unsigned integer
#[pyfunction]
fn fast_hash(key: &str) -> u64 {
    // FNV-1a hash - excellent for short strings like cache keys
    const FNV_OFFSET_BASIS: u64 = 14695981039346656037;
    const FNV_PRIME: u64 = 1099511628211;

    let mut hash = FNV_OFFSET_BASIS;
    for byte in key.bytes() {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(FNV_PRIME);
    }
    hash
}

/// Generate a composite cache key from multiple components.
/// Efficiently combines service name, endpoint, and request parameters into a single hash.
///
/// # Arguments
/// * `service` - Service name
/// * `endpoint` - API endpoint path
/// * `params` - Request parameters as key-value pairs
///
/// # Returns
/// A cache key string in format "acgs2:{hash}"
#[pyfunction]
fn generate_cache_key(service: &str, endpoint: &str, params: Vec<(&str, &str)>) -> String {
    let mut combined = String::with_capacity(256);
    combined.push_str(service);
    combined.push(':');
    combined.push_str(endpoint);

    // Sort params for consistent hashing regardless of order
    let mut sorted_params = params;
    sorted_params.sort_by(|a, b| a.0.cmp(b.0));

    for (key, value) in sorted_params {
        combined.push(':');
        combined.push_str(key);
        combined.push('=');
        combined.push_str(value);
    }

    let hash = fast_hash(&combined);
    format!("acgs2:{:x}", hash)
}

/// Validate a batch of strings against a regex-like pattern.
/// This is much faster than Python's re.match() for simple patterns.
///
/// # Arguments
/// * `strings` - List of strings to validate
/// * `pattern` - Pattern to match (supports: alphanumeric, email, uuid)
///
/// # Returns
/// Vector of validation results (true/false for each string)
#[pyfunction]
fn batch_validate_strings(strings: Vec<&str>, pattern: &str) -> Vec<bool> {
    strings
        .iter()
        .map(|s| match pattern {
            "alphanumeric" => s.chars().all(|c| c.is_alphanumeric()),
            "email" => validate_email(s),
            "uuid" => validate_uuid(s),
            "non_empty" => !s.is_empty(),
            "identifier" => validate_identifier(s),
            _ => false,
        })
        .collect()
}

/// Fast email validation (basic format check)
fn validate_email(email: &str) -> bool {
    if email.len() < 3 || email.len() > 254 {
        return false;
    }

    let at_pos = match email.find('@') {
        Some(pos) => pos,
        None => return false,
    };

    if at_pos == 0 || at_pos == email.len() - 1 {
        return false;
    }

    let domain = &email[at_pos + 1..];
    domain.contains('.') && !domain.starts_with('.') && !domain.ends_with('.')
}

/// Fast UUID validation (format check for UUID v4)
fn validate_uuid(uuid: &str) -> bool {
    if uuid.len() != 36 {
        return false;
    }

    let parts: Vec<&str> = uuid.split('-').collect();
    if parts.len() != 5 {
        return false;
    }

    let expected_lens = [8, 4, 4, 4, 12];
    for (part, &expected_len) in parts.iter().zip(expected_lens.iter()) {
        if part.len() != expected_len || !part.chars().all(|c| c.is_ascii_hexdigit()) {
            return false;
        }
    }
    true
}

/// Validate identifier (alphanumeric + underscore, starts with letter)
fn validate_identifier(s: &str) -> bool {
    if s.is_empty() {
        return false;
    }
    let first = s.chars().next().unwrap();
    if !first.is_alphabetic() && first != '_' {
        return false;
    }
    s.chars().all(|c| c.is_alphanumeric() || c == '_')
}

/// Aggregate numeric data with multiple operations in a single pass.
/// Returns sum, mean, min, max, and count in one efficient operation.
///
/// # Arguments
/// * `values` - List of floating point numbers
///
/// # Returns
/// Tuple of (sum, mean, min, max, count)
#[pyfunction]
fn aggregate_stats(values: Vec<f64>) -> (f64, f64, f64, f64, usize) {
    if values.is_empty() {
        return (0.0, 0.0, 0.0, 0.0, 0);
    }

    let count = values.len();
    let mut sum = 0.0;
    let mut min = f64::MAX;
    let mut max = f64::MIN;

    for &v in &values {
        sum += v;
        if v < min {
            min = v;
        }
        if v > max {
            max = v;
        }
    }

    let mean = sum / count as f64;
    (sum, mean, min, max, count)
}

/// Batch compute percentiles for latency data.
/// Used for P50, P90, P95, P99 latency calculations.
///
/// # Arguments
/// * `values` - List of latency values in milliseconds
/// * `percentiles` - List of percentiles to calculate (e.g., [50.0, 90.0, 95.0, 99.0])
///
/// # Returns
/// Vector of percentile values
#[pyfunction]
fn compute_percentiles(mut values: Vec<f64>, percentiles: Vec<f64>) -> Vec<f64> {
    if values.is_empty() {
        return vec![0.0; percentiles.len()];
    }

    values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    percentiles
        .iter()
        .map(|&p| {
            let index = (p / 100.0 * (values.len() - 1) as f64).round() as usize;
            values[index.min(values.len() - 1)]
        })
        .collect()
}

/// Filter and transform a batch of dictionaries based on field criteria.
/// This is a hot path for filtering API responses and policy evaluations.
///
/// # Arguments
/// * `py` - Python GIL handle
/// * `items` - List of dictionaries to filter
/// * `field` - Field name to check
/// * `allowed_values` - Set of allowed values for the field
///
/// # Returns
/// Filtered list of dictionaries
#[pyfunction]
fn batch_filter_dicts<'py>(
    py: Python<'py>,
    items: Vec<Bound<'py, PyDict>>,
    field: &str,
    allowed_values: Vec<String>,
) -> PyResult<Bound<'py, PyList>> {
    let allowed_set: std::collections::HashSet<String> = allowed_values.into_iter().collect();
    let result = PyList::empty(py);

    for item in items {
        if let Ok(Some(value)) = item.get_item(field) {
            if let Ok(s) = value.extract::<String>() {
                if allowed_set.contains(&s) {
                    result.append(item)?;
                }
            }
        }
    }

    Ok(result)
}

/// Merge multiple dictionaries efficiently, with later values overwriting earlier ones.
/// Used for combining configuration and policy data.
///
/// # Arguments
/// * `dicts` - List of dictionaries to merge
///
/// # Returns
/// Merged dictionary
#[pyfunction]
fn merge_dicts<'py>(py: Python<'py>, dicts: Vec<Bound<'py, PyDict>>) -> PyResult<Bound<'py, PyDict>> {
    let result = PyDict::new(py);

    for dict in dicts {
        for (key, value) in dict.iter() {
            result.set_item(key, value)?;
        }
    }

    Ok(result)
}

/// Parse and extract values from a list of JSON-like strings.
/// Optimized for simple key extraction without full JSON parsing.
///
/// # Arguments
/// * `json_strings` - List of JSON strings
/// * `key` - Key to extract
///
/// # Returns
/// Vector of extracted values (None if key not found)
#[pyfunction]
fn batch_extract_json_field(json_strings: Vec<&str>, key: &str) -> Vec<Option<String>> {
    let search_pattern = format!("\"{}\":", key);

    json_strings
        .iter()
        .map(|s| {
            if let Some(start) = s.find(&search_pattern) {
                let value_start = start + search_pattern.len();
                let rest = &s[value_start..];
                let rest = rest.trim_start();

                if rest.starts_with('"') {
                    // String value
                    if let Some(end) = rest[1..].find('"') {
                        return Some(rest[1..=end].to_string());
                    }
                } else {
                    // Numeric or other value
                    let end = rest
                        .find(|c: char| c == ',' || c == '}' || c.is_whitespace())
                        .unwrap_or(rest.len());
                    return Some(rest[..end].to_string());
                }
            }
            None
        })
        .collect()
}

/// Normalize a batch of strings (lowercase, trim, remove extra whitespace).
/// Common preprocessing for search and comparison operations.
///
/// # Arguments
/// * `strings` - List of strings to normalize
///
/// # Returns
/// Normalized strings
#[pyfunction]
fn batch_normalize_strings(strings: Vec<&str>) -> Vec<String> {
    strings
        .iter()
        .map(|s| {
            s.trim()
                .to_lowercase()
                .split_whitespace()
                .collect::<Vec<&str>>()
                .join(" ")
        })
        .collect()
}

/// Compute similarity scores between a query and a list of targets.
/// Uses Jaccard similarity on character n-grams for fuzzy matching.
///
/// # Arguments
/// * `query` - The query string
/// * `targets` - List of target strings to compare against
/// * `n` - N-gram size (default 2 for bigrams)
///
/// # Returns
/// Vector of similarity scores (0.0 to 1.0)
#[pyfunction]
#[pyo3(signature = (query, targets, n = 2))]
fn batch_similarity_scores(query: &str, targets: Vec<&str>, n: usize) -> Vec<f64> {
    let query_ngrams = get_ngrams(query, n);

    targets
        .iter()
        .map(|target| {
            let target_ngrams = get_ngrams(target, n);
            jaccard_similarity(&query_ngrams, &target_ngrams)
        })
        .collect()
}

/// Extract n-grams from a string
fn get_ngrams(s: &str, n: usize) -> std::collections::HashSet<String> {
    let chars: Vec<char> = s.to_lowercase().chars().collect();
    if chars.len() < n {
        return std::collections::HashSet::new();
    }

    chars.windows(n).map(|w| w.iter().collect()).collect()
}

/// Compute Jaccard similarity between two sets
fn jaccard_similarity(
    set1: &std::collections::HashSet<String>,
    set2: &std::collections::HashSet<String>,
) -> f64 {
    if set1.is_empty() && set2.is_empty() {
        return 1.0;
    }
    if set1.is_empty() || set2.is_empty() {
        return 0.0;
    }

    let intersection = set1.intersection(set2).count();
    let union = set1.union(set2).count();

    intersection as f64 / union as f64
}

/// Count occurrences of each unique value in a list.
/// Much faster than Python's collections.Counter for large datasets.
///
/// # Arguments
/// * `values` - List of strings to count
///
/// # Returns
/// HashMap of value -> count
#[pyfunction]
fn count_values(values: Vec<&str>) -> HashMap<String, usize> {
    let mut counts: HashMap<String, usize> = HashMap::new();
    for value in values {
        *counts.entry(value.to_string()).or_insert(0) += 1;
    }
    counts
}

/// Deduplicate a list while preserving order.
/// Returns only the first occurrence of each value.
///
/// # Arguments
/// * `values` - List of strings to deduplicate
///
/// # Returns
/// Deduplicated list
#[pyfunction]
fn deduplicate_ordered(values: Vec<&str>) -> Vec<String> {
    let mut seen = std::collections::HashSet::new();
    values
        .into_iter()
        .filter(|v| seen.insert(*v))
        .map(|v| v.to_string())
        .collect()
}

/// Check if any value in the list matches any of the patterns.
/// Used for batch permission/policy checking.
///
/// # Arguments
/// * `values` - List of values to check
/// * `patterns` - List of patterns (supports * as wildcard)
///
/// # Returns
/// True if any value matches any pattern
#[pyfunction]
fn batch_match_patterns(values: Vec<&str>, patterns: Vec<&str>) -> bool {
    for value in &values {
        for pattern in &patterns {
            if match_wildcard_pattern(value, pattern) {
                return true;
            }
        }
    }
    false
}

/// Simple wildcard pattern matching (supports * as any characters)
fn match_wildcard_pattern(value: &str, pattern: &str) -> bool {
    if pattern == "*" {
        return true;
    }

    if !pattern.contains('*') {
        return value == pattern;
    }

    let parts: Vec<&str> = pattern.split('*').collect();

    if parts.len() == 2 {
        // Single wildcard
        let starts_with = parts[0].is_empty() || value.starts_with(parts[0]);
        let ends_with = parts[1].is_empty() || value.ends_with(parts[1]);
        return starts_with && ends_with;
    }

    // Multiple wildcards - simple recursive approach
    let mut remaining = value;
    for (i, part) in parts.iter().enumerate() {
        if part.is_empty() {
            continue;
        }
        if i == 0 {
            if !remaining.starts_with(part) {
                return false;
            }
            remaining = &remaining[part.len()..];
        } else if i == parts.len() - 1 {
            if !remaining.ends_with(part) {
                return false;
            }
        } else if let Some(pos) = remaining.find(part) {
            remaining = &remaining[pos + part.len()..];
        } else {
            return false;
        }
    }
    true
}

/// Compute a simple checksum for data integrity verification.
/// Uses a fast additive checksum suitable for quick validation.
///
/// # Arguments
/// * `data` - The data bytes as a string
///
/// # Returns
/// 32-bit checksum value
#[pyfunction]
fn fast_checksum(data: &str) -> u32 {
    let mut sum: u32 = 0;
    for (i, byte) in data.bytes().enumerate() {
        sum = sum.wrapping_add((byte as u32).wrapping_mul((i as u32).wrapping_add(1)));
    }
    sum
}

/// Python module definition
#[pymodule]
fn acgs2_perf(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fast_hash, m)?)?;
    m.add_function(wrap_pyfunction!(generate_cache_key, m)?)?;
    m.add_function(wrap_pyfunction!(batch_validate_strings, m)?)?;
    m.add_function(wrap_pyfunction!(aggregate_stats, m)?)?;
    m.add_function(wrap_pyfunction!(compute_percentiles, m)?)?;
    m.add_function(wrap_pyfunction!(batch_filter_dicts, m)?)?;
    m.add_function(wrap_pyfunction!(merge_dicts, m)?)?;
    m.add_function(wrap_pyfunction!(batch_extract_json_field, m)?)?;
    m.add_function(wrap_pyfunction!(batch_normalize_strings, m)?)?;
    m.add_function(wrap_pyfunction!(batch_similarity_scores, m)?)?;
    m.add_function(wrap_pyfunction!(count_values, m)?)?;
    m.add_function(wrap_pyfunction!(deduplicate_ordered, m)?)?;
    m.add_function(wrap_pyfunction!(batch_match_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(fast_checksum, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fast_hash() {
        let hash1 = fast_hash("test");
        let hash2 = fast_hash("test");
        let hash3 = fast_hash("different");

        assert_eq!(hash1, hash2);
        assert_ne!(hash1, hash3);
    }

    #[test]
    fn test_generate_cache_key() {
        let key = generate_cache_key("service", "/api/test", vec![("a", "1"), ("b", "2")]);
        assert!(key.starts_with("acgs2:"));

        // Same params in different order should produce same key
        let key2 = generate_cache_key("service", "/api/test", vec![("b", "2"), ("a", "1")]);
        assert_eq!(key, key2);
    }

    #[test]
    fn test_validate_email() {
        assert!(validate_email("test@example.com"));
        assert!(validate_email("user.name@domain.co.uk"));
        assert!(!validate_email("invalid"));
        assert!(!validate_email("@domain.com"));
        assert!(!validate_email("test@"));
    }

    #[test]
    fn test_validate_uuid() {
        assert!(validate_uuid("550e8400-e29b-41d4-a716-446655440000"));
        assert!(!validate_uuid("invalid-uuid"));
        assert!(!validate_uuid("550e8400-e29b-41d4-a716-44665544000")); // Too short
    }

    #[test]
    fn test_aggregate_stats() {
        let values = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let (sum, mean, min, max, count) = aggregate_stats(values);

        assert_eq!(sum, 15.0);
        assert_eq!(mean, 3.0);
        assert_eq!(min, 1.0);
        assert_eq!(max, 5.0);
        assert_eq!(count, 5);
    }

    #[test]
    fn test_compute_percentiles() {
        let values = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0];
        let percentiles = compute_percentiles(values, vec![50.0, 90.0, 99.0]);

        assert_eq!(percentiles[0], 5.0); // P50
        assert_eq!(percentiles[1], 9.0); // P90
        assert_eq!(percentiles[2], 10.0); // P99
    }

    #[test]
    fn test_batch_normalize_strings() {
        let strings = vec!["  HELLO World  ", "  test  string  "];
        let normalized = batch_normalize_strings(strings);

        assert_eq!(normalized[0], "hello world");
        assert_eq!(normalized[1], "test string");
    }

    #[test]
    fn test_count_values() {
        let values = vec!["a", "b", "a", "c", "a", "b"];
        let counts = count_values(values);

        assert_eq!(*counts.get("a").unwrap(), 3);
        assert_eq!(*counts.get("b").unwrap(), 2);
        assert_eq!(*counts.get("c").unwrap(), 1);
    }

    #[test]
    fn test_deduplicate_ordered() {
        let values = vec!["a", "b", "a", "c", "b", "d"];
        let deduped = deduplicate_ordered(values);

        assert_eq!(deduped, vec!["a", "b", "c", "d"]);
    }

    #[test]
    fn test_match_wildcard_pattern() {
        assert!(match_wildcard_pattern("test", "test"));
        assert!(match_wildcard_pattern("test", "*"));
        assert!(match_wildcard_pattern("test", "te*"));
        assert!(match_wildcard_pattern("test", "*st"));
        assert!(match_wildcard_pattern("test", "t*t"));
        assert!(!match_wildcard_pattern("test", "no*match"));
    }

    #[test]
    fn test_fast_checksum() {
        let sum1 = fast_checksum("hello");
        let sum2 = fast_checksum("hello");
        let sum3 = fast_checksum("different");

        assert_eq!(sum1, sum2);
        assert_ne!(sum1, sum3);
    }

    #[test]
    fn test_validate_identifier() {
        assert!(validate_identifier("valid_name"));
        assert!(validate_identifier("_private"));
        assert!(validate_identifier("CamelCase"));
        assert!(!validate_identifier("123invalid"));
        assert!(!validate_identifier(""));
        assert!(!validate_identifier("has-dash"));
    }
}
