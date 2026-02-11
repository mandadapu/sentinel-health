use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use regex::Regex;
use std::sync::LazyLock;

struct PIIPattern {
    name: &'static str,
    regex: Regex,
}

static PII_PATTERNS: LazyLock<Vec<PIIPattern>> = LazyLock::new(|| {
    vec![
        PIIPattern {
            name: "SSN",
            regex: Regex::new(r"\b\d{3}-\d{2}-\d{4}\b").unwrap(),
        },
        PIIPattern {
            name: "MRN",
            regex: Regex::new(r"(?i)\b(?:MRN)[:\s#]*\d{6,10}\b").unwrap(),
        },
        PIIPattern {
            name: "EMAIL",
            regex: Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b").unwrap(),
        },
        PIIPattern {
            name: "DOB",
            regex: Regex::new(
                r"(?i)\b(?:DOB|Date of Birth)[:\s]*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
            )
            .unwrap(),
        },
        PIIPattern {
            name: "PHONE",
            regex: Regex::new(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b").unwrap(),
        },
    ]
});

const REDACTED: &str = "[REDACTED]";

#[pyfunction]
fn scan_pii(py: Python<'_>, text: &str) -> PyResult<PyObject> {
    let mut masked = text.to_string();
    let matches = PyList::empty(py);

    for pattern in PII_PATTERNS.iter() {
        let count = pattern.regex.find_iter(&masked).count();
        if count > 0 {
            masked = pattern.regex.replace_all(&masked, REDACTED).to_string();
            let match_dict = PyDict::new(py);
            match_dict.set_item("type", pattern.name)?;
            match_dict.set_item("count", count)?;
            matches.append(match_dict)?;
        }
    }

    let result = PyDict::new(py);
    result.set_item("masked", masked)?;
    result.set_item("matches", matches)?;
    Ok(result.into())
}

#[pymodule]
fn sentinel_pii_scanner(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_pii, m)?)?;
    Ok(())
}
