"""
High-Precision Mutual Fund Fact Extractor
AI Director - Fintech RAG Pipeline
Deterministic, production-ready fact extraction with strict source priorities
"""
import os
import re
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import traceback

# Directories
DATA_PROCESSED = Path("data_processed")
CHUNKS_CLEAN_DIR = Path("chunks_clean")
FACTS_VERIFIED_DIR = Path("facts_verified")
LOGS_DIR = Path("logs")
SOURCES_CSV = Path("sources.csv")

# Create directories
for dir_path in [CHUNKS_CLEAN_DIR, FACTS_VERIFIED_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Logging
LOG_FILE = LOGS_DIR / "cleaning.log"
OCR_REQUIRED_FILE = LOGS_DIR / "ocr_required.txt"

def log(message: str, level: str = "INFO"):
    """Write to log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)
    if level in ["ERROR", "WARN"]:
        print(log_entry.strip())

def load_sources() -> Dict[str, Dict]:
    """Load sources.csv and create lookup"""
    sources = {}
    try:
        with open(SOURCES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sources[row["source_id"]] = {
                    "source_url": row["source_url"],
                    "source_type": row["source_type"],
                    "scheme_tag": row["scheme_tag"],
                    "authority": row["authority"],
                    "last_fetched_date": row["last_fetched_date"]
                }
        log(f"Loaded {len(sources)} sources from sources.csv")
    except Exception as e:
        log(f"Error loading sources.csv: {e}", "ERROR")
    return sources

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace: join broken lines, collapse multiple spaces"""
    # Replace newlines with spaces
    text = text.replace("\n", " ")
    # Collapse repeated whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def fix_ocr_artifacts(text: str, source_id: str) -> str:
    """Fix common OCR split-word artifacts with logging"""
    fixes_count = 0
    
    # Specific deterministic fixes
    patterns = [
        (r"\bMi\s?nimum\b", "Minimum", "Mi nimum"),
        (r"\bSe\s?gregated\b", "Segregated", "Se gregated"),
        (r"\bSto\s?ck\b", "Stock", "Sto ck"),
    ]
    
    for pattern, replacement, label in patterns:
        matches = len(re.findall(pattern, text, re.IGNORECASE))
        if matches > 0:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            fixes_count += matches
            log(f"{source_id}: Fixed '{label}' -> '{replacement}' ({matches} occurrences)")
    
    # Fix hyphenation at line breaks: invest-\nment -> investment
    text = re.sub(r"(\w+)-\s+(\w+)", r"\1\2", text)
    
    # Collapse single-letter internal spaces for short tokens (conservative)
    def collapse_short_spaces(match):
        before = match.group(1)
        after = match.group(2)
        if len(before) <= 4 and len(after) <= 4:
            combined = before + after
            # Check if combined looks like a real word (has vowels)
            if re.search(r'[aeiouAEIOU]', combined):
                return combined
        return match.group(0)
    
    text = re.sub(r"(\w{1,4})\s(\w{1,4})", collapse_short_spaces, text)
    
    if fixes_count > 0:
        log(f"{source_id}: Applied {fixes_count} OCR fixes")
    
    return text

def normalize_currency_numbers(text: str) -> str:
    """Normalize currency and numbers"""
    # Currency: (₹|Rs\.?|INR)\s?([0-9,]+(?:\.[0-9]+)?) -> ₹<digits_no_commas>
    text = re.sub(r"(?:₹|Rs\.?|INR)\s?([0-9,]+(?:\.[0-9]+)?)", r"₹\1", text)
    # Remove commas from numbers
    text = re.sub(r"₹([0-9,]+)", lambda m: "₹" + m.group(1).replace(",", ""), text)
    # Percent: normalize spacing
    text = re.sub(r"([0-9]+(?:\.[0-9]+)?)\s?%", r"\1%", text)
    return text

def remove_repeated_headers_footers(text: str) -> str:
    """Remove repeated headers/footers that occur >3 times"""
    lines = text.split(" ")
    word_counts = {}
    for word in lines:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    # Remove words that appear >3 times and are likely headers/footers
    # (short words, all caps, or common header patterns)
    filtered_words = []
    for word in lines:
        if word_counts[word] > 3:
            # Check if it's likely a header/footer
            if (len(word) < 10 and word.isupper()) or word in ["Page", "Page:", "©", "Copyright"]:
                continue
        filtered_words.append(word)
    
    return " ".join(filtered_words)

def redact_pii(text: str, source_id: str) -> str:
    """Detect and redact PII"""
    redactions = 0
    
    # PAN: [A-Z]{5}[0-9]{4}[A-Z]
    pan_pattern = r"[A-Z]{5}[0-9]{4}[A-Z]"
    pan_matches = re.findall(pan_pattern, text)
    if pan_matches:
        text = re.sub(pan_pattern, "<REDACTED_PII>", text)
        redactions += len(pan_matches)
        log(f"{source_id}: Redacted {len(pan_matches)} PAN numbers")
    
    # Aadhaar: \b[0-9]{4}\s[0-9]{4}\s[0-9]{4}\b
    aadhaar_pattern = r"\b[0-9]{4}\s[0-9]{4}\s[0-9]{4}\b"
    aadhaar_matches = re.findall(aadhaar_pattern, text)
    if aadhaar_matches:
        text = re.sub(aadhaar_pattern, "<REDACTED_PII>", text)
        redactions += len(aadhaar_matches)
        log(f"{source_id}: Redacted {len(aadhaar_matches)} Aadhaar numbers")
    
    # Email
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    email_matches = re.findall(email_pattern, text)
    if email_matches:
        text = re.sub(email_pattern, "<REDACTED_PII>", text)
        redactions += len(email_matches)
        log(f"{source_id}: Redacted {len(email_matches)} email addresses")
    
    # Phone (10-digit Indian numbers)
    phone_pattern = r"\b[6-9][0-9]{9}\b"
    phone_matches = re.findall(phone_pattern, text)
    if phone_matches:
        text = re.sub(phone_pattern, "<REDACTED_PII>", text)
        redactions += len(phone_matches)
        log(f"{source_id}: Redacted {len(phone_matches)} phone numbers")
    
    if redactions > 0:
        log(f"{source_id}: Total PII redactions: {redactions}")
    
    return text

def clean_text(text: str, source_id: str) -> str:
    """Apply all cleaning steps in order"""
    original_len = len(text)
    text = normalize_whitespace(text)
    text = fix_ocr_artifacts(text, source_id)
    text = normalize_currency_numbers(text)
    text = remove_repeated_headers_footers(text)
    text = redact_pii(text, source_id)
    cleaned_len = len(text)
    log(f"{source_id}: Cleaned {source_id}: {original_len} -> {cleaned_len} chars, PII redactions logged above")
    return text

# ============================================================================
# EXTRACTION FUNCTIONS (with source priority enforcement)
# ============================================================================

def extract_minimum_sip(text: str) -> Optional[str]:
    """Extract minimum SIP amount"""
    # Search for "Minimum SIP" or "Minimum Subscription" patterns
    # Handle cases where words might be concatenated after cleaning
    patterns = [
        r"Minimum\s+SIP[:\s]+(?:₹|Rs\.?|INR)?\s?([0-9,]+)",
        r"Minimum\s+Subscription[:\s]+(?:₹|Rs\.?|INR)?\s?([0-9,]+)",
        r"Minimum\s+Installment[:\s]+(?:₹|Rs\.?|INR)?\s?([0-9,]+)",
        r"MinimumSIP[:\s]+(?:₹|Rs\.?|INR)?\s?([0-9,]+)",  # Concatenated
        r"Minimum\s+Application[:\s]+(?:₹|Rs\.?|INR)?\s?([0-9,]+)",  # Sometimes SIP uses "Application"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                amount = int(amount_str)
                # Validation: must be ≥ ₹100
                if amount >= 100:
                    return f"₹{amount}"
                else:
                    return None  # Invalid amount
            except ValueError:
                continue
    
    # Also try finding "Rs.100" or "₹100" patterns (common minimum SIP)
    # Pattern: Rs.100/- or ₹100 or Rs 100
    simple_patterns = [
        r"(?:Rs\.?|₹|INR)\s?100(?:\s?/-)?",
        r"100\s?(?:/-|rupees)",
    ]
    for pattern in simple_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            # Check context - should be near "SIP", "subscription", "minimum", or "application"
            start = max(0, match.start()-100)
            end = min(len(text), match.end()+100)
            context = text[start:end].lower()
            if any(keyword in context for keyword in ["sip", "subscription", "minimum", "application", "installment"]):
                return "₹100"
    
    # Also try finding "SIP" and look for nearby numbers
    sip_positions = []
    for match in re.finditer(r"\bSIP\b", text, re.IGNORECASE):
        sip_positions.append((match.start(), match.end()))
    
    for sip_start, sip_end in sip_positions:
        # Look before and after for "Minimum" and numbers
        before_text = text[max(0, sip_start-50):sip_start]
        after_text = text[sip_end:min(len(text), sip_end+100)]
        
        if "minimum" in before_text.lower():
            # Find number after SIP
            num_match = re.search(r"([0-9,]+)", after_text)
            if num_match:
                amount_str = num_match.group(1).replace(",", "")
                try:
                    amount = int(amount_str)
                    if amount >= 100:
                        return f"₹{amount}"
                except ValueError:
                    continue
    
    return None

def extract_minimum_lumpsum(text: str) -> Optional[str]:
    """Extract minimum application/lumpsum amount"""
    patterns = [
        r"Minimum\s+Application[:\s]+(?:₹|Rs\.?|INR)?\s?([0-9,]+)",
        r"Minimum\s+Amount[:\s]+(?:₹|Rs\.?|INR)?\s?([0-9,]+)",
        r"Minimum\s+Investment[:\s]+(?:₹|Rs\.?|INR)?\s?([0-9,]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                amount = int(amount_str)
                return f"₹{amount}"
            except ValueError:
                continue
    
    return None

def extract_exit_load(text: str) -> Optional[str]:
    """Extract exit load information - capture structured exit loads"""
    # First, look for structured exit loads: "X% if within Y time, Nil/Nothing after"
    # Pattern: Exit Load of X% if within Y, No/Nil after Y
    structured_patterns = [
        r"Exit\s*Load\s*of\s*([0-9]+(?:\.[0-9]+)?)\s?%\s*.*?(?:within|from).*?(?:year|month).*?(?:No|Nil|no)\s*Exit\s*Load",
        r"Exit\s*Load[:\s]+([0-9]+(?:\.[0-9]+)?)\s?%\s*.*?(?:within|from).*?(?:year|month).*?(?:No|Nil|no)\s*Exit\s*Load",
    ]
    
    for pattern in structured_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = float(match.group(1))
            if 0.1 <= value <= 10.0:
                return f"{match.group(1)}%"
    
    # Look for "Exit Load" or "Redemption Charge" patterns
    patterns = [
        r"Exit\s+Load[:\s]+([0-9]+(?:\.[0-9]+)?)\s?%",
        r"Redemption\s+Charge[:\s]+([0-9]+(?:\.[0-9]+)?)\s?%",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.lastindex and match.group(1):
                value = float(match.group(1))
                if 0.1 <= value <= 10.0:
                    return f"{match.group(1)}%"
    
    # Also handle cases where words are concatenated after cleaning
    # Pattern: "Exit Load" followed by number within reasonable distance
    exit_load_positions = []
    for match in re.finditer(r"Exit\s*Load|Redemption\s*Charge", text, re.IGNORECASE):
        exit_load_positions.append(match.end())
    
    for exit_end in exit_load_positions:
        # Look for percentage in next 200 characters (more generous for structured loads)
        search_text = text[exit_end:exit_end+200]
        # Look for patterns like "1.00%" or "1%" after "Exit Load"
        percent_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s?%", search_text)
        if percent_match:
            # Check if there's a "No Exit Load" or "Nil" AFTER the percentage (structured load)
            after_percent = search_text[percent_match.end():]
            has_structured = re.search(r"(?:No|Nil|no)\s*Exit\s*Load", after_percent, re.IGNORECASE)
            
            # Check if it's "Nil" or "No" BEFORE the number
            before_text = search_text[:percent_match.start()].lower()
            if "nil" in before_text or ("no" in before_text and "exit" in before_text):
                # This is a "Nil" case, but check if there's a percentage mentioned elsewhere
                continue
            else:
                value = float(percent_match.group(1))
                if 0.1 <= value <= 10.0:  # Sanity check for exit load (usually 0-5%)
                    return f"{percent_match.group(1)}%"
    
    # Check for explicit "Nil" or "No Exit Load" (only if no percentage found)
    if re.search(r"Exit\s*Load[:\s]+(?:Nil|No\s+Exit\s+Load)", text, re.IGNORECASE):
        return "Nil"
    
    return None

def extract_lock_in(text: str, scheme_tag: str) -> Optional[str]:
    """Extract lock-in period - ONLY for ELSS schemes"""
    # ONLY set for ELSS
    if scheme_tag != "ELSS":
        return None
    
    # For ELSS, it's statutory: 3 years
    if "ELSS" in text.upper() or "Equity Linked Saving" in text:
        return "3 years"
    
    # Also check for explicit lock-in mentions
    patterns = [
        r"Lock[-\s]?in[:\s]+([0-9]+)\s*(?:year|years|yr|yrs)",
        r"Lock[-\s]?in\s+period[:\s]+([0-9]+)\s*(?:year|years|yr|yrs)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            years = int(match.group(1))
            if years == 3:
                return "3 years"
    
    return None

def extract_expense_ratio(text: str, source_type: str) -> Optional[str]:
    """Extract expense ratio/TER - ONLY from factsheet_consolidated or AMFI regulatory"""
    # STRICT: Only extract from factsheet_consolidated or regulatory (AMFI)
    if source_type not in ["factsheet_consolidated", "regulatory"]:
        return None
    
    patterns = [
        r"Total\s+Expense\s+Ratio[:\s]+([0-9]+(?:\.[0-9]+)?)\s?%",
        r"TER[:\s]+([0-9]+(?:\.[0-9]+)?)\s?%",
        r"expense\s+ratio[:\s]+([0-9]+(?:\.[0-9]+)?)\s?%",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1)
            try:
                val_float = float(value)
                if 0.1 <= val_float <= 5.0:  # Sanity check
                    return f"{value}%"
            except ValueError:
                continue
    
    # Also try finding TER followed by number (flexible spacing)
    ter_positions = []
    for match in re.finditer(r"Total\s+Expense\s+Ratio|TER\b|expense\s+ratio", text, re.IGNORECASE):
        ter_positions.append(match.end())
    
    for ter_end in ter_positions:
        search_text = text[ter_end:ter_end+100]
        num_match = re.search(r"([0-9]+\.[0-9]{1,2})", search_text)
        if num_match:
            value = float(num_match.group(1))
            if 0.1 <= value <= 5.0:
                return f"{num_match.group(1)}%"
    
    return None

def extract_benchmark(text: str) -> Optional[str]:
    """Extract benchmark name"""
    # Look for NIFTY, SENSEX, BSE, NSE patterns
    benchmark_patterns = [
        r"Benchmark[:\s]+(NIFTY\s+[0-9]+(?:\s+[A-Z]+)?)",
        r"Benchmark[:\s]+(S&P\s+BSE\s+[0-9]+)",
        r"Benchmark[:\s]+(BSE\s+[0-9]+)",
        r"Benchmark\s+Index[:\s]+(NIFTY\s+[0-9]+(?:\s+[A-Z]+)?)",
        r"(NIFTY\s+[0-9]+(?:\s+[A-Z]+)?)\s+Index",
    ]
    
    for pattern in benchmark_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            benchmark = match.group(1).strip()
            # Clean up common artifacts
            benchmark = re.sub(r"\b(website|subjectto|fields)\b", "", benchmark, flags=re.IGNORECASE)
            benchmark = re.sub(r"\s+", " ", benchmark).strip()
            if len(benchmark) > 3:
                return benchmark
    
    return None

def extract_riskometer(text: str) -> Optional[str]:
    """Extract riskometer level"""
    # Must be one of: Low, Low to Moderate, Moderate, Moderately High, High, Very High
    valid_levels = [
        "Very High",
        "Moderately High",
        "Low to Moderate",
        "Moderate",
        "High",
        "Low"
    ]
    
    # Search for riskometer mentions
    riskometer_patterns = [
        r"Risk[-\s]?o[-\s]?meter[:\s]+([^.\n]+)",
        r"Riskometer[:\s]+([^.\n]+)",
        r"Risk\s+Level[:\s]+([^.\n]+)",
    ]
    
    for pattern in riskometer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            level_text = match.group(1).strip()
            # Check if it matches any valid level
            for valid_level in valid_levels:
                if valid_level.lower() in level_text.lower():
                    return valid_level
    
    return None

# ============================================================================
# SOURCE PRIORITY MAP (STRICT)
# ============================================================================

def get_field_source_priority(field: str) -> List[str]:
    """Return ordered list of source types for a field (highest priority first)"""
    priority_map = {
        "minimum_sip": ["kim_pdf", "sid_pdf", "scheme_overview"],
        "min_lumpsum": ["kim_pdf", "sid_pdf", "scheme_overview"],
        "exit_load": ["sid_pdf", "kim_pdf", "factsheet_consolidated", "scheme_overview"],  # Added scheme_overview as fallback
        "lock_in": ["regulatory"],  # Only ELSS, statutory
        "expense_ratio": ["factsheet_consolidated", "regulatory"],  # ONLY these
        "benchmark": ["scheme_overview", "factsheet_consolidated"],
        "riskometer": ["scheme_overview", "factsheet_consolidated"],
    }
    return priority_map.get(field, [])

def should_extract_field(field: str, source_type: str) -> bool:
    """Check if field should be extracted from this source type"""
    allowed_types = get_field_source_priority(field)
    return source_type in allowed_types

# ============================================================================
# CHUNK CREATION
# ============================================================================

def create_chunk_text(field: str, value: str, source_id: str, source_type: str) -> str:
    """Create clean chunk text (1-3 sentences, ≤600 chars)"""
    field_labels = {
        "minimum_sip": "Minimum SIP",
        "min_lumpsum": "Minimum application amount",
        "exit_load": "Exit Load",
        "lock_in": "Lock-in period",
        "expense_ratio": "Total Expense Ratio (TER)",
        "benchmark": "Benchmark",
        "riskometer": "Riskometer",
    }
    
    label = field_labels.get(field, field)
    
    # Format based on field
    if field == "exit_load" and value == "Nil":
        chunk_text = f"{label}: Nil. Source: {source_id} ({source_type})."
    elif field == "lock_in":
        chunk_text = f"{label}: {value}. Source: {source_id} ({source_type})."
    else:
        chunk_text = f"{label}: {value}. Source: {source_id} ({source_type})."
    
    # Ensure ≤600 chars
    if len(chunk_text) > 600:
        chunk_text = chunk_text[:597] + "..."
    
    return chunk_text

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_source(source_id: str, sources: Dict[str, Dict]) -> Tuple[List[Dict], Dict]:
    """Process a single source file"""
    text_file = DATA_PROCESSED / f"{source_id}.txt"
    
    if not text_file.exists():
        log(f"{source_id}: File not found: {text_file}", "WARN")
        return [], {}
    
    # Check metadata
    source_meta = sources.get(source_id)
    if not source_meta:
        log(f"{source_id}: Missing metadata in sources.csv", "WARN")
        return [], {}
    
    try:
        # Read and clean text
        with open(text_file, "r", encoding="utf-8") as f:
            raw_text = f.read()
        
        if len(raw_text.strip()) < 200:
            log(f"{source_id}: File too short (<200 chars), may require OCR", "WARN")
            with open(OCR_REQUIRED_FILE, "a") as f:
                f.write(f"{source_id}\n")
            return [], {}
        
        cleaned_text = clean_text(raw_text, source_id)
        
        if len(cleaned_text.strip()) < 200:
            log(f"{source_id}: Cleaned text too short, flagging for OCR", "WARN")
            with open(OCR_REQUIRED_FILE, "a") as f:
                f.write(f"{source_id}\n")
            return [], {}
        
        source_type = source_meta["source_type"]
        scheme_tag = source_meta["scheme_tag"]
        
        # Extract facts based on source priority
        facts = {}
        fields_attempted = []
        fields_found = []
        
        # minimum_sip
        if should_extract_field("minimum_sip", source_type):
            fields_attempted.append("minimum_sip")
            value = extract_minimum_sip(cleaned_text)
            if value:
                facts["min_sip"] = value
                fields_found.append("minimum_sip")
            else:
                facts["min_sip"] = None
        
        # min_lumpsum
        if should_extract_field("min_lumpsum", source_type):
            fields_attempted.append("min_lumpsum")
            value = extract_minimum_lumpsum(cleaned_text)
            if value:
                facts["min_lumpsum"] = value
                fields_found.append("min_lumpsum")
            else:
                facts["min_lumpsum"] = None
        
        # exit_load
        if should_extract_field("exit_load", source_type):
            fields_attempted.append("exit_load")
            value = extract_exit_load(cleaned_text)
            if value:
                facts["exit_load"] = value
                fields_found.append("exit_load")
            else:
                facts["exit_load"] = None
        
        # lock_in (ONLY for ELSS) - STATUTORY: always 3 years for ELSS
        if scheme_tag == "ELSS":
            fields_attempted.append("lock_in")
            # Statutory: ELSS always has 3-year lock-in
            facts["lock_in"] = "3 years"
            fields_found.append("lock_in")
            # Also try to extract from text to verify
            extracted_value = extract_lock_in(cleaned_text, scheme_tag)
            if extracted_value and extracted_value != "3 years":
                log(f"{source_id}: WARN - ELSS lock_in extracted as {extracted_value}, overriding to 3 years (statutory)", "WARN")
        else:
            facts["lock_in"] = None  # Not ELSS
        
        # expense_ratio (ONLY from factsheet or AMFI)
        if should_extract_field("expense_ratio", source_type):
            fields_attempted.append("expense_ratio")
            value = extract_expense_ratio(cleaned_text, source_type)
            if value:
                facts["expense_ratio"] = value
                fields_found.append("expense_ratio")
            else:
                facts["expense_ratio"] = None
        else:
            facts["expense_ratio"] = None  # Not allowed source
        
        # benchmark
        if should_extract_field("benchmark", source_type):
            fields_attempted.append("benchmark")
            value = extract_benchmark(cleaned_text)
            if value:
                facts["benchmark"] = value
                fields_found.append("benchmark")
            else:
                facts["benchmark"] = None
        
        # riskometer
        if should_extract_field("riskometer", source_type):
            fields_attempted.append("riskometer")
            value = extract_riskometer(cleaned_text)
            if value:
                facts["riskometer"] = value
                fields_found.append("riskometer")
            else:
                facts["riskometer"] = None
        
        # Create chunks
        chunks = []
        field_mapping = {
            "min_sip": "minimum_sip",
            "min_lumpsum": "min_lumpsum",
            "exit_load": "exit_load",
            "lock_in": "lock_in",
            "expense_ratio": "expense_ratio",
            "benchmark": "benchmark",
            "riskometer": "riskometer",
        }
        
        for fact_key, fact_value in facts.items():
            if fact_value:  # Only create chunk if value found
                field = field_mapping[fact_key]
                chunk_id = f"{source_id}__{field}"
                chunk_text = create_chunk_text(field, fact_value, source_id, source_type)
                
                chunk = {
                    "id": chunk_id,
                    "source_id": source_id,
                    "source_url": source_meta["source_url"],
                    "authority": source_meta["authority"],
                    "source_type": source_type,
                    "scheme_tag": scheme_tag,
                    "field": field,
                    "chunk_index": 0,
                    "chunk_text": chunk_text,
                    "last_fetched_date": source_meta["last_fetched_date"]
                }
                chunks.append(chunk)
        
        log(f"{source_id}: Attempted {len(fields_attempted)} fields, found {len(fields_found)}: {', '.join(fields_found) if fields_found else 'none'}, created {len(chunks)} chunks")
        
        return chunks, facts
        
    except Exception as e:
        log(f"{source_id}: Error processing: {e}\n{traceback.format_exc()}", "ERROR")
        return [], {}

# Deduplication is handled in main() directly

def quality_checks(chunks: List[Dict], facts: Dict[str, Dict], sources: Dict[str, Dict]):
    """Run quality checks"""
    issues = []
    
    # Check 1: ELSS must have lock_in = 3 years
    elss_sources = [s for s, m in sources.items() if m.get("scheme_tag") == "ELSS"]
    for source_id in elss_sources:
        fact = facts.get(source_id, {})
        if fact.get("lock_in") != "3 years":
            issues.append(f"{source_id}: ELSS missing lock_in=3 years")
            log(f"{source_id}: QUALITY CHECK FAILED - ELSS must have lock_in=3 years", "WARN")
    
    # Check 2: min_sip must match ₹[0-9]+ pattern
    for source_id, fact in facts.items():
        min_sip = fact.get("min_sip")
        if min_sip and not re.match(r"₹[0-9]+", min_sip):
            issues.append(f"{source_id}: Invalid min_sip format: {min_sip}")
            log(f"{source_id}: QUALITY CHECK FAILED - Invalid min_sip format: {min_sip}", "WARN")
            facts[source_id]["min_sip"] = None  # Blank it
    
    # Check 3: expense_ratio must come from factsheet or AMFI
    for chunk in chunks:
        if chunk["field"] == "expense_ratio":
            if chunk["source_type"] not in ["factsheet_consolidated", "regulatory"]:
                issues.append(f"{chunk['source_id']}: expense_ratio from invalid source: {chunk['source_type']}")
                log(f"{chunk['source_id']}: QUALITY CHECK FAILED - expense_ratio from invalid source", "WARN")
                # Remove chunk
                chunks.remove(chunk)
                if chunk["source_id"] in facts:
                    facts[chunk["source_id"]]["expense_ratio"] = None
    
    # Check 4: Count extracted fields per scheme
    scheme_field_counts = {}
    for source_id, fact in facts.items():
        scheme_tag = sources.get(source_id, {}).get("scheme_tag", "UNKNOWN")
        if scheme_tag not in scheme_field_counts:
            scheme_field_counts[scheme_tag] = 0
        count = sum(1 for v in fact.values() if v)
        scheme_field_counts[scheme_tag] = max(scheme_field_counts[scheme_tag], count)
    
    for scheme_tag, count in scheme_field_counts.items():
        if count < 3:
            issues.append(f"{scheme_tag}: Only {count} fields extracted (<3)")
            log(f"{scheme_tag}: QUALITY CHECK - Only {count} fields extracted", "WARN")
    
    return issues

def main():
    """Main processing function"""
    log("=" * 70)
    log("Starting High-Precision Fact Extraction")
    log("=" * 70)
    
    # Clear log files
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    if OCR_REQUIRED_FILE.exists():
        OCR_REQUIRED_FILE.unlink()
    
    # Load sources
    sources = load_sources()
    if not sources:
        log("No sources loaded, exiting", "ERROR")
        return 1
    
    # Process all sources
    all_chunks = []
    all_facts = {}
    sources_processed = 0
    sources_missing_metadata = 0
    
    for source_id in sources.keys():
        chunks, facts = process_source(source_id, sources)
        if chunks or facts:
            sources_processed += 1
            all_chunks.extend(chunks)
            all_facts[source_id] = facts
        elif source_id in sources:
            # Check if it was missing metadata
            if not sources.get(source_id):
                sources_missing_metadata += 1
    
    # Deduplicate by priority
    # Group by (scheme_tag, field) and keep highest priority
    chunk_groups = {}
    for chunk in all_chunks:
        key = (chunk["scheme_tag"], chunk["field"])
        if key not in chunk_groups:
            chunk_groups[key] = []
        chunk_groups[key].append(chunk)
    
    final_chunks = []
    for (scheme_tag, field), chunks_list in chunk_groups.items():
        field_priorities = get_field_source_priority(field)
        priority_map = {st: i for i, st in enumerate(field_priorities)}
        
        def get_priority(chunk):
            st = chunk["source_type"]
            return priority_map.get(st, 999)
        
        chunks_list.sort(key=get_priority)
        final_chunks.append(chunks_list[0])
    
    # Aggregate facts by scheme_tag (keep highest priority source per field)
    # For now, keep all facts per source_id
    final_facts = all_facts
    
    # Quality checks
    quality_issues = quality_checks(final_chunks, final_facts, sources)
    
    # Write chunks
    CHUNKS_CLEAN_DIR.mkdir(exist_ok=True)
    chunks_file = CHUNKS_CLEAN_DIR / "chunks_clean.jsonl"
    with open(chunks_file, "w", encoding="utf-8") as f:
        for chunk in final_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    log(f"Written {len(final_chunks)} chunks to {chunks_file}")
    
    # Write facts CSV
    FACTS_VERIFIED_DIR.mkdir(exist_ok=True)
    facts_file = FACTS_VERIFIED_DIR / "facts_extracted.csv"
    with open(facts_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source_id", "scheme_tag", "min_sip", "min_lumpsum", "exit_load",
            "lock_in", "expense_ratio", "benchmark", "riskometer",
            "source_url", "last_fetched_date"
        ])
        writer.writeheader()
        for source_id, facts_dict in final_facts.items():
            source_meta = sources.get(source_id, {})
            row = {
                "source_id": source_id,
                "scheme_tag": source_meta.get("scheme_tag", ""),
                "min_sip": facts_dict.get("min_sip", ""),
                "min_lumpsum": facts_dict.get("min_lumpsum", ""),
                "exit_load": facts_dict.get("exit_load", ""),
                "lock_in": facts_dict.get("lock_in", ""),
                "expense_ratio": facts_dict.get("expense_ratio", ""),
                "benchmark": facts_dict.get("benchmark", ""),
                "riskometer": facts_dict.get("riskometer", ""),
                "source_url": source_meta.get("source_url", ""),
                "last_fetched_date": source_meta.get("last_fetched_date", ""),
            }
            writer.writerow(row)
    log(f"Written facts to {facts_file}")
    
    # Count fields
    field_counts = {
        "min_sip": 0,
        "min_lumpsum": 0,
        "exit_load": 0,
        "lock_in": 0,
        "expense_ratio": 0,
        "benchmark": 0,
        "riskometer": 0,
    }
    for facts_dict in final_facts.values():
        for field in field_counts:
            if facts_dict.get(field):
                field_counts[field] += 1
    
    # Count OCR required
    ocr_count = 0
    if OCR_REQUIRED_FILE.exists():
        with open(OCR_REQUIRED_FILE, "r") as f:
            ocr_count = len([line for line in f if line.strip()])
    
    # Print summary
    log("=" * 70)
    log("CLEANING COMPLETE")
    log("=" * 70)
    log(f"Sources processed: {sources_processed}")
    log(f"Chunks created: {len(final_chunks)}")
    log(f"Sources flagged for OCR: {ocr_count}")
    log(f"Sources missing metadata: {sources_missing_metadata}")
    log("")
    log("Facts found per field:")
    for field, count in field_counts.items():
        log(f"  {field}: {count}")
    
    # Print to stdout
    print(f"\nCLEANING COMPLETE: {sources_processed} sources processed, {len(final_chunks)} chunks created, {ocr_count} sources flagged_for_ocr, {sources_missing_metadata} sources_missing_metadata")
    print(f"\nFacts per field:")
    for field, count in field_counts.items():
        print(f"  {field}: {count}")
    print(f"\nOutput files:")
    print(f"  {chunks_file}")
    print(f"  {facts_file}")
    print(f"  {LOG_FILE}")
    print(f"  {OCR_REQUIRED_FILE}")
    
    return 0 if len(final_chunks) >= len(sources) * 0.5 else 1

if __name__ == "__main__":
    exit(main())
