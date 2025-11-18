"""
Response Formatter - Ensures structured, readable output
Enterprise-grade UX excellence
"""
import re
from typing import List, Dict, Optional


class ResponseFormatter:
    """Formats responses with structure, bullets, headings, and steps"""
    
    def __init__(self):
        """Initialize response formatter"""
        pass
    
    def format_with_structure(self, answer: str, query_type: str = 'general') -> str:
        """
        Format answer with proper structure (bullets, headings, steps)
        
        Args:
            answer: Raw answer text
            query_type: Type of query (metric, entity, list, how_to, etc.)
            
        Returns:
            Formatted answer with structure
        """
        answer = answer.strip()
        
        # For list queries, ensure bullet points
        if query_type == 'list':
            answer = self._format_as_list(answer)
        
        # For how-to queries, ensure step-by-step format
        elif query_type == 'how_to':
            answer = self._format_as_steps(answer)
        
        # For metric queries, ensure clear format
        elif query_type == 'metric':
            answer = self._format_metric_answer(answer)
        
        # For entity queries, ensure structured format
        elif query_type == 'entity':
            answer = self._format_entity_answer(answer)
        
        # For comparison queries, ensure table-like format
        elif query_type == 'comparison':
            answer = self._format_comparison(answer)
        
        # General: Add structure if needed
        else:
            answer = self._add_structure_to_text(answer)
        
        return answer
    
    def _format_as_list(self, text: str) -> str:
        """Format text as a bulleted list"""
        # Check if already has bullets
        if re.search(r'^[\*\-\•]\s', text, re.MULTILINE):
            return text
        
        # Split by common list indicators
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if it's a numbered list item
            if re.match(r'^\d+[\.\)]\s', line):
                formatted_lines.append(f"• {line}")
            # Check if it contains "and" or commas (might be a list)
            elif ',' in line and ('and' in line.lower() or 'or' in line.lower()):
                items = re.split(r',\s*(?:and|or)\s*', line)
                for item in items:
                    item = item.strip()
                    if item:
                        formatted_lines.append(f"• {item}")
            else:
                formatted_lines.append(f"• {line}")
        
        return '\n'.join(formatted_lines) if formatted_lines else text
    
    def _format_as_steps(self, text: str) -> str:
        """Format text as step-by-step instructions"""
        # Check if already has steps
        if re.search(r'^(step|step \d+|1\.|2\.)', text.lower(), re.MULTILINE):
            return text
        
        # Split by sentences or common step indicators
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return text
        
        formatted = []
        step_num = 1
        for sentence in sentences:
            # Skip if it's too short or just a fragment
            if len(sentence) < 10:
                continue
            formatted.append(f"**Step {step_num}:** {sentence}")
            step_num += 1
        
        return '\n\n'.join(formatted) if formatted else text
    
    def _format_metric_answer(self, text: str) -> str:
        """Format metric answer with clear structure"""
        # If it's already in strict format, keep it
        if 'Answer:' in text and 'Source:' in text:
            return text
        
        # Extract key metric information
        # Look for patterns like "X%", "₹X", "X years"
        metric_patterns = [
            r'(\d+\.?\d*)\s*%',
            r'₹\s*([\d,]+)',
            r'(\d+)\s*(?:year|month|day)',
        ]
        
        # Try to format as: Metric: Value
        for pattern in metric_patterns:
            match = re.search(pattern, text)
            if match:
                # Format with emphasis
                formatted = re.sub(pattern, r'**\1**', text, count=1)
                return formatted
        
        return text
    
    def _format_entity_answer(self, text: str) -> str:
        """Format entity answer (names, roles, etc.)"""
        # Look for names (capitalized words)
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        matches = re.findall(name_pattern, text)
        
        if matches:
            # Format first name found with emphasis
            first_name = matches[0]
            text = text.replace(first_name, f"**{first_name}**", 1)
        
        return text
    
    def _format_comparison(self, text: str) -> str:
        """Format comparison answer as structured comparison"""
        # Look for comparison indicators
        if 'vs' in text.lower() or 'versus' in text.lower() or 'compare' in text.lower():
            # Try to extract comparison points
            lines = text.split('\n')
            formatted = []
            
            for line in lines:
                line = line.strip()
                if ':' in line:
                    # Format as key: value
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        formatted.append(f"**{parts[0].strip()}:** {parts[1].strip()}")
                    else:
                        formatted.append(line)
                else:
                    formatted.append(line)
            
            return '\n'.join(formatted)
        
        return text
    
    def _add_structure_to_text(self, text: str) -> str:
        """Add basic structure to any text"""
        # If text is long, add paragraphs
        if len(text) > 300:
            # Split by sentences
            sentences = re.split(r'([.!?]+)', text)
            if len(sentences) > 6:
                # Group into paragraphs
                para_sentences = []
                current_para = []
                
                for i in range(0, len(sentences), 2):
                    if i + 1 < len(sentences):
                        sentence = sentences[i] + sentences[i + 1]
                        current_para.append(sentence.strip())
                        
                        if len(current_para) >= 3:
                            para_sentences.append(' '.join(current_para))
                            current_para = []
                
                if current_para:
                    para_sentences.append(' '.join(current_para))
                
                return '\n\n'.join(para_sentences)
        
        return text
    
    def format_with_confidence(self, answer: str, confidence: str, source_info: Optional[Dict] = None) -> str:
        """
        Format answer with confidence indicator
        
        Args:
            answer: Answer text
            confidence: Confidence level (HIGH, MEDIUM, LOW)
            source_info: Optional source information
            
        Returns:
            Formatted answer with confidence indicator
        """
        confidence_indicators = {
            'HIGH': '✓',
            'MEDIUM': '~',
            'LOW': '?'
        }
        
        indicator = confidence_indicators.get(confidence, '')
        
        if indicator:
            answer = f"{indicator} {answer}"
        
        return answer

