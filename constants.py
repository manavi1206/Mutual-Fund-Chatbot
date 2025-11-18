"""
Constants and Configuration
Centralized constants to avoid duplication and magic strings
"""
from typing import Dict

# Scheme tag mappings
SCHEME_TAG_MAP = {
    'largecap': 'LARGE_CAP',
    'flexicap': 'FLEXI_CAP',
    'elss': 'ELSS',
    'hybrid': 'HYBRID'
}

# Reverse mapping: scheme tag -> display name
SCHEME_DISPLAY_NAMES = {
    'LARGE_CAP': 'HDFC Large Cap Fund',
    'FLEXI_CAP': 'HDFC Flexi Cap Fund',
    'ELSS': 'HDFC TaxSaver (ELSS)',
    'HYBRID': 'HDFC Hybrid Equity Fund'
}

# Field display names
FIELD_DISPLAY_NAMES = {
    'exit_load': 'Exit Load',
    'expense_ratio': 'Total Expense Ratio (TER)',
    'minimum_sip': 'Minimum SIP',
    'min_lumpsum': 'Minimum Application Amount',
    'lock_in': 'Lock-in Period',
    'benchmark': 'Benchmark',
    'riskometer': 'Riskometer'
}

# Source authority priority (higher = more authoritative)
SOURCE_AUTHORITY = {
    'sid_pdf': 1.0,
    'kim_pdf': 0.9,
    'factsheet_consolidated': 0.8,
    'scheme_overview': 0.7,
    'amfi': 0.9,
    'sebi': 0.95,
    'groww': 0.6
}

# Field source priorities (order matters - first is highest priority)
FIELD_SOURCE_PRIORITY = {
    'exit_load': ['sid_pdf', 'kim_pdf', 'factsheet_consolidated', 'scheme_overview'],
    'expense_ratio': ['sid_pdf', 'kim_pdf', 'factsheet_consolidated', 'scheme_overview'],
    'minimum_sip': ['sid_pdf', 'kim_pdf', 'factsheet_consolidated', 'scheme_overview'],
    'min_lumpsum': ['sid_pdf', 'kim_pdf', 'factsheet_consolidated', 'scheme_overview'],
    'lock_in': ['sid_pdf', 'kim_pdf', 'scheme_overview'],
    'benchmark': ['sid_pdf', 'kim_pdf', 'factsheet_consolidated', 'scheme_overview'],
    'riskometer': ['scheme_overview', 'factsheet_consolidated', 'kim_pdf', 'sid_pdf']
}

# Query classification keywords
METRIC_KEYWORDS = ['expense ratio', 'ter', 'exit load', 'minimum sip', 'lock-in', 'benchmark', 'riskometer']
SCHEME_KEYWORDS = ['large cap', 'flexi cap', 'elss', 'hybrid', 'taxsaver', 'tax saver']

# Retrieval settings
DEFAULT_TOP_K = 5
SEARCH_K_MULTIPLIER = 3
FIELD_FILTER_THRESHOLD = 3  # Minimum chunks for field filtering (was 5)

# Scraper settings
MAX_CONCURRENT_REQUESTS = 10
CACHE_TTL_HOURS = 24
REQUEST_TIMEOUT = 15

# Answer formatting
MAX_ANSWER_SENTENCES = {
    'entity': 4,
    'metric': 3,
    'list': 5,
    'how_to': 5,
    'general': 4
}

# Date formats to try
DATE_FORMATS = [
    "%m/%d/%Y",      # 11/17/2025
    "%Y-%m-%d",      # 2025-11-17
    "%d/%m/%Y",      # 17/11/2025
    "%d %b %Y",      # 17 Nov 2025
    "%d %B %Y",      # 17 November 2025
]

# Output date format
OUTPUT_DATE_FORMAT = "%d %b, %Y"  # 17 Nov, 2025


