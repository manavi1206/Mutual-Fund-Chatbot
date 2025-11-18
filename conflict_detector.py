"""
Conflict Detector - Detects and logs conflicts when different sources have different values
"""
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re


class ConflictDetector:
    """Detects conflicts in extracted facts across different sources"""
    
    def __init__(self, facts_file: str = "facts_verified/facts_extracted.csv"):
        self.facts_file = Path(facts_file)
        self.conflicts = []
        self.source_priority = {
            'sid': 1.0,
            'kim': 0.9,
            'factsheet': 0.8,
            'overview': 0.7,
            'amfi': 0.9,
            'sebi': 0.95,
            'groww': 0.6
        }
    
    def _get_source_priority(self, source_id: str) -> float:
        """Get priority score for a source (higher = more authoritative)"""
        source_lower = source_id.lower()
        for source_type, priority in self.source_priority.items():
            if source_type in source_lower:
                return priority
        return 0.5
    
    def _normalize_value(self, value: str, field: str) -> Optional[float]:
        """Normalize value for comparison (extract numeric value)"""
        if not value or value.lower() in ['nil', 'na', 'n/a', 'not available', '']:
            return None
        
        # Extract number from value
        if field in ['expense_ratio', 'exit_load']:
            # Look for percentage: "1.00%" or "1.00 %" or "1.00% per annum"
            match = re.search(r'(\d+\.?\d*)\s*%', value, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        elif field in ['minimum_sip', 'min_lumpsum']:
            # Look for amount: "Rs. 100" or "₹100" or "100"
            # Remove commas, extract number
            cleaned = re.sub(r'[₹Rs.,\s]', '', value)
            match = re.search(r'(\d+)', cleaned)
            if match:
                return float(match.group(1))
        
        elif field == 'lock_in':
            # Look for years: "3 years" or "3 Y" or "36 months"
            match = re.search(r'(\d+)', value)
            if match:
                years = float(match.group(1))
                if 'month' in value.lower():
                    years = years / 12
                return years
        
        return None
    
    def _values_conflict(self, val1: Optional[float], val2: Optional[float], field: str, threshold: float = 0.01) -> bool:
        """Check if two values conflict (different beyond threshold)"""
        if val1 is None or val2 is None:
            return False  # Can't compare if one is missing
        
        if field in ['expense_ratio', 'exit_load']:
            # For percentages, allow small differences (rounding)
            return abs(val1 - val2) > threshold
        
        elif field in ['minimum_sip', 'min_lumpsum']:
            # For amounts, allow small differences
            return abs(val1 - val2) > 10  # 10 rupees difference
        
        elif field == 'lock_in':
            # For lock-in, must be exact
            return val1 != val2
        
        return False
    
    def detect_conflicts(self) -> List[Dict]:
        """
        Detect conflicts in facts across sources
        
        Returns:
            List of conflict dictionaries
        """
        if not self.facts_file.exists():
            return []
        
        # Load facts
        facts_by_scheme = {}  # scheme_tag -> {field -> [(source_id, value, priority)]}
        
        with open(self.facts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                scheme_tag = row.get('scheme_tag', '')
                source_id = row.get('source_id', '')
                priority = self._get_source_priority(source_id)
                
                if scheme_tag not in facts_by_scheme:
                    facts_by_scheme[scheme_tag] = {}
                
                # Check each field
                fields = ['min_sip', 'min_lumpsum', 'exit_load', 'lock_in', 'expense_ratio']
                for field in fields:
                    value = row.get(field, '').strip()
                    if value and value.lower() not in ['nil', 'na', 'n/a', '']:
                        if field not in facts_by_scheme[scheme_tag]:
                            facts_by_scheme[scheme_tag][field] = []
                        
                        facts_by_scheme[scheme_tag][field].append({
                            'source_id': source_id,
                            'value': value,
                            'priority': priority
                        })
        
        # Detect conflicts
        conflicts = []
        for scheme_tag, fields in facts_by_scheme.items():
            for field, values in fields.items():
                if len(values) < 2:
                    continue  # Need at least 2 sources to have a conflict
                
                # Normalize and compare values
                normalized = []
                for v in values:
                    norm_val = self._normalize_value(v['value'], field)
                    if norm_val is not None:
                        normalized.append({
                            'source_id': v['source_id'],
                            'value': v['value'],
                            'normalized': norm_val,
                            'priority': v['priority']
                        })
                
                # Check for conflicts
                if len(normalized) >= 2:
                    # Sort by priority (highest first)
                    normalized.sort(key=lambda x: x['priority'], reverse=True)
                    
                    # Compare highest priority with others
                    authoritative = normalized[0]
                    for other in normalized[1:]:
                        if self._values_conflict(authoritative['normalized'], other['normalized'], field):
                            conflicts.append({
                                'scheme_tag': scheme_tag,
                                'field': field,
                                'authoritative_source': authoritative['source_id'],
                                'authoritative_value': authoritative['value'],
                                'conflicting_source': other['source_id'],
                                'conflicting_value': other['value'],
                                'authoritative_priority': authoritative['priority'],
                                'conflicting_priority': other['priority'],
                                'detected_at': datetime.now().isoformat()
                            })
        
        self.conflicts = conflicts
        return conflicts
    
    def log_conflicts(self, output_file: str = "logs/conflicts.json"):
        """Log conflicts to file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.conflicts, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Logged {len(self.conflicts)} conflicts to {output_path}")
    
    def get_resolved_value(self, scheme_tag: str, field: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get resolved value for a field (using source priority)
        
        Returns:
            (value, source_id) or (None, None) if not found
        """
        if not self.facts_file.exists():
            return None, None
        
        candidates = []
        
        with open(self.facts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('scheme_tag') == scheme_tag:
                    value = row.get(field, '').strip()
                    if value and value.lower() not in ['nil', 'na', 'n/a', '']:
                        source_id = row.get('source_id', '')
                        priority = self._get_source_priority(source_id)
                        candidates.append({
                            'value': value,
                            'source_id': source_id,
                            'priority': priority
                        })
        
        if not candidates:
            return None, None
        
        # Return highest priority
        candidates.sort(key=lambda x: x['priority'], reverse=True)
        return candidates[0]['value'], candidates[0]['source_id']


if __name__ == "__main__":
    detector = ConflictDetector()
    conflicts = detector.detect_conflicts()
    
    if conflicts:
        print(f"\n⚠️  Found {len(conflicts)} conflicts:")
        for conflict in conflicts[:5]:  # Show first 5
            print(f"\n  Scheme: {conflict['scheme_tag']}")
            print(f"  Field: {conflict['field']}")
            print(f"  Authoritative ({conflict['authoritative_source']}): {conflict['authoritative_value']}")
            print(f"  Conflicting ({conflict['conflicting_source']}): {conflict['conflicting_value']}")
        
        detector.log_conflicts()
    else:
        print("✓ No conflicts detected")

