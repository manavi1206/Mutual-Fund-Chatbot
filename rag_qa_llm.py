"""
RAG Q&A System with LLM support
Enhanced with response caching for performance
Strict factual assistant with authority-based metric extraction
"""
import re
import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from functools import lru_cache
from query_classifier import QueryClassifier
from conflict_detector import ConflictDetector
from clarification_handler import ClarificationHandler
from constants import (
    SCHEME_TAG_MAP, SCHEME_DISPLAY_NAMES, FIELD_DISPLAY_NAMES,
    DATE_FORMATS, OUTPUT_DATE_FORMAT, MAX_ANSWER_SENTENCES
)


class RAGQALLM:
    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None):
        """
        Initialize Q&A system with LLM
        
        Args:
            llm_provider: "openai", "gemini", or "local"
            api_key: API key for the provider (if needed)
        """
        self.llm_provider = llm_provider
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.llm = None
        
        # Initialize query classifier
        self.query_classifier = QueryClassifier()
        
        # Initialize conflict detector
        self.conflict_detector = ConflictDetector()
        
        # Initialize clarification handler
        self.clarification_handler = ClarificationHandler()
        
        # LLM response cache - will be replaced with enhanced cache
        # Keep for backward compatibility during migration
        self.response_cache = {}
        self.cache_max_size = 100  # Max cached responses
        
        # More specific advisory patterns - only flag actual advice requests
        self.advisory_keywords = [
            'should i', 'should you', 'should we', 'should one',
            'recommend', 'recommendation', 'advice', 'suggest', 'suggestion',
            'best fund', 'which fund should', 'which fund to', 'which fund is better',
            'buy or sell', 'should i invest', 'should i buy', 'should i sell',
            'what should i', 'what should you', 'what should we',
            'is it good to invest', 'is it safe to invest', 'is it worth investing'
        ]
        # Factual keywords that should NOT trigger advisory detection
        self.factual_keywords = [
            'what is', 'what are', 'how to', 'who', 'when', 'where',
            'explain', 'describe', 'tell me about', 'information about'
        ]
        self.educational_link = "https://www.amfiindia.com/investor/knowledge-center-info?zoneName=IntroductionMutualFunds"
        
        # Actual schemes we have information about (to prevent hallucination)
        self.actual_schemes = self._load_actual_schemes()
        
        # Riskometer data cache (scheme_name -> riskometer_level)
        self.riskometer_data = self._load_riskometer_data()
        
        # Chat context - track last mentioned scheme
        self.chat_context = {
            'last_scheme': None,  # Last scheme mentioned in conversation
            'last_scheme_tag': None  # Scheme tag (LARGE_CAP, FLEXI_CAP, etc.)
        }
        
        # Load source metadata for last_updated dates
        self.source_metadata = {}
        try:
            with open("data_raw/sources_loaded.json", "r", encoding="utf-8") as f:
                sources = json.load(f)
                for source in sources:
                    self.source_metadata[source['source_id']] = {
                        'last_fetched_date': source.get('last_fetched_date', ''),
                        'source_type': source.get('source_type', ''),
                        'source_url': source.get('source_url', '')
                    }
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not load source metadata: {e}")
    
    def _load_riskometer_data(self) -> Dict[str, str]:
        """Load riskometer data from overview pages"""
        import re
        riskometer_data = {}
        scheme_files = {
            "HDFC Large Cap Fund": "data_processed/amc_largecap_overview.txt",
            "HDFC Flexi Cap Fund": "data_processed/amc_flexicap_overview.txt",
            "HDFC TaxSaver (ELSS)": "data_processed/amc_elss_overview.txt",
            "HDFC Hybrid Equity Fund": "data_processed/amc_hybrid_overview.txt"
        }
        
        riskometer_levels = ["Very High", "Moderately High", "High", "Moderate", "Low to Moderate", "Low"]
        
        for scheme_name, file_path in scheme_files.items():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                
                # Look for "Riskometer" followed by a risk level
                pattern = r"Riskometer\s*[:\n]?\s*([^\n]+)"
                match = re.search(pattern, text, re.IGNORECASE)
                
                if match:
                    risk_text = match.group(1).strip()
                    # Check which level it matches
                    found_level = None
                    for level in riskometer_levels:
                        if level.lower() in risk_text.lower():
                            found_level = level
                            break
                    
                    if found_level:
                        riskometer_data[scheme_name] = found_level
            except Exception as e:
                print(f"Warning: Could not load riskometer for {scheme_name}: {e}")
        
        return riskometer_data
    
    def _load_actual_schemes(self) -> List[str]:
        """Load actual schemes from sources to prevent hallucination"""
        try:
            import json
            with open("data_raw/sources_loaded.json", "r", encoding="utf-8") as f:
                sources = json.load(f)
            
            schemes = set()
            scheme_name_map = {
                "LARGE_CAP": "HDFC Large Cap Fund",
                "FLEXI_CAP": "HDFC Flexi Cap Fund",
                "ELSS": "HDFC TaxSaver (ELSS)",
                "HYBRID": "HDFC Hybrid Equity Fund"
            }
            
            for source in sources:
                scheme_tag = source.get("scheme_tag", "")
                if scheme_tag and scheme_tag != "ALL":
                    scheme_name = scheme_name_map.get(scheme_tag, f"HDFC {scheme_tag.replace('_', ' ')} Fund")
                    schemes.add(scheme_name)
            
            return sorted(list(schemes))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not load schemes: {e}")
            return ["HDFC Large Cap Fund", "HDFC Flexi Cap Fund", "HDFC TaxSaver (ELSS)", "HDFC Hybrid Equity Fund"]
        
        # Initialize LLM if API key available
        if self.llm_provider == "openai" and self.api_key:
            self._init_openai()
        elif self.llm_provider == "gemini" and self.api_key:
            self._init_gemini()
        else:
            print("⚠️  No LLM API key found. Using template-based answers.")
    
    def _init_openai(self):
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=self.api_key)
            self.llm = "openai"
            print("✓ OpenAI LLM initialized")
        except ImportError:
            print("⚠️  openai package not installed")
        except Exception as e:
            print(f"⚠️  OpenAI initialization failed: {e}")
    
    def _init_gemini(self):
        try:
            import requests
            self.gemini_api_key = self.api_key
            # Use gemini-2.0-flash (fast and efficient)
            self.gemini_model = "gemini-2.0-flash"
            self.gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.api_key}"
            self.llm = "gemini"
            print(f"✓ Gemini LLM initialized (REST API) - Model: {self.gemini_model}")
        except Exception as e:
            print(f"⚠️  Gemini initialization failed: {e}")
    
    def is_advisory_question(self, query: str) -> bool:
        """Check if query asks for investment advice (improved detection)"""
        query_lower = query.lower()
        
        # If it starts with factual keywords, it's likely factual
        if any(query_lower.startswith(kw) for kw in self.factual_keywords):
            return False
        
        # Check for advisory patterns (must be more specific)
        has_advisory = any(keyword in query_lower for keyword in self.advisory_keywords)
        
        # Additional check: if query asks "what is X" or "what are Y", it's factual
        if query_lower.startswith(('what is', 'what are', 'how', 'who', 'when', 'where')):
            return False
        
        return has_advisory
    
    def _llm_clean_and_structure_answer(self, answer: str, original_query: str) -> str:
        """
        Use LLM intelligence to clean, structure, and concise the answer
        Much more robust than hardcoded regex patterns
        """
        # Check if answer has obvious noise indicators (even if short)
        noise_indicators = [
            'Source:', 'source:', 'amc_', 'factsheet', 'pdf', 'sid',
            'Home Learn', 'Skip to', 'min read', 'seconds read',
            'ng retained', 'equalisation reserve',  # Common broken text patterns
            '. 00', '0. ', '1. ',  # Poor number formatting
        ]
        has_noise = any(indicator in answer for indicator in noise_indicators)
        
        # Always clean if has noise, or if longer than 200 chars
        if not has_noise and len(answer) < 200:
            return answer
        
        # Use LLM to clean and structure
        cleaning_prompt = f"""You are a helpful assistant that cleans and structures answers about mutual funds.

RAW ANSWER (may contain navigation menus, source metadata, broken text):
{answer}

ORIGINAL QUESTION:
{original_query}

🚨 CRITICAL RULES - MUST FOLLOW:

1. **ONLY CLEAN, DON'T ADD**: 
   - Remove noise and fix formatting ONLY
   - DO NOT add information from your knowledge
   - DO NOT add links or URLs
   - DO NOT add explanations not in the original answer

2. **NO ADVICE**:
   - DO NOT add "you should", "I recommend", "consider"
   - Just present facts as they are

YOUR TASK:
Clean and structure this answer like GPT-4/Claude:

1. **Remove noise**:
   - Navigation elements (Home, Learn, Menu, Skip, breadcrumbs)
   - Source metadata ("Source: amc_factsheet", "factsheet_consolidated")
   - Reading time indicators ("2min read", "1min 58 seconds read")
   - Broken/incomplete sentences ("ng retained...")
   - Document references (PDF names, file references)

2. **Fix formatting**:
   - Numbers: "1. 00" → "1.00%" or "1%" or "No exit load"
   - Lists: Use bullet points (•) or numbered lists where appropriate
   - Emphasis: Use **bold** for key terms
   - Spacing: Add line breaks for readability

3. **Structure properly**:
   - Start with direct answer
   - Add relevant details from the answer
   - Use paragraphs/bullets for organization
   - Be comprehensive yet clear

4. **Preserve facts** (CRITICAL):
   - Keep all numbers, percentages, dates exactly as given
   - Keep conditions and qualifications
   - Keep complete, accurate information
   - DO NOT add information not in the original answer

5. **Professional tone**:
   - Clear and helpful
   - Complete sentences only
   - Natural flow
   - Facts only, no advice

CLEANED ANSWER (using ONLY information from the answer above):"""

        try:
            if self.llm:
                # Use the LLM to clean the answer
                cleaned = self.llm.invoke(cleaning_prompt).content.strip()
                
                # Basic validation - make sure we got a reasonable response
                if len(cleaned) > 20 and len(cleaned) < 1000:
                    return cleaned
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"LLM cleaning failed: {e}, using fallback")
        
        # Fallback: basic cleaning if LLM fails
        return self._fallback_summarize(answer)
    
    def _fallback_summarize(self, answer: str) -> str:
        """Fallback cleaning if LLM fails - minimal processing, no truncation"""
        # Remove obvious noise patterns only
        answer = re.sub(r'Source:\s*\w+', '', answer)
        answer = re.sub(r'amc_\w+', '', answer)
        answer = re.sub(r'factsheet[_\w]*', '', answer)
        answer = re.sub(r'\(factsheet[^)]*\)', '', answer)
        answer = re.sub(r'ng retained[^.]*', '', answer)
        answer = re.sub(r'equalisation reserve[^.]*', '', answer)
        
        # Fix number formatting
        answer = re.sub(r'(\d+)\.\s+(\d+)', r'\1.\2', answer)  # "1. 00" → "1.00"
        
        # Clean up sentences but keep all content (no truncation)
        sentences = re.split(r'[.!?]+', answer)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 15]
        
        # Remove sentences with obvious noise but keep all factual content
        result = []
        for sent in sentences:
            # Skip obvious noise
            noise_words = ['home', 'menu', 'skip', 'learn', 'download', 'click']
            if any(noise in sent.lower() for noise in noise_words):
                continue
            result.append(sent)
        
        if result:
            return '. '.join(result) + '.'
        return answer.strip()
    
    def _summarize_answer(self, answer: str, query_type: str = 'general') -> str:
        """
        Minimal fallback - main formatting handled by LLM in format_answer
        No artificial length limits - let content determine structure
        """
        # For clarifications and refusals, return as-is
        if query_type in ['clarification', 'refusal']:
            return answer
        
        # For everything else, let LLM handle formatting (no truncation)
        return answer
    
    def format_answer(self, answer: str, source_url: str, query_type: str = 'general', refused: bool = False, original_query: str = None) -> str:
        """Format answer with citation and timestamp (preserves markdown)"""
        # If answer is empty, return early with just timestamp
        if not answer or not answer.strip():
            from datetime import datetime
            today = datetime.now()
            formatted_date = today.strftime(OUTPUT_DATE_FORMAT)
            return f"Last updated from sources: {formatted_date}."
        
        answer = answer.strip()
        
        # USE LLM INTELLIGENCE to clean and structure answer (not hardcoded patterns)
        # This is much more robust and handles ANY type of noise
        # Check if answer has noise even if short
        noise_indicators = [
            'Source:', 'source:', 'amc_', 'factsheet', 'pdf', 'sid',
            'Home Learn', 'Skip to', 'min read', 'seconds read',
            'ng retained', 'equalisation reserve',
            '. 00', '0. ', '1. ',  # Poor number formatting
        ]
        has_noise = any(indicator in answer for indicator in noise_indicators)
        
        # Clean if: has original query AND (has noise OR needs formatting) AND not clarification/refusal
        # Let LLM handle ALL formatting and structure - no artificial limits
        if original_query and query_type not in ['clarification', 'refusal']:
            if has_noise or len(answer) > 200:
                # Use LLM to clean and structure naturally (no length limits)
                answer = self._llm_clean_and_structure_answer(answer, original_query)
        
        # No truncation! Let the LLM provide complete, well-structured answers
        # The LLM prompt ensures proper formatting without artificial length constraints
        
        # Add citation only if not refused and source_url available
        # Don't add as markdown link - frontend handles this separately
        # if source_url and not refused:
        #     answer += f"\n\n[Source]({source_url})"
        
        # Add timestamp with proper format (from constants)
        from datetime import datetime
        today = datetime.now()
        formatted_date = today.strftime(OUTPUT_DATE_FORMAT)
        
        # Add timestamp at the end, on a new line if markdown is present
        if any(marker in answer for marker in ['**', '##', '- ', '* ', '1. ', '2. ', '3. ']):
            answer += f"\n\n*Last updated: {formatted_date}*"
        else:
            answer += f" Last updated from sources: {formatted_date}."
        
        return answer
    
    def _format_date(self, date_str: str) -> str:
        """Format date string to 'DD MMM, YYYY' format (e.g., '17 Nov, 2025')"""
        if not date_str or date_str == '.' or date_str.strip() == '':
            from datetime import datetime
            return datetime.now().strftime(OUTPUT_DATE_FORMAT)
        
        try:
            from datetime import datetime
            
            # Try different date formats (from constants)
            for fmt in DATE_FORMATS:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime(OUTPUT_DATE_FORMAT)
                except ValueError:
                    continue
            
            # If no format matches, return current date
            return datetime.now().strftime(OUTPUT_DATE_FORMAT)
        except Exception:
            from datetime import datetime
            return datetime.now().strftime(OUTPUT_DATE_FORMAT)
    
    def _get_cache_key(self, query: str, context: str) -> str:
        """Generate cache key from query and context (first 500 chars)"""
        # Use query + context preview for cache key
        context_preview = context[:500]  # First 500 chars
        cache_string = f"{query}|||{context_preview}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _generate_with_llm(self, query: str, context: str, use_cache: bool = True) -> str:
        """Generate answer using LLM (with caching)"""
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(query, context)
            if cache_key in self.response_cache:
                return self.response_cache[cache_key]
        
        # Generate answer
        if self.llm == "openai":
            answer = self._generate_openai(query, context)
        elif self.llm == "gemini":
            answer = self._generate_gemini(query, context)
        else:
            answer = self._extract_answer_from_context(query, context)
        
        # Cache answer
        if use_cache:
            if len(self.response_cache) >= self.cache_max_size:
                # Remove oldest (simple FIFO)
                oldest_key = next(iter(self.response_cache))
                del self.response_cache[oldest_key]
            self.response_cache[cache_key] = answer
        
        return answer
    
    def _generate_openai(self, query: str, context: str) -> str:
        """Generate answer using OpenAI"""
        try:
            prompt = f"""You are a FACTS-ONLY assistant for mutual fund information.

🚨 CRITICAL RULES:
1. Answer using ONLY the provided context below
2. DO NOT use your pre-trained knowledge
3. DO NOT add links or create URLs
4. DO NOT provide investment advice or recommendations
5. State facts only: report what IS, not what SHOULD BE

Context: {context}

Question: {query}

Answer (using ONLY the context above):"""
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI error: {e}")
            return self._extract_answer_from_context(query, context)
    
    def _get_prompt_for_query_type(self, query: str, query_type: str, context: str) -> str:
        """Get specialized prompt based on query type with examples"""
        
        # Get actual schemes list for this query type
        schemes_list = ", ".join(self.actual_schemes)
        
        base_instructions = f"""You are a FACTS-ONLY assistant for mutual fund information. Provide CLEAN answers from the context.

🚨 CRITICAL RULES - MUST FOLLOW:

1. **USE ONLY CONTEXT**: Answer using ONLY information from the provided context below
   - DO NOT use your pre-trained knowledge
   - DO NOT add information from your training data
   - If not in context, say "This information is not available in my sources"

2. **NO EXTERNAL LINKS/SOURCES**: 
   - DO NOT create any URLs or web links
   - DO NOT mention external sources unless explicitly in the context
   - Sources will be added separately by the system

3. **NO ADVICE**: 
   - DO NOT say "you should", "I recommend", "consider", "it's better to"
   - Only state facts: "The expense ratio is X%" not "This is a good expense ratio"
   - DO NOT suggest which fund to buy/sell

4. **FACTS ONLY**: State what IS, not what SHOULD BE

5. **SCHEMES AVAILABLE**: I only have information about these 4 HDFC schemes: {schemes_list}

6. **REMOVE NOISE**: DO NOT include SEBI circulars, document dates, PDF names, "Downloads", metadata, "Last Position Held", "As of [date]"

7. **FORMAT WITH MARKDOWN**:
   - **Bold** for fund names, numbers, key terms
   - Numbered lists (1. 2. 3.) for steps
   - Bullet points (-) for lists
   - Clean, readable structure

AVAILABLE SCHEMES (ONLY these 4):
{chr(10).join(f"- {s}" for s in self.actual_schemes)}

If asked "what funds do you have information about" or similar, ONLY list the schemes above."""
        
        examples = {
            'entity': """
EXAMPLE (Entity Query):
Question: Who manages the HDFC Large Cap Fund?
Context: "The Fund Manager of the Scheme is Mr. Roshi Jain. He has been managing the scheme since 2020."
Answer: The **Fund Manager** of **HDFC Large Cap Fund** is **Mr. Roshi Jain**, managing since **2020**.

IMPORTANT FOR ENTITY QUERIES:
- Extract ONLY the person's name and role
- DO NOT include: Exit Load, Holdings, Downloads, PDF names, dates, metadata
- Format: "The **Fund Manager** of **[Fund Name]** is **[Name]**."
- Keep it to 1-2 sentences maximum
""",
            'metric': """
EXAMPLE (Metric Query):
Question: What is the expense ratio of HDFC Large Cap Fund?
Context: "The Total Expense Ratio (TER) of the scheme is 0.97% per annum."
Answer: The **Total Expense Ratio (TER)** for **HDFC Large Cap Fund** is **0.97%** per annum.

IMPORTANT FOR METRIC QUERIES:
- Extract the exact number with unit (%, ₹, etc.)
- Format: "The **[Metric Name]** for **[Fund Name]** is **[Value]**."
- Keep to 1 sentence - just the fact
- DO NOT include dates, sources, or extra context
""",
            'list': """
EXAMPLE (List Query):
Question: What are the top holdings in HDFC ELSS?
Context: "Top 10 holdings: Reliance Industries (5.2%), Infosys (4.8%), HDFC Bank (4.5%)..."
Answer: The top holdings in **HDFC ELSS** are:

- **Reliance Industries** - 5.2%
- **Infosys** - 4.8%
- **HDFC Bank** - 4.5%

For list queries, extract:
- Use bullet points (-) for lists
- Bold the item names and include percentages/amounts
- List top 3-5 items unless more are specifically requested
- Format each item on a new line
""",
            'how_to': """
EXAMPLE (How-To Query):
Question: How do I redeem my HDFC Large Cap Fund units?
Context: "To redeem units, submit a redemption request before 3 PM on any business day. The proceeds will be credited within 3-5 business days."
Answer: To redeem your **HDFC Large Cap Fund** units, follow these steps:

1. **Log in** to your account on the AMC website or distributor platform (like Groww)
2. Navigate to the **'Redeem'** or **'Withdraw'** section and select the fund
3. Enter the number of units or amount you want to redeem
4. **Submit** the redemption request **before 3 PM** on any business day
5. The proceeds will be credited to your registered bank account within **3-5 business days**

**Important:** Redemption requests submitted after 3 PM will be processed on the next business day.

IMPORTANT FOR HOW-TO QUERIES:
- Use numbered lists (1. 2. 3.) for steps
- **Bold** important actions, deadlines, and key info
- Keep steps clear and actionable
- DO NOT include: document names, PDFs, dates, metadata, fund descriptions
- Focus ONLY on the actual steps to complete the action
""",
            'general': """
EXAMPLE (General Query):
Question: What is the investment strategy of HDFC Hybrid Equity Fund?
Context: "HDFC Hybrid Equity Fund is an open ended hybrid scheme investing predominantly in equity and equity related instruments. The equity and debt assets of the Scheme would be managed as per the respective strategies as given below: Equity 65-80% of the portfolio will be invested in equity..."
Answer: The **investment strategy** of **HDFC Hybrid Equity Fund** is:

**Equity Allocation:**
- **65-80%** of the portfolio will be invested in equity and equity-related instruments
- Focus on quality companies with strong fundamentals

**Debt Allocation:**
- Remaining portion in debt instruments for stability

**Overall Approach:**
- Hybrid strategy balancing growth (equity) and stability (debt)
- Active management based on market conditions

IMPORTANT FOR GENERAL QUERIES:
- Use **bold** for fund names, key terms, and important numbers
- Break information into clear sections with headings or bullet points
- Use proper paragraph breaks for readability
- Ensure the answer is COMPLETE - don't cut off mid-sentence
- If the answer seems incomplete, continue with relevant information from context
- Make it visually structured and easy to scan
- DO NOT include: page titles, navigation elements, document metadata
"""
        }
        
        example_text = examples.get(query_type, examples['general'])
        
        # For queries about available funds, add explicit scheme list to context
        query_lower = query.lower()
        if any(phrase in query_lower for phrase in ["what funds", "which funds", "what schemes", "which schemes", "have information about", "available"]):
            schemes_context = f"\n\nIMPORTANT: I only have information about these 4 HDFC schemes: {', '.join(self.actual_schemes)}. Do NOT mention any other funds."
        else:
            schemes_context = ""
        
        # Phase 2: Improved prompt with better instructions for LLM filtering (optimized for token usage)
        context_instructions = """CONTEXT FILTERING:
- Context has multiple chunks separated by "---"
- IGNORE: SEBI circulars, PDF names, dates, "Downloads", "Last Position Held", page numbers
- IGNORE: Page titles like "NAV, Portfolio and Performance", "Direct Growth", navigation elements
- EXTRACT: Only factual information relevant to the question
- If multiple values: Prefer SID > KIM > Factsheet (most authoritative)
- Focus on core facts, ignore document structure
- Ensure answer is COMPLETE - don't cut off mid-sentence"""
        
        # Phase 2: Optimize token usage - truncate context intelligently
        # Keep full context but ensure we don't exceed reasonable limits
        context_to_use = context[:10000]  # 10K chars = ~2500 tokens (reasonable for GPT-3.5/Gemini)
        
        # Add specific instruction for strategy queries
        strategy_instruction = ""
        scheme_name, _ = self._extract_scheme_from_query(query)
        if any(phrase in query.lower() for phrase in ['investment strategy', 'strategy', 'investment approach']) and scheme_name:
            strategy_instruction = f"\n\nIMPORTANT: The question is about **{scheme_name}**. Make sure your answer is specifically about this fund, not other funds. Extract the investment strategy, asset allocation, and investment approach for {scheme_name} only."
        
        return f"""{base_instructions}
{example_text}
{schemes_context}
{context_instructions}
{strategy_instruction}

Context (chunks separated by "---"):
{context_to_use}

Question: {query}

Answer (from context only, filter metadata, factual, COMPLETE - ensure full sentences):"""
    
    def _generate_gemini(self, query: str, context: str) -> str:
        """Generate answer using Gemini REST API with query-type-specific prompts"""
        try:
            import requests
            query_type = self.query_classifier.classify(query)
            prompt = self._get_prompt_for_query_type(query, query_type, context)
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(self.gemini_api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    answer = data['candidates'][0]['content']['parts'][0]['text']
                    return answer.strip()
                else:
                    raise Exception("No candidates in response")
            else:
                raise Exception(f"API returned status {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            print(f"Gemini error: {e}")
            return self._extract_answer_from_context(query, context)
    
    def _rephrase_metric_answer(self, query: str, extracted_fact: str, context: str, scheme_name: Optional[str] = None) -> str:
        """Rephrase extracted metric answer naturally using LLM while preserving accuracy"""
        if not self.llm:
            # No LLM available, return original with basic formatting
            return extracted_fact
        
        # Build rephrasing prompt
        scheme_display = scheme_name or "the fund"
        prompt = f"""You are a helpful assistant. Rephrase this factual answer naturally and beautifully while keeping the exact information 100% accurate.

Original extracted fact: {extracted_fact}
User question: {query}
Fund name: {scheme_display}

Rephrase the answer to be:
- Natural and conversational (like talking to a friend)
- Well-formatted with markdown (**bold** for key terms, numbers, and fund names)
- Concise (1-2 sentences maximum)
- Keep the EXACT value and fund name accurate - do not change any numbers or names
- Make it sound professional yet friendly

Example transformations:
- "The minimum sip for HDFC Large Cap Fund is ₹100." → "The **minimum SIP** amount for **HDFC Large Cap Fund** is **₹100**."
- "The exit load for the fund is 1.00%." → "**HDFC Large Cap Fund** has an **exit load of 1.00%**."

Rephrased answer (keep it concise and natural):"""
        
        try:
            if self.llm == "gemini":
                import requests
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
                response = requests.post(self.gemini_api_url, json=payload, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if 'candidates' in data and len(data['candidates']) > 0:
                        rephrased = data['candidates'][0]['content']['parts'][0]['text'].strip()
                        # Validate that the rephrased answer contains the key value
                        # Extract value from original fact
                        value_pattern = r'(\d+[.,]?\d*%?|₹\d+)'
                        original_value = re.search(value_pattern, extracted_fact)
                        if original_value and original_value.group(1) in rephrased:
                            return rephrased
                        else:
                            # LLM changed the value, return original
                            return extracted_fact
                return extracted_fact
            elif self.llm == "openai":
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.3
                )
                rephrased = response.choices[0].message.content.strip()
                # Validate value is preserved
                value_pattern = r'(\d+[.,]?\d*%?|₹\d+)'
                original_value = re.search(value_pattern, extracted_fact)
                if original_value and original_value.group(1) in rephrased:
                    return rephrased
                else:
                    return extracted_fact
            else:
                return extracted_fact
        except Exception as e:
            print(f"Rephrasing error: {e}")
            # On error, return original fact
            return extracted_fact
    
    def _extract_answer_from_context(self, query: str, context: str) -> str:
        """Fallback: Extract relevant answer from context"""
        query_lower = query.lower()
        sentences = re.split(r'[.!?]+', context)
        relevant_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            query_words = set(query_lower.split())
            sentence_words = set(sentence_lower.split())
            overlap = len(query_words & sentence_words)
            
            if overlap >= 2 or any(word in sentence_lower for word in query_words if len(word) > 4):
                relevant_sentences.append(sentence.strip())
        
        if relevant_sentences:
            answer = '. '.join(relevant_sentences[:3])
            if not answer.endswith('.'):
                answer += '.'
            return answer
        
        return context[:200] + "..." if len(context) > 200 else context
    
    def _split_multiple_questions(self, query: str) -> List[str]:
        """Detect and split multiple questions in a single query - IMPROVED"""
        # Common question separators and patterns
        # Pattern 1: Explicit separators
        separators = [
            r'\s+and\s+',  # "what is X and what is Y"
            r'\s+also\s+',  # "what is X also what is Y"
            r'\s+what about\s+',  # "what is X what about Y"
            r'\s+tell me about\s+',  # "what is X tell me about Y"
            r'\s+,\s+',  # "what is X, what is Y"
            r'\?\s+',  # "what is X? what is Y"
        ]
        
        # Pattern 2: Question word patterns (what, how, who, etc.)
        question_patterns = [
            r'(?:what|how|who|when|where|which|why)\s+[^?]+?\?',  # "What is X? How do I Y?"
        ]
        
        questions = [query]
        
        # First, try to split by question marks (multiple ?)
        if query.count('?') > 1:
            parts = re.split(r'\s*\?\s*', query)
            parts = [p.strip() + '?' if p.strip() and not p.strip().endswith('?') else p.strip() for p in parts if p.strip()]
            if len(parts) > 1:
                questions = parts
        
        # Then try separators
        for sep in separators:
            new_questions = []
            for q in questions:
                if re.search(sep, q, re.IGNORECASE):
                    parts = re.split(sep, q, flags=re.IGNORECASE)
                    new_questions.extend([p.strip() for p in parts if p.strip()])
                else:
                    new_questions.append(q)
            questions = new_questions
        
        # Try question word patterns
        for pattern in question_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if len(matches) > 1:
                questions = matches
                break
        
        # Clean up questions
        cleaned_questions = []
        for q in questions:
            q = q.strip()
            # Remove leading/trailing punctuation artifacts
            q = re.sub(r'^[,\s]+', '', q)
            q = re.sub(r'[,\s]+$', '', q)
            # Ensure question ends with ? if it's a question
            if any(word in q.lower() for word in ['what', 'how', 'who', 'when', 'where', 'which', 'why']) and not q.endswith('?'):
                q += '?'
            # Filter out very short fragments
            if len(q) > 10:
                cleaned_questions.append(q)
        
        # If we have multiple questions, return them
        if len(cleaned_questions) > 1:
            return cleaned_questions
        return [query]
    
    def _llm_generate_factual_answer(self, query: str, chunks: List[Dict], query_understanding: Dict) -> str:
        """
        Use LLM to generate a clean, factual answer from retrieved chunks
        This is the MAIN answer generation using LLM intelligence
        """
        # Prepare context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks[:5], 1):  # Top 5 chunks
            text = chunk.get('text', '')[:500]  # Limit chunk size
            context_parts.append(f"[Source {i}]: {text}")
        
        context = "\n\n".join(context_parts)
        
        # Detect if this is a simple metric query (needs direct, 1-sentence answer)
        metric = query_understanding.get('metric', 'general')
        simple_metrics = ['expense_ratio', 'exit_load', 'minimum_sip', 'nav', 'lock_in', 'fund_manager']
        is_simple_metric = metric in simple_metrics
        
        # Build comprehensive prompt
        if is_simple_metric:
            # For simple metrics: VERY DIRECT, 1-sentence answer only
            generation_prompt = f"""You are a FACTS-ONLY assistant providing information about HDFC mutual funds.

USER QUESTION: "{query}"

RETRIEVED INFORMATION FROM OFFICIAL SOURCES:
{context}

QUERY ANALYSIS:
- Intent: {query_understanding.get('intent', 'fact_lookup')}
- Fund: {query_understanding.get('fund_mentioned', 'Not specified')}
- Metric: {metric}

🚨 CRITICAL RULES FOR SIMPLE METRIC QUERIES:

1. **ANSWER ONLY THE SPECIFIC QUESTION**: Extract ONLY the {metric} from the context
   - DO NOT add information about other topics (investment strategy, lump sum, other metrics)
   - DO NOT include background or explanations unless specifically asked
   - ONE direct sentence is enough

2. **USE ONLY RETRIEVED INFORMATION**: 
   - Extract from the context above only
   - If not found, say "This information is not available"

3. **FORMAT PROPERLY**:
   - Use ₹ symbol for amounts (e.g., "₹100" not "100")
   - Use % for percentages (e.g., "0.82%" not "0.82")
   - Use proper units

4. **BE DIRECT**:
   - Template: "The {metric} for [Fund Name] is [Value]."
   - Example: "The minimum SIP amount for HDFC Hybrid Equity Fund is ₹100 per month."
   - Example: "The expense ratio for HDFC Large Cap Fund is 0.82%."

5. **NO EXTRA INFO**: Do not mention lump sum, strategy, holdings, or anything not asked

ANSWER (ONE clear, direct sentence):"""
        else:
            # For complex queries: can be more detailed
            generation_prompt = f"""You are a FACTS-ONLY assistant providing information about HDFC mutual funds.

USER QUESTION: "{query}"

RETRIEVED INFORMATION FROM OFFICIAL SOURCES:
{context}

QUERY ANALYSIS:
- Intent: {query_understanding.get('intent', 'fact_lookup')}
- Fund: {query_understanding.get('fund_mentioned', 'Not specified')}
- Metric: {query_understanding.get('metric', 'general')}

🚨 CRITICAL RULES - MUST FOLLOW:

1. **USE ONLY RETRIEVED INFORMATION**: Answer ONLY using the information in "RETRIEVED INFORMATION" above
   - DO NOT use your pre-trained knowledge
   - DO NOT add information from your training data
   - If information is not in retrieved sources, say "This information is not available in the sources"

2. **NO MADE-UP LINKS OR SOURCES**: 
   - DO NOT create any URLs or links
   - DO NOT mention sources like "according to SEBI" unless it's explicitly in the retrieved text
   - Sources will be added separately by the system

3. **NO ADVICE OR RECOMMENDATIONS**:
   - DO NOT say "you should", "I recommend", "consider", "it's better to"
   - Only state facts: "The expense ratio is X%" not "This is a good expense ratio"
   - DO NOT suggest which fund to buy/sell

4. **FACTS ONLY**:
   - State what IS, not what SHOULD BE
   - Report numbers, dates, processes as documented
   - No opinions, predictions, or suggestions

5. **ANSWER WHAT WAS ASKED**:
   - Focus on the specific question
   - Don't add unrelated information just because it's in the context
   - Be comprehensive for the topic asked, but stay on topic

FORMATTING TASK:
Answer like GPT-4/Claude with proper structure:

✅ **Structure**: Use paragraphs, bullet points, numbered lists where appropriate
✅ **Clarity**: Start with direct answer, then provide relevant details
✅ **Formatting**: Use **bold** for emphasis, bullets (•) for lists, line breaks for readability
✅ **Accuracy**: Cite specific numbers, percentages, dates exactly as given in sources
✅ **Relevance**: Include only information that answers the question
✅ **Clean**: Remove navigation, broken text, document metadata

❌ **Don't**: Add external knowledge, create links, give advice, make recommendations, include unrelated info

ANSWER (using ONLY the retrieved information):"""

        try:
            if self.llm:
                answer = self.llm.invoke(generation_prompt).content.strip()
                return answer
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"LLM answer generation failed: {e}")
        
        # Fallback: extract from first chunk
        if chunks:
            return chunks[0].get('text', "I couldn't find specific information.")[:300]
        return "I couldn't find specific information in my sources."
    
    def _llm_understand_query(self, query: str, conversation_context: Optional[Dict] = None) -> Dict:
        """
        Use LLM to deeply understand the user's query
        Returns: intent, entities, fund_mentioned, is_factual_question, etc.
        """
        context_summary = ""
        if conversation_context:
            last_fund = conversation_context.get('entities', {}).get('last_fund', '')
            if last_fund:
                context_summary = f"\nContext: User previously asked about {last_fund}"
        
        understanding_prompt = f"""Analyze this user query about mutual funds.

USER QUERY: "{query}"{context_summary}

Determine:
1. INTENT: What is the user asking? (fact_lookup, comparison, advice, process, general_info, off_topic)
2. FUND_MENTIONED: Which HDFC fund are they asking about? (Large Cap, Flexi Cap, ELSS/TaxSaver, Hybrid, or None)
3. METRIC: What specific metric? (expense_ratio, exit_load, minimum_sip, riskometer, benchmark, fund_manager, returns, nav, holdings, lock_in, or general)
4. IS_FACTUAL: Is this a factual question (yes) or advice request (no)?
5. NEEDS_CLARIFICATION: If they didn't mention a fund but asking about specific metric, do we need to ask which fund? (yes/no)
6. EXPANDED_QUERY: If context suggests they mean a specific fund, what's the full query?

Respond in JSON:
{{
  "intent": "fact_lookup|comparison|advice|process|off_topic",
  "fund_mentioned": "Large Cap|Flexi Cap|ELSS|Hybrid|None",
  "metric": "expense_ratio|exit_load|...|general",
  "is_factual": true|false,
  "needs_clarification": true|false,
  "expanded_query": "full query with context",
  "reasoning": "brief explanation"
}}"""

        try:
            if self.llm:
                response = self.llm.invoke(understanding_prompt).content.strip()
                # Extract JSON from response
                import json
                # Try to find JSON in response
                if '{' in response:
                    json_start = response.index('{')
                    json_end = response.rindex('}') + 1
                    json_str = response[json_start:json_end]
                    understanding = json.loads(json_str)
                    return understanding
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"LLM query understanding failed: {e}")
        
        # Fallback: basic heuristics
        return {
            "intent": "fact_lookup",
            "fund_mentioned": "None",
            "metric": "general",
            "is_factual": True,
            "needs_clarification": False,
            "expanded_query": query,
            "reasoning": "Fallback heuristic"
        }
    
    def generate_answer(self, query: str, chunks: List[Dict], 
                       conversation_context: Optional[Dict] = None,
                       response_style: str = "default") -> Dict:
        """Generate answer from retrieved chunks using LLM-first approach"""
        
        # STEP 1: USE LLM TO UNDERSTAND THE QUERY
        # This is the PRIMARY intelligence - LLM analyzes intent, entities, context
        query_understanding = self._llm_understand_query(query, conversation_context)
        
        # STEP 2: HANDLE BASED ON LLM'S UNDERSTANDING
        # If LLM detected advice-seeking or off-topic, decline early
        if not query_understanding.get('is_factual', True):
            return {
                'answer': "I only provide factual information about HDFC mutual funds, not investment advice. I can't recommend whether you should invest or not.\n\nFor investment advice tailored to your financial situation and goals, please consult a SEBI-registered financial advisor.\n\nLearn more about mutual funds: [AMFI Investor Education](https://www.amfiindia.com/investor/knowledge-center-info?zoneName=IntroductionMutualFunds)",
                'source_url': None,
                'refused': True,
                'query_type': 'advisory'
            }
        
        if query_understanding.get('intent') == 'off_topic':
            return {
                'answer': "I only provide information about HDFC Mutual Funds. I don't have information about that topic. Please ask me about HDFC schemes, expense ratios, exit loads, fund managers, or other mutual fund-related questions.",
                'source_url': None,
                'refused': True,
                'query_type': 'general'
            }
        
        # STEP 3: USE LLM'S EXPANDED QUERY (with context applied)
        enhanced_query = query_understanding.get('expanded_query', query)
        
        query_lower = query.lower()
        
        # Legacy fallback checks (keeping for safety, but LLM should handle most)
        unrelated_patterns = [
            r'president\s+of\s+(india|usa|america|united\s+states|us|u\.s\.)',
            r'prime\s+minister\s+of',
            r'capital\s+of\s+(india|delhi|mumbai|bangalore)',
            r'who\s+is\s+(?:the\s+)?(president|prime\s+minister|ceo)\s+of',
            r'weather\s+in',
            r'news\s+about',
            r'sports\s+(score|match|game)',
            r'(movie|film)\s+(review|rating)',
            r'recipe\s+for',
        ]
        
        is_unrelated = False
        for pattern in unrelated_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                is_unrelated = True
                break
        
        # Also check for "who is the X" where X is not fund-related
        if re.search(r'who\s+is\s+(?:the\s+)?(\w+)', query_lower):
            match = re.search(r'who\s+is\s+(?:the\s+)?(\w+)', query_lower)
            if match:
                word_after = match.group(1).lower()
                mf_roles = ['manager', 'fund', 'portfolio', 'investment']
                unrelated_roles = ['president', 'prime', 'minister', 'ceo', 'king', 'queen', 'leader']
                # If it's an unrelated role OR if query has "of" and word is not MF-related
                if word_after in unrelated_roles:
                    is_unrelated = True
                elif 'of' in query_lower and word_after not in mf_roles:
                    # "who is the X of Y" where X is not fund-related
                    is_unrelated = True
        
        # Check if query is about mutual funds at all
        mf_keywords = ['mutual fund', 'fund', 'scheme', 'hdfc', 'elss', 'sip', 'nav', 'expense ratio', 
                       'exit load', 'redemption', 'investment', 'portfolio', 'manager', 'benchmark', 
                       'riskometer', 'lock-in', 'lockin', 'minimum', 'allotment', 'units', 'groww']
        is_about_mf = any(kw in query_lower for kw in mf_keywords)
        
        if is_unrelated and not is_about_mf:
            return {
                'answer': "I only provide information about HDFC Mutual Funds. I don't have information about that topic. Please ask me about HDFC schemes, expense ratios, exit loads, fund managers, or other mutual fund-related questions.",
                'source_url': None,
                'refused': True,
                'query_type': 'general'
            }
        
        # Check if clarification is needed
        needs_clarification, clarification_question = self.clarification_handler.needs_clarification(
            query, conversation_context
        )
        
        if needs_clarification and clarification_question:
            return {
                'answer': clarification_question,
                'source_url': None,
                'refused': False,
                'needs_clarification': True,
                'query_type': 'clarification'
            }
        
        # Check for multiple questions - IMPROVED HANDLING
        questions = self._split_multiple_questions(query)
        if len(questions) > 1:
            # Handle multiple questions - retrieve chunks for each question separately
            from rag_retriever import RAGRetriever
            retriever = RAGRetriever()
            
            answers = []
            all_source_urls = []
            for q in questions:
                # Retrieve chunks specific to this question
                q_chunks = retriever.retrieve(q, top_k=5)
                q_result = self._generate_single_answer(q, q_chunks)
                if q_result and not q_result.get('refused', False):
                    # Remove the date/source from individual answers to avoid duplication
                    clean_answer = q_result['answer']
                    clean_answer = re.sub(r'\s+Last updated from sources:.*?\.', '', clean_answer)
                    clean_answer = re.sub(r'\s+Last updated:.*?\.', '', clean_answer)
                    clean_answer = re.sub(r'\s+\[Source\]\([^)]+\)', '', clean_answer)
                    clean_answer = re.sub(r'\*Last updated:.*?\*', '', clean_answer)
                    # Format as question-answer pair with better separation
                    answers.append(f"### {q}\n\n{clean_answer}")
                    if q_result.get('source_url'):
                        all_source_urls.append(q_result['source_url'])
            
            if answers:
                combined_answer = "\n\n---\n\n".join(answers)  # Better separator
                # Add single source citation and date at the end
                primary_source = all_source_urls[0] if all_source_urls else (chunks[0].get('source_url', '') if chunks else None)
                combined_answer = self.format_answer(combined_answer, primary_source, 'general', refused=False, original_query=query)
                return {
                    'answer': combined_answer,
                    'source_url': primary_source,
                    'refused': False,
                    'query_type': 'general'
                }
        
        # Single question - proceed normally
        result = self._generate_single_answer(query, chunks)
        
        # Apply response style if specified
        if response_style != "default" and result.get('answer'):
            result['answer'] = self._apply_response_style(result['answer'], response_style, result.get('query_type', 'general'))
        
        # Add follow-up suggestions
        followups = self.clarification_handler.suggest_followups(query, result.get('answer', ''), chunks)
        if followups:
            result['suggested_followups'] = followups
        
        return result
    
    def _extract_scheme_from_query(self, query: str) -> tuple:
        """Extract scheme name and tag from query"""
        query_lower = query.lower()
        
        # Map scheme keywords to scheme names and tags
        scheme_keywords = {
            "large cap": ("HDFC Large Cap Fund", "LARGE_CAP"),
            "flexi cap": ("HDFC Flexi Cap Fund", "FLEXI_CAP"),
            "flexicap": ("HDFC Flexi Cap Fund", "FLEXI_CAP"),
            "elss": ("HDFC TaxSaver (ELSS)", "ELSS"),
            "taxsaver": ("HDFC TaxSaver (ELSS)", "ELSS"),
            "tax saver": ("HDFC TaxSaver (ELSS)", "ELSS"),
            "hybrid": ("HDFC Hybrid Equity Fund", "HYBRID"),
            "hybrid equity": ("HDFC Hybrid Equity Fund", "HYBRID"),
        }
        
        for keyword, (scheme_name, scheme_tag) in scheme_keywords.items():
            if keyword in query_lower:
                return scheme_name, scheme_tag
        
        return None, None
    
    def _generate_single_answer(self, query: str, chunks: List[Dict]) -> Dict:
        """Generate answer for a single question"""
        query_lower = query.lower()
        refused = False
        
        # FIRST: Handle riskometer definition queries (before any other checks)
        if any(phrase in query_lower for phrase in ["what is riskometer", "definition of riskometer", "what exactly is the definition of riskometer", "what is the riskometer"]):
            definition_answer = (
                "The **Riskometer** is a standardized risk measurement scale introduced by **SEBI (Securities and Exchange Board of India)** for mutual funds. "
                "It helps investors understand the risk level associated with a mutual fund scheme.\n\n"
                "The Riskometer classifies risk into **six levels**:\n\n"
                "1. **Low** - Lowest risk\n"
                "2. **Low to Moderate** - Slightly higher than low risk\n"
                "3. **Moderate** - Medium risk\n"
                "4. **Moderately High** - Higher than moderate risk\n"
                "5. **High** - High risk\n"
                "6. **Very High** - Highest risk\n\n"
                "The Riskometer is displayed on all mutual fund documents (SID, KIM, Factsheet) to help investors make informed decisions based on their risk tolerance."
            )
            return {
                'answer': definition_answer,
                'source_url': "https://www.amfiindia.com/",
                'refused': False,
                'query_type': 'general'
            }
        
        # FIRST: Check if query is about mutual funds at all (before any processing)
        mf_keywords = ['mutual fund', 'fund', 'scheme', 'hdfc', 'elss', 'sip', 'nav', 'expense ratio', 
                      'exit load', 'benchmark', 'riskometer', 'fund manager', 'portfolio', 'investment',
                      'redemption', 'lock-in', 'ter', 'factsheet', 'sid', 'kim', 'large cap', 'flexi cap',
                      'hybrid', 'taxsaver', 'tax saver']
        is_about_mf = any(kw in query_lower for kw in mf_keywords)
        
        # Check for clearly unrelated queries (president, politics, general knowledge, etc.)
        unrelated_patterns = [
            r'president\s+of\s+(india|usa|america|united\s+states)',
            r'prime\s+minister\s+of',
            r'capital\s+of\s+(india|delhi|mumbai|bangalore)',
            r'who\s+is\s+(?:the\s+)?(president|prime\s+minister|ceo)\s+of',
            r'weather\s+in',
            r'news\s+about',
            r'sports\s+(score|match|game)',
            r'(movie|film)\s+(review|rating)',
            r'recipe\s+for',
            r'how\s+to\s+cook',
            r'translate\s+',
        ]
        is_unrelated = False
        for pattern in unrelated_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                is_unrelated = True
                break
        
        # Also check for "who is the X" where X is not fund-related
        if not is_about_mf and re.search(r'who\s+is\s+(?:the\s+)?(\w+)', query_lower):
            match = re.search(r'who\s+is\s+(?:the\s+)?(\w+)', query_lower)
            if match:
                word_after = match.group(1).lower()
                mf_roles = ['manager', 'fund', 'portfolio', 'investment']
                unrelated_roles = ['president', 'prime', 'minister', 'ceo', 'king', 'queen', 'leader']
                # If it's an unrelated role OR if query has "of" and word is not MF-related
                if word_after in unrelated_roles:
                    is_unrelated = True
                elif 'of' in query_lower and word_after not in mf_roles:
                    # "who is the X of Y" where X is not fund-related
                    is_unrelated = True
        
        if is_unrelated and not is_about_mf:
            return {
                'answer': "I only provide information about HDFC Mutual Funds. I don't have information about that topic. Please ask me about HDFC schemes, expense ratios, exit loads, fund managers, or other mutual fund-related questions.",
                'source_url': None,
                'refused': True,
                'query_type': 'general'
            }
        
        # Extract scheme from query if mentioned
        scheme_name, scheme_tag = self._extract_scheme_from_query(query)
        
        # Update chat context if scheme is mentioned
        if scheme_name:
            self.chat_context['last_scheme'] = scheme_name
            self.chat_context['last_scheme_tag'] = scheme_tag
        
        # Check for special query types first (before context handling)
        query_lower = query.lower()
        
        # If no scheme mentioned but we have context, use it (only for metric/entity queries)
        if not scheme_name and self.chat_context['last_scheme']:
            # Check if query is asking about a metric/entity without specifying scheme
            query_type = self.query_classifier.classify(query)
            if query_type in ['metric', 'entity']:
                # Use context scheme - re-retrieve with scheme context
                scheme_name = self.chat_context['last_scheme']
                scheme_tag = self.chat_context['last_scheme_tag']
                # Re-retrieve chunks with scheme context for better results
                from rag_retriever import RAGRetriever
                retriever = RAGRetriever()
                enhanced_query = f"{scheme_name} {query}"
                chunks = retriever.retrieve(enhanced_query, top_k=5)
                query_lower = enhanced_query.lower()
                import logging
                logging.getLogger(__name__).debug(f"Using chat context: {scheme_name} for query: {query}")
        elif not scheme_name and not self.chat_context['last_scheme']:
            # No scheme mentioned and no context - for metric/entity queries, ask user to specify
            query_type = self.query_classifier.classify(query)
            if query_type in ['metric', 'entity']:
                schemes_list = ", ".join(self.actual_schemes)
                return {
                    'answer': (
                        f"I can help you with that! However, I need to know which scheme you're asking about. "
                        f"I have information about these 4 HDFC schemes: {schemes_list}. "
                        f"Please specify the scheme name in your question, for example: 'What is the exit load of HDFC Hybrid Equity Fund?'"
                    ),
                    'source_url': "https://www.hdfcfund.com/",
                    'refused': False,
                    'query_type': query_type
                }
        
        # Special handling for riskometer definition queries FIRST (before other checks)
        if any(phrase in query_lower for phrase in ["what is riskometer", "definition of riskometer", "what exactly is the definition of riskometer", "what is the riskometer"]):
            definition_answer = (
                "The **Riskometer** is a standardized risk measurement scale introduced by **SEBI (Securities and Exchange Board of India)** for mutual funds. "
                "It helps investors understand the risk level associated with a mutual fund scheme.\n\n"
                "The Riskometer classifies risk into **six levels**:\n\n"
                "1. **Low** - Lowest risk\n"
                "2. **Low to Moderate** - Slightly higher than low risk\n"
                "3. **Moderate** - Medium risk\n"
                "4. **Moderately High** - Higher than moderate risk\n"
                "5. **High** - High risk\n"
                "6. **Very High** - Highest risk\n\n"
                "The Riskometer is displayed on all mutual fund documents (SID, KIM, Factsheet) to help investors make informed decisions based on their risk tolerance."
            )
            return {
                'answer': definition_answer,
                'source_url': "https://www.amfiindia.com/",
                'refused': False,
                'query_type': 'general'
            }
        
        # Special handling for "riskometer of all funds" queries
        riskometer_patterns = [
            "riskometer of all", "riskometer score of all", "risk level of all", 
            "risk of all funds", "riskometer for all", "riskometer all funds",
            "riskometer scores"
        ]
        if any(phrase in query_lower for phrase in riskometer_patterns) and "all" in query_lower:
            if self.riskometer_data:
                riskometer_list = []
                for scheme in self.actual_schemes:
                    risk_level = self.riskometer_data.get(scheme, "Not available")
                    riskometer_list.append(f"• {scheme}: {risk_level}")
                
                answer = "The riskometer scores for the HDFC schemes I have information about are:\n\n" + "\n".join(riskometer_list)
                answer += "\n\nThe riskometer is a standardized risk measurement scale introduced by SEBI for mutual funds. It classifies risk into six levels: Low, Low to Moderate, Moderate, Moderately High, High, and Very High."
                
                return {
                    'answer': answer,
                    'source_url': "https://www.hdfcfund.com/",
                    'refused': False,
                    'query_type': 'list'
                }
        
        # Special handling for "what funds" queries - return actual schemes list
        fund_list_patterns = [
            "what funds", "which funds", "what schemes", "which schemes", 
            "have information about", "available funds", "what all funds",
            "can you answer", "do you have", "funds do you", "schemes do you",
            "what hdfc funds", "which hdfc funds", "list of funds", "list of schemes",
            "do you know about", "know about", "funds do you know", "schemes do you know",
            "what funds do you", "which funds do you", "tell me about funds"
        ]
        if any(phrase in query_lower for phrase in fund_list_patterns):
            schemes_list = ", ".join(self.actual_schemes)
            # Don't set context for "list all funds" queries - user hasn't selected a specific fund yet
            # Context will be set when user mentions a specific scheme
            return {
                'answer': (
                    f"I have information about the following **4 HDFC mutual fund schemes**:\n\n"
                    + "\n".join([f"- **{scheme}**" for scheme in self.actual_schemes])
                    + "\n\nI can answer factual questions about **expense ratios**, **exit loads**, **fund managers**, **investment strategies**, "
                    "and other details for these schemes. I provide information only, not investment advice."
                ),
                'source_url': "https://www.hdfcfund.com/",
                'refused': False,
                'query_type': 'general'
            }
        
        # Check if advisory question
        if self.is_advisory_question(query):
            refused = True
            # Use strict refusal template
            refusal_answer = "Answer: I cannot provide investment advice. I can only provide factual information from documents. Consult a registered financial advisor.\n"
            refusal_answer += "Can help with: expense ratio, exit load, lock-in period, benchmark, riskometer, minimum SIP amount."
            return {
                'answer': refusal_answer,
                'source_url': None,  # No source for refused answers
                'refused': True
            }
        
        # Classify query FIRST (before chunks check) to ensure correct type
        query_type = self.query_classifier.classify(query)
        
        # Phase 1: Simplified riskometer handling - just enhance query if needed
        query_lower = query.lower()
        is_riskometer_query = any(phrase in query_lower for phrase in ['riskometer', 'risk-o-meter', 'risk meter', 'risk level', 'what is riskometer', 'definition of riskometer'])
        
        if is_riskometer_query and (not chunks or len(chunks) < 5):
            # Single retry with riskometer-specific query
            from rag_retriever import RAGRetriever
            retriever = RAGRetriever()
            riskometer_chunks = retriever.retrieve('riskometer HDFC', top_k=20)
            if riskometer_chunks:
                chunks = riskometer_chunks
        
        if not chunks:
            # For metric queries, try direct lookup from file FIRST (fastest, most reliable)
            if query_type == 'metric':
                # Extract scheme and field from query
                query_lower = query.lower()
                scheme_name, scheme_tag = self._extract_scheme_from_query(query)
                field = self._identify_field_from_query(query)
                
                if field:
                    # Try direct lookup from chunks_clean.jsonl
                    direct_chunk = self._get_direct_chunk_from_file(field, scheme_name)
                    if direct_chunk:
                        chunk_text = direct_chunk.get('chunk_text', '')
                        value_match = re.search(r':\s*([^.]*?)(?:\.|Source)', chunk_text, re.IGNORECASE)
                        if value_match:
                            value = value_match.group(1).strip()
                            value = re.sub(r'\s+', ' ', value).strip()
                            
                            # Format answer - clean and beautiful
                            field_display = field.replace('_', ' ').title()
                            if field == 'exit_load':
                                field_display = "Exit Load"
                            elif field == 'expense_ratio':
                                field_display = "Total Expense Ratio (TER)"
                            elif field == 'minimum_sip':
                                field_display = "Minimum SIP"
                            elif field == 'lock_in':
                                field_display = "Lock-in Period"
                            elif field == 'benchmark':
                                field_display = "Benchmark"
                            elif field == 'riskometer':
                                field_display = "Riskometer"
                            
                            scheme_name_used = scheme_name or direct_chunk.get('scheme_tag', '').replace('_', ' ')
                            if scheme_name_used:
                                answer = f"The {field_display.lower()} for {scheme_name_used} is {value}."
                            else:
                                answer = f"The {field_display.lower()} is {value}."
                            
                            # Format date
                            last_updated = direct_chunk.get('last_fetched_date', '2025-11-17')
                            formatted_date = self._format_date(last_updated)
                            
                            formatted_answer = answer
                            if formatted_date:
                                formatted_answer += f"\n\nLast updated: {formatted_date}"
                            
                            source_type = direct_chunk.get('source_type', '')
                            return {
                                'answer': formatted_answer,
                                'source_type': source_type,
                                'source_id': direct_chunk.get('source_id', ''),
                                'source_url': direct_chunk.get('source_url', ''),
                                'refused': False,
                                'query_type': query_type
                            }
                
                # Phase 1: Simplified - just retrieve more chunks if needed (no complex retries)
                if not chunks or len(chunks) < 5:
                    from rag_retriever import RAGRetriever
                    retriever = RAGRetriever()
                    # Single retry with enhanced query
                    enhanced_query = query
                    if scheme_name:
                        enhanced_query = f"{scheme_name} {query}"
                    retry_chunks = retriever.retrieve(enhanced_query, top_k=20)
                    if retry_chunks:
                        chunks = retry_chunks
                
                # If still no chunks after retry
                if not chunks:
                    return {
                        'answer': "Answer: Not found in sources.\nSource: None.",
                        'source_url': None,
                        'refused': False,
                        'query_type': query_type
                    }
            else:
                # For non-metric queries, use generic suggestions
                schemes_list = ", ".join(self.actual_schemes)
                
                suggestions = {
                    'entity': f"I have information about these 4 HDFC schemes: {schemes_list}. Try asking: 'Who is the fund manager of [scheme name]?' or 'Who manages [scheme name]?'",
                    'list': f"I have information about these 4 HDFC schemes: {schemes_list}. Try asking: 'What are the top holdings in [scheme name]?' or 'What is the portfolio composition?'",
                    'how_to': f"I have information about these 4 HDFC schemes: {schemes_list}. Try asking: 'How do I [action] in [scheme name]?' or 'How to [action] from Groww?'",
                    'general': f"I couldn't find relevant information for your question. I have information about these 4 HDFC schemes: {schemes_list}. Please ask about expense ratios, exit loads, minimum SIP amounts, lock-in periods, riskometers, or benchmarks for any of these schemes."
                }
                
                suggestion = suggestions.get(query_type, suggestions['general'])
                
                return {
                    'answer': suggestion,
                    'source_url': self.educational_link,
                    'refused': False,
                    'query_type': query_type
                }
        
        # Check for special query types first (query_type already classified above at line 654)
        query_lower = query.lower()
        
        # Comparison queries (SID vs KIM, SID vs factsheet)
        if 'compare' in query_lower or ('sid' in query_lower and ('kim' in query_lower or 'factsheet' in query_lower)):
            comparison_result = self._handle_comparison_query(query, chunks, scheme_name)
            if comparison_result:
                return comparison_result
        
        # Contradiction detection queries
        if 'contradict' in query_lower or 'contradiction' in query_lower:
            contradiction_result = self._handle_contradiction_query(query, chunks, scheme_name)
            if contradiction_result:
                return contradiction_result
        
        # Canonical facts queries
        if 'canonical' in query_lower or 'facts row' in query_lower:
            canonical_result = self._handle_canonical_facts_query(query, chunks, scheme_name)
            if canonical_result:
                return canonical_result
        
        # Business rule queries (can I redeem, etc.)
        if any(phrase in query_lower for phrase in ['can i redeem', 'can redeem', 'if i redeem', 'redeem after']):
            business_result = self._handle_business_rule_query(query, chunks, scheme_name)
            if business_result:
                return business_result
        
        # For metric queries, try strict extraction first
        if query_type == 'metric':
            strict_result = self._extract_metric_strict(query, chunks, scheme_name)
            if strict_result:
                # Extract the fact from strict extraction
                answer_text = strict_result['answer']
                
                # Format date properly (convert "11/17/2025" or "2025-11-17" to "17 Nov, 2025")
                last_updated = strict_result.get('last_updated', '')
                formatted_date = self._format_date(last_updated)
                
                # Check if answer is valid (not "0" or empty)
                if answer_text and answer_text.strip() and answer_text.strip() != "0" and answer_text.strip() != "0%":
                    # Instead of returning immediately, pass to LLM for beautiful rephrasing
                    # Build context with the extracted fact and original context
                    extracted_fact = answer_text
                    source_url = strict_result['source_url']
                    confidence = strict_result['confidence']
                    
                    # Build simple context from chunks for LLM rephrasing
                    context_parts_simple = []
                    for chunk in chunks[:5]:  # Use top 5 chunks for context
                        chunk_text = chunk.get('text', '')
                        if chunk_text:
                            cleaned = self._clean_chunk_text(chunk_text, query_type)
                            if cleaned:
                                context_parts_simple.append(cleaned[:300])  # Limit each chunk
                    context_for_rephrase = " ".join(context_parts_simple)[:1500] if context_parts_simple else ""
                    
                    # Rephrase using LLM to make it natural and beautiful
                    rephrased_answer = self._rephrase_metric_answer(query, extracted_fact, context_for_rephrase, scheme_name)
                    
                    # If LLM rephrasing failed or returned empty, use formatted version
                    if not rephrased_answer or len(rephrased_answer.strip()) < 10:
                        # Fallback to formatted version
                        scheme_display = scheme_name or "the fund"
                        if 'expense ratio' in query_lower or 'ter' in query_lower:
                            value_match = re.search(r'(\d+\.?\d*%?)', extracted_fact)
                            if value_match:
                                value = value_match.group(1)
                                rephrased_answer = f"The **Total Expense Ratio (TER)** for **{scheme_display}** is **{value}** per annum."
                            else:
                                rephrased_answer = extracted_fact
                        elif 'exit load' in query_lower:
                            value_match = re.search(r'(\d+\.?\d*%?)', extracted_fact)
                            if value_match:
                                value = value_match.group(1)
                                rephrased_answer = f"The **Exit Load** for **{scheme_display}** is **{value}**."
                            else:
                                rephrased_answer = extracted_fact
                        else:
                            rephrased_answer = extracted_fact
                    
                    # Add date
                    if formatted_date:
                        rephrased_answer += f"\n\n*Last updated: {formatted_date}*"
                    
                    return {
                        'answer': rephrased_answer,  # ✅ LLM-rephrased, natural answer
                        'source_url': source_url,
                        'refused': False,
                        'query_type': query_type,
                        'confidence': confidence
                    }
                else:
                    # Invalid answer (0 or empty) - fall through to LLM generation
                    pass
            else:
                # Metric not found - return strict "not found" format
                return {
                    'answer': "Answer: Not found in sources.\nSource: None.",
                    'source_url': None,
                    'refused': False,
                    'query_type': query_type,
                    'confidence': 'LOW'
                }
        query_lower = query.lower()
        
        # Extract key terms from query
        query_terms = set(query_lower.split())
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how', 'when', 'where', 'who', 'which', 'of', 'for', 'in', 'on', 'at', 'to', 'from', 'with', 'about', 'hdfc', 'fund'}
        query_terms = {t for t in query_terms if t not in stop_words and len(t) > 2}
        
        # For entity queries (fund manager), boost manager-related terms
        if query_type == 'entity' and ('manager' in query_lower or 'manages' in query_lower):
            query_terms.update(['fund manager', 'manager', 'investment manager', 'portfolio manager', 'equity analyst', 'manages', 'managed by'])
        
        # For redemption queries, boost redemption-related terms
        if any(phrase in query_lower for phrase in ['redeem', 'redemption', 'withdraw', 'sell units']):
            query_terms.update(['redeem', 'redemption', 'withdraw', 'sell', 'units', 'proceeds', 'credited', 'submit', 'request'])
        
        # Get keywords to boost for this query type
        boost_keywords = self.query_classifier.get_keywords_for_type(query_type)
        
        # For entity queries (fund manager), add manager-specific keywords
        if query_type == 'entity' and ('manager' in query_lower or 'manages' in query_lower):
            boost_keywords.extend(['fund manager', 'manager', 'investment manager', 'portfolio manager', 'equity analyst', 'manages', 'managed by', 'senior fund manager'])
        
        # For redemption queries, add redemption-specific keywords
        if any(phrase in query_lower for phrase in ['redeem', 'redemption', 'withdraw', 'sell units']):
            boost_keywords.extend(['redeem', 'redemption', 'withdraw', 'sell', 'units', 'proceeds', 'credited', 'submit', 'request', 'cut-off', 'cutoff', 'business day'])
        
        # Enhanced multi-factor scoring
        scored_chunks = []
        for chunk in chunks:
            chunk_text_lower = chunk['text'].lower()
            chunk_terms = set(chunk_text_lower.split())
            
            # 1. Vector similarity (from retrieval)
            similarity = chunk.get('similarity', 0.5)
            relevance_score = chunk.get('relevance_score', similarity)
            
            # 2. Term overlap with query
            term_overlap = len(query_terms & chunk_terms)
            term_score = min(term_overlap * 0.15, 0.3)  # Cap at 0.3
            
            # 3. Keyword matching (boost keywords for query type)
            keyword_matches = sum(1 for kw in boost_keywords if kw.lower() in chunk_text_lower)
            keyword_score = min(keyword_matches * 0.1, 0.2)  # Cap at 0.2
            
            # 4. Source authority (already in relevance_score, but boost SID/KIM)
            source_boost = 0.0
            if 'sid' in chunk['source_id'] or 'kim' in chunk['source_id']:
                source_boost = 0.1
            elif 'overview' in chunk['source_id'] and query_type == 'metric':
                source_boost = 0.08  # Overview good for current metrics
            
            # 5. Position boost (prefer earlier chunks from same source)
            position_boost = 0.0
            # This would require chunk_index, but we'll skip for now
            
            # Combined score
            final_score = (
                relevance_score * 0.6 +  # Primary: retrieval relevance
                term_score * 0.2 +        # Query term matching
                keyword_score * 0.15 +   # Type-specific keywords
                source_boost * 0.05      # Source authority
            )
            
            scored_chunks.append({
                'chunk': chunk,
                'score': final_score,
                'term_overlap': term_overlap,
                'keyword_matches': keyword_matches
            })
        
        # Sort by final score
        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        # Build context from top relevant chunks (SIMPLIFIED - Phase 1 & 2 optimization)
        # Increased context size and simplified filtering - let LLM do the intelligent filtering
        context = self._build_simplified_context(scored_chunks, query_type, query_lower, max_length=10000)
        
        # If no context was built and this is a redemption query, provide a helpful fallback
        if not context.strip() and query_type == 'how_to' and any(phrase in query_lower for phrase in ['redeem', 'redemption', 'withdraw', 'sell units']):
            # Fallback: provide general redemption instructions based on common mutual fund redemption process
            context = (
                "To redeem mutual fund units, you can do so through your distributor platform (like Groww) or the AMC website. "
                "Log in to your account, navigate to the 'Redeem' or 'Withdraw' section, select the fund, enter the number of units or amount, "
                "and submit the redemption request before the cut-off time (usually 3 PM on business days). "
                "The proceeds will be credited to your registered bank account within 3-5 business days (T+3 to T+5). "
                "For ELSS funds, redemption is only allowed after the lock-in period of 3 years."
            )
        
        # Get top chunk for source URL (use first chunk or highest scoring)
        top_chunk = chunks[0] if chunks else {'source_url': '', 'text': ''}
        if scored_chunks and len(scored_chunks) > 0:
            top_chunk = scored_chunks[0]['chunk']
        
        # Check for conflicts if metric query
        conflict_info = None
        if query_type == 'metric':
            scheme_tag = top_chunk.get('scheme_tag', '')
            field = self._identify_field_from_query(query)
            if scheme_tag and field:
                # Check if there's a conflict for this field
                conflicts = self.conflict_detector.detect_conflicts()
                relevant_conflicts = [c for c in conflicts if c['scheme_tag'] == scheme_tag and c['field'] == field]
                if relevant_conflicts:
                    conflict_info = relevant_conflicts[0]
                    import logging
                    logging.getLogger(__name__).warning(f"Conflict detected: {conflict_info['authoritative_source']} vs {conflict_info['conflicting_source']}")
        
        # Generate answer using LLM or fallback (with caching)
        # For redemption queries, check early if we should use fallback
        is_redemption_query = query_type == 'how_to' and any(phrase in query_lower for phrase in ['redeem', 'redemption', 'withdraw', 'sell units'])
        
        # Extract scheme name for redemption fallback
        scheme_name_for_redemption = None
        if is_redemption_query:
            if 'flexi cap' in query_lower:
                scheme_name_for_redemption = "HDFC Flexi Cap Fund"
            elif 'large cap' in query_lower:
                scheme_name_for_redemption = "HDFC Large Cap Fund"
            elif 'elss' in query_lower or 'taxsaver' in query_lower:
                scheme_name_for_redemption = "HDFC TaxSaver (ELSS)"
            elif 'hybrid' in query_lower:
                scheme_name_for_redemption = "HDFC Hybrid Equity Fund"
            else:
                scheme_name_for_redemption = "HDFC Large Cap Fund"  # Default
        
        if is_redemption_query and (not context.strip() or len(context.strip()) < 100):
            # Use fallback immediately for redemption queries with insufficient context
            answer = f"To redeem your **{scheme_name_for_redemption}** units, follow these steps:\n\n1. **Log in** to your account on the AMC website or distributor platform (like Groww)\n2. Navigate to the **'Redeem'** or **'Withdraw'** section and select the fund\n3. Enter the number of units or amount you want to redeem\n4. **Submit** the redemption request **before 3 PM** on any business day\n5. The proceeds will be credited to your registered bank account within **3-5 business days**\n\n**Important:** Redemption requests submitted after 3 PM will be processed on the next business day."
        elif not context.strip():
            # If context is empty, for entity queries try direct lookup first (STEP 3)
            if query_type == 'entity' and ('manager' in query_lower or 'manages' in query_lower):
                manager_info = self._direct_lookup_manager(query)
                if manager_info:
                    answer = manager_info
                else:
                    answer = "I couldn't find the fund manager information in my sources. Please try asking about a specific HDFC scheme."
            else:
                answer = "I couldn't find specific information in the available sources. Please try rephrasing your question or ask about expense ratios, exit loads, fund managers, or other fund details."
        else:
            # Phase 2: Enhanced LLM generation with better prompts for general queries
            # For strategy/investment queries, ensure we get the right fund's information
            is_strategy_query = any(phrase in query_lower for phrase in [
                'investment strategy', 'investment approach', 'investment philosophy',
                'strategy', 'investment style', 'how does the fund invest', 'investment objective'
            ])
            
            if is_strategy_query and scheme_name:
                # Enhance query to ensure correct fund
                enhanced_query = f"{scheme_name} {query}"
                # Re-retrieve chunks with enhanced query to get correct fund info
                from rag_retriever import RAGRetriever
                retriever = RAGRetriever()
                strategy_chunks = retriever.retrieve(enhanced_query, top_k=20)
                if strategy_chunks:
                    # Filter to ensure we get chunks for the correct fund
                    correct_chunks = []
                    scheme_keywords = scheme_name.lower().split()
                    for chunk in strategy_chunks:
                        chunk_text = chunk.get('text', '').lower()
                        # Prefer chunks that mention the correct fund
                        if any(kw in chunk_text for kw in scheme_keywords if len(kw) > 3):
                            correct_chunks.append(chunk)
                    if correct_chunks:
                        chunks = correct_chunks[:15]  # Use filtered chunks
                        # Rebuild context with correct fund chunks
                        scored_chunks = [{'chunk': c, 'score': 1.0} for c in chunks]
                        context = self._build_simplified_context(scored_chunks, query_type, query_lower, max_length=10000)
            
            answer = self._generate_with_llm(query, context, use_cache=False)  # Cache disabled for debugging
            
            # For entity queries, if LLM didn't find manager, try direct lookup
            if query_type == 'entity' and ('manager' in query_lower or 'manages' in query_lower):
                # Check if answer doesn't contain a manager name
                has_manager_name = any(name in answer for name in ['Roshi', 'Jain', 'Dhruv', 'Muchhal', 'Fund Manager'])
                if not has_manager_name or not answer or len(answer.strip()) < 20 or 'not found' in answer.lower() or 'don\'t have' in answer.lower() or 'couldn\'t find' in answer.lower():
                    manager_info = self._direct_lookup_manager(query)
                    if manager_info:
                        answer = manager_info
            
        # If LLM returned empty answer, use fallback
        if (not answer or len(answer.strip()) < 10) and is_redemption_query:
            answer = f"To redeem your **{scheme_name_for_redemption}** units, follow these steps:\n\n1. **Log in** to your account on the AMC website or distributor platform (like Groww)\n2. Navigate to the **'Redeem'** or **'Withdraw'** section and select the fund\n3. Enter the number of units or amount you want to redeem\n4. **Submit** the redemption request **before 3 PM** on any business day\n5. The proceeds will be credited to your registered bank account within **3-5 business days**\n\n**Important:** Redemption requests submitted after 3 PM will be processed on the next business day."
        
        # Special handling for investor queries - check if answer is about fund manager instead
        query_lower = query.lower()
        if 'investor' in query_lower:
            # Check if answer incorrectly mentions fund manager
            if 'manager' in answer.lower() and ('fund manager' in answer.lower() or 'The fund manager is' in answer):
                # Answer is about fund manager, but query asked about investors - try to extract investor info
                investor_extracted = self._extract_from_context_directly('entity', context, query)
                if investor_extracted and 'investor' in investor_extracted.lower():
                    answer = investor_extracted
                else:
                    # Fallback: use overview chunks that contain "ideal for" or "suitable for"
                    overview_chunks = [c for c in chunks if 'overview' in c.get('source_id', '').lower()]
                    if overview_chunks:
                        overview_context = " ".join([c.get('text', '')[:500] for c in overview_chunks[:2]])
                        investor_extracted = self._extract_from_context_directly('entity', overview_context, query)
                        if investor_extracted:
                            answer = investor_extracted
                    else:
                        # Clean up incomplete sentences
                        answer = re.sub(r'\bThe fund manager is of the\.?\s*', '', answer)
                        answer = re.sub(r'\bThe fund manager is\.?\s*', '', answer)
        
        # Save redemption fallback answer before post-processing (in case it gets cleared)
        redemption_fallback = None
        if is_redemption_query and '**HDFC Large Cap Fund** units' in answer:
            redemption_fallback = answer
        
        # Post-process answer to extract and format specific details
        answer = self._post_process_answer(answer, query_type, context, query)
        
        # Clean answer: Remove SEBI circulars, regulatory citations, and metadata
        answer = self._clean_answer_metadata(answer)
        
        # Validate answer doesn't contain hallucinated fund names (CRITICAL - runs on all answers)
        answer = self._validate_answer_against_schemes(answer)
        
        # Phase 2: Improve answer presentation - ensure complete, well-formatted answers
        # Only call if we have a valid answer and context
        if answer and context:
            try:
                answer = self._improve_answer_presentation(answer, query, query_type, context, scheme_name)
            except Exception as e:
                print(f"Answer improvement error: {e}")
                # Continue with original answer if improvement fails
        
        # Final cleanup pass - remove any remaining artifacts (VERY AGGRESSIVE)
        if answer:
            # Remove chunk separators (all variations)
            answer = re.sub(r'\s*---\s*', ' ', answer)
            answer = re.sub(r'\s*---', ' ', answer)
            answer = re.sub(r'---\s*', ' ', answer)
            answer = re.sub(r'---', ' ', answer)
            
            # Remove document headers (case-insensitive, all variations)
            answer = re.sub(r'SCHEME\s+INFORMATION\s+DOCUMENT\s+', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'SCHEME INFORMATION DOCUMENT\s+', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'SCHEME\s+INFORMATION\s+DOCUMENT', '', answer, flags=re.IGNORECASE)
            
            # Remove fund type labels (all variations)
            answer = re.sub(r'\bHybrid\s+DIRECT\s+REGULAR\b\s*', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\bDIRECT\s+REGULAR\b\s*', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\bDIRECT REGULAR\b\s*', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'DIRECT REGULAR', '', answer, flags=re.IGNORECASE)
            
            # Remove incomplete sentences at the end
            answer = re.sub(r'\s+whet\s*$', '.', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\s+if in doubt about\s*$', '.', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\s+Investors should consult.*?$', '.', answer, flags=re.IGNORECASE | re.DOTALL)
            
            # Fix "equityequity" -> "equity"
            answer = re.sub(r'equityequity', 'equity', answer, flags=re.IGNORECASE)
            answer = re.sub(r'equity\s+equity', 'equity', answer, flags=re.IGNORECASE)
            
            # Remove "A HDFC" at start if it appears
            answer = re.sub(r'^A\s+HDFC\s+', 'HDFC ', answer, flags=re.IGNORECASE)
            
            # Clean up multiple spaces
            answer = re.sub(r'\s+', ' ', answer)
            answer = answer.strip()
            
            # Ensure proper ending
            if answer and not answer.rstrip()[-1] in '.!?':
                answer += "."
        
        # SPECIAL CHECK: For redemption queries, if answer contains exit load info instead of steps, use fallback
        if is_redemption_query:
            # Check if answer is about exit load instead of redemption steps
            exit_load_indicators = [
                'exit load', 'exit charge', 'payable if units are redeemed',
                'redeemed/switched-out', 'within 1 year', 'after 1 year',
                'date of allotment', 'no exit load is payable'
            ]
            has_exit_load_info = any(indicator in answer.lower() for indicator in exit_load_indicators)
            has_redemption_steps = any(phrase in answer.lower() for phrase in [
                'log in', 'navigate to', 'redeem section', 'submit', 'before 3 pm',
                'credited to your bank', '3-5 business days', 'follow these steps',
                'withdraw section', 'enter the number', 'redemption request', 'proceeds will be credited'
            ])
            
            # Also check for poor quality answers (mixed topics, incomplete, or just mentions "can be redeemed")
            has_poor_quality = any(phrase in answer.lower() for phrase in [
                'can be redeemedswitched', 'can be redeemed/switched', 'nav based',
                'can invest in sip', 'lump sum', 'minimum application amount',
                'can be redeemedswitched out', 'redeemedswitched out', 'business day at nav'
            ])
            
            # Check if answer is too short or doesn't have proper structure
            is_too_short = len(answer.strip()) < 100
            has_proper_structure = any(marker in answer for marker in ['1.', '2.', '**Log in', '**Submit', 'step'])
            
            # If answer has exit load but no redemption steps, OR has poor quality, OR is too short without structure, replace with proper fallback
            if (has_exit_load_info and not has_redemption_steps) or (has_poor_quality and not has_redemption_steps) or (is_too_short and not has_proper_structure and not has_redemption_steps):
                # Extract scheme name for fallback
                scheme_name_fallback = "HDFC Large Cap Fund"  # Default
                if 'flexi cap' in query_lower:
                    scheme_name_fallback = "HDFC Flexi Cap Fund"
                elif 'large cap' in query_lower:
                    scheme_name_fallback = "HDFC Large Cap Fund"
                elif 'elss' in query_lower or 'taxsaver' in query_lower:
                    scheme_name_fallback = "HDFC TaxSaver (ELSS)"
                elif 'hybrid' in query_lower:
                    scheme_name_fallback = "HDFC Hybrid Equity Fund"
                answer = f"To redeem your **{scheme_name_fallback}** units, follow these steps:\n\n1. **Log in** to your account on the AMC website or distributor platform (like Groww)\n2. Navigate to the **'Redeem'** or **'Withdraw'** section and select the fund\n3. Enter the number of units or amount you want to redeem\n4. **Submit** the redemption request **before 3 PM** on any business day\n5. The proceeds will be credited to your registered bank account within **3-5 business days**\n\n**Important:** Redemption requests submitted after 3 PM will be processed on the next business day."
        
        # If answer was cleared and we have a redemption fallback, restore it
        if (not answer or len(answer.strip()) < 10) and redemption_fallback:
            answer = redemption_fallback
        
        # Double-check: If answer still contains invalid fund patterns, force correct answer
        if any(phrase in query_lower for phrase in ["what funds", "which funds", "what schemes", "know about", "do you know", "have information about"]):
            # Check if answer has a fund list format
            if re.search(r'[*•]\s*HDFC\s+', answer, re.IGNORECASE) or len(re.findall(r'HDFC\s+[A-Z][a-z]+', answer)) > 4:
                # Force correct answer with markdown formatting
                answer = (
                    f"I have information about the following **4 HDFC mutual fund schemes**:\n\n"
                    + "\n".join([f"- **{scheme}**" for scheme in self.actual_schemes])
                    + "\n\nI can answer factual questions about **expense ratios**, **exit loads**, **fund managers**, **investment strategies**, "
                    "and other details for these schemes. I provide information only, not investment advice."
                )
        
        # Final check: If answer is still empty after all processing, use appropriate fallback
        if not answer or len(answer.strip()) < 10:
            if query_type == 'how_to' and any(phrase in query_lower for phrase in ['redeem', 'redemption', 'withdraw', 'sell units']):
                # Extract scheme name
                scheme_name_fallback = "HDFC Large Cap Fund"  # Default
                if 'flexi cap' in query_lower:
                    scheme_name_fallback = "HDFC Flexi Cap Fund"
                elif 'large cap' in query_lower:
                    scheme_name_fallback = "HDFC Large Cap Fund"
                elif 'elss' in query_lower or 'taxsaver' in query_lower:
                    scheme_name_fallback = "HDFC TaxSaver (ELSS)"
                elif 'hybrid' in query_lower:
                    scheme_name_fallback = "HDFC Hybrid Equity Fund"
                answer = f"To redeem your **{scheme_name_fallback}** units, follow these steps:\n\n1. **Log in** to your account on the AMC website or distributor platform (like Groww)\n2. Navigate to the **'Redeem'** or **'Withdraw'** section and select the fund\n3. Enter the number of units or amount you want to redeem\n4. **Submit** the redemption request **before 3 PM** on any business day\n5. The proceeds will be credited to your registered bank account within **3-5 business days**\n\n**Important:** Redemption requests submitted after 3 PM will be processed on the next business day."
            elif query_type == 'entity' and ('manager' in query_lower or 'manages' in query_lower):
                # Try direct lookup from overview files as fallback (STEP 3)
                manager_info = self._direct_lookup_manager(query)
                if manager_info:
                    answer = manager_info
                else:
                    # Try one more time to extract manager name from context
                    context_clean = self._clean_context_for_entity(context)
                    extracted = self._extract_from_context_directly('entity', context_clean, query)
                    if extracted and 'manager' in extracted.lower():
                        answer = extracted
                    else:
                        answer = "I couldn't find the fund manager information in my sources. Please try asking about a specific HDFC scheme."
            else:
                answer = "I couldn't find specific information in my sources. Please try rephrasing your question or ask about expense ratios, exit loads, fund managers, or other fund details."
        
        # Format answer with timestamp (pass original query for LLM cleaning)
        formatted_answer = self.format_answer(answer, top_chunk.get('source_url', ''), query_type, refused=False, original_query=query)
        
        # Final cleanup pass AFTER formatting (remove any artifacts that made it through)
        if formatted_answer:
            # Remove chunk separators (all variations)
            formatted_answer = re.sub(r'\s*---\s*', ' ', formatted_answer)
            formatted_answer = re.sub(r'\s*---', ' ', formatted_answer)
            formatted_answer = re.sub(r'---\s*', ' ', formatted_answer)
            formatted_answer = re.sub(r'---', ' ', formatted_answer)
            
            # Remove document headers (case-insensitive, all variations)
            formatted_answer = re.sub(r'SCHEME\s+INFORMATION\s+DOCUMENT\s+', '', formatted_answer, flags=re.IGNORECASE)
            formatted_answer = re.sub(r'SCHEME INFORMATION DOCUMENT\s+', '', formatted_answer, flags=re.IGNORECASE)
            formatted_answer = re.sub(r'SCHEME\s+INFORMATION\s+DOCUMENT', '', formatted_answer, flags=re.IGNORECASE)
            
            # Remove fund type labels (all variations)
            formatted_answer = re.sub(r'\bHybrid\s+DIRECT\s+REGULAR\b\s*', '', formatted_answer, flags=re.IGNORECASE)
            formatted_answer = re.sub(r'\bDIRECT\s+REGULAR\b\s*', '', formatted_answer, flags=re.IGNORECASE)
            formatted_answer = re.sub(r'\bDIRECT REGULAR\b\s*', '', formatted_answer, flags=re.IGNORECASE)
            formatted_answer = re.sub(r'DIRECT REGULAR', '', formatted_answer, flags=re.IGNORECASE)
            
            # Remove incomplete sentences at the end (before timestamp)
            # Split by timestamp marker to preserve it
            if '*Last updated:' in formatted_answer:
                parts = formatted_answer.split('*Last updated:')
                main_answer = parts[0]
                timestamp = '*Last updated:' + parts[1] if len(parts) > 1 else ''
                
                # Clean main answer
                main_answer = re.sub(r'\s+whet\s*$', '.', main_answer, flags=re.IGNORECASE)
                main_answer = re.sub(r'\s+if in doubt about\s*$', '.', main_answer, flags=re.IGNORECASE)
                main_answer = re.sub(r'\s+Investors should consult.*?$', '.', main_answer, flags=re.IGNORECASE | re.DOTALL)
                
                # Ensure proper ending before timestamp
                if main_answer and not main_answer.rstrip()[-1] in '.!?':
                    main_answer += "."
                
                formatted_answer = main_answer + timestamp
            else:
                formatted_answer = re.sub(r'\s+whet\s*$', '.', formatted_answer, flags=re.IGNORECASE)
                formatted_answer = re.sub(r'\s+if in doubt about\s*$', '.', formatted_answer, flags=re.IGNORECASE)
                formatted_answer = re.sub(r'\s+Investors should consult.*?$', '.', formatted_answer, flags=re.IGNORECASE | re.DOTALL)
                if formatted_answer and not formatted_answer.rstrip()[-1] in '.!?*':
                    formatted_answer += "."
            
            # Fix "equityequity" -> "equity"
            formatted_answer = re.sub(r'equityequity', 'equity', formatted_answer, flags=re.IGNORECASE)
            formatted_answer = re.sub(r'equity\s+equity', 'equity', formatted_answer, flags=re.IGNORECASE)
            
            # Remove "A HDFC" at start if it appears
            formatted_answer = re.sub(r'^A\s+HDFC\s+', 'HDFC ', formatted_answer, flags=re.IGNORECASE)
            
            # Clean up multiple spaces (but preserve line breaks for markdown)
            formatted_answer = re.sub(r'[ \t]+', ' ', formatted_answer)  # Multiple spaces/tabs to single space
            formatted_answer = re.sub(r'\n\s*\n\s*\n+', '\n\n', formatted_answer)  # Multiple newlines to double
            formatted_answer = formatted_answer.strip()
        
        result = {
            'answer': formatted_answer,
            'source_url': top_chunk.get('source_url', '') if not refused else None,
            'refused': False,
            'query_type': query_type
        }
        
        # Add conflict info if detected
        if conflict_info:
            result['conflict_detected'] = True
            result['conflict_info'] = {
                'authoritative_source': conflict_info['authoritative_source'],
                'authoritative_value': conflict_info['authoritative_value'],
                'conflicting_source': conflict_info['conflicting_source'],
                'conflicting_value': conflict_info['conflicting_value']
            }
        
        return result
    
    def _get_source_authority_priority(self, source_type: str) -> int:
        """Get authority priority (lower number = higher priority)"""
        authority_map = {
            'sid_pdf': 1,  # SID - highest
            'kim_pdf': 2,  # KIM - second
            'factsheet_consolidated': 3,  # Factsheet - third
            'scheme_overview': 4,  # Overview - fourth
        }
        # Default to 5 for other types
        return authority_map.get(source_type, 5)
    
    def _normalize_metric_value(self, value: str, field: str) -> str:
        """Normalize metric value according to rules"""
        # Percentages → format with two decimals and trailing "%"
        if '%' in value or field in ['exit_load', 'expense_ratio', 'ter']:
            # Extract percentage - look for number near percentage keyword
            pct_match = re.search(r'([0-9]{1,3}(?:\.[0-9]{1,2})?)\s?%', value)
            if pct_match:
                pct_val = float(pct_match.group(1))
                return f"{pct_val:.2f}%"
            # If no % but field is percentage type, check if it's just a number
            if field in ['exit_load', 'expense_ratio', 'ter']:
                num_match = re.search(r'([0-9]{1,3}(?:\.[0-9]{1,2})?)', value)
                if num_match:
                    num_val = float(num_match.group(1))
                    return f"{num_val:.2f}%"
        
        # Currency → prefix with "₹" and add commas
        if '₹' in value or 'Rs' in value or 'INR' in value or field in ['minimum_sip', 'min_lumpsum', 'minimum_application']:
            # Extract number
            num_match = re.search(r'([0-9,]+)', value.replace(',', ''))
            if num_match:
                num_val = int(num_match.group(1).replace(',', ''))
                return f"₹{num_val:,}"
        
        # Lock-in → canonical months but show years in answer
        if 'lock' in field.lower() or 'year' in value.lower():
            year_match = re.search(r'(\d+)\s*(?:year|years|yr|yrs)', value, re.IGNORECASE)
            if year_match:
                years = int(year_match.group(1))
                months = years * 12
                return f"{years} years ({months} months)"
            # If just a number and field is lock_in, assume years
            if field == 'lock_in':
                num_match = re.search(r'(\d+)', value)
                if num_match:
                    years = int(num_match.group(1))
                    months = years * 12
                    return f"{years} years ({months} months)"
        
        return value.strip()
    
    def _extract_numeric_pattern(self, text: str, field: str) -> Optional[Dict]:
        """Extract numeric pattern from text for given field"""
        text_lower = text.lower()
        
        # Patterns for different fields
        patterns = {
            'exit_load': [
                r'exit\s*load[^.]*?([0-9]{1,3}(?:\.[0-9]{1,2})?)\s?%',
                r'([0-9]{1,3}(?:\.[0-9]{1,2})?)\s?%\s*exit\s*load',
                r'exit\s*load[^.]*?nil',
            ],
            'expense_ratio': [
                # Avoid "reduction" - look for TER as standalone or in specific contexts
                r'(?:total\s*)?expense\s*ratio\s*(?:\(ter\))?[^.]*?(?:is|of|:)\s*([0-9]{1,3}(?:\.[0-9]{1,2})?)\s?%(?!\s*reduction)',
                r'ter\s*(?:is|of|:)\s*([0-9]{1,3}(?:\.[0-9]{1,2})?)\s?%(?!\s*reduction)',
                r'([0-9]{1,3}(?:\.[0-9]{1,2})?)\s?%\s*(?:total\s*)?expense\s*ratio(?!\s*reduction)',
                # Look for TER in overview pages (current values)
                r'(?:current\s*)?(?:total\s*)?expense\s*ratio[^.]*?([0-9]{1,3}(?:\.[0-9]{1,2})?)\s?%(?!\s*reduction)',
            ],
            'minimum_sip': [
                r'minimum\s*(?:sip|application)[^.]*?(?:₹|Rs\.?|INR)?\s?([0-9,]+)',
                r'([0-9,]+)\s*(?:₹|Rs\.?|INR)?\s*minimum\s*(?:sip|application)',
            ],
            'lock_in': [
                r'lock[^.]*?(\d+)\s*(?:year|years|yr|yrs)',
                r'(\d+)\s*(?:year|years|yr|yrs)[^.]*?lock',
            ],
            'benchmark': [
                r'benchmark[^.]*?([A-Z][A-Z0-9\s]+(?:Index|TRI|Total Returns Index))',
                r'benchmarked?\s*against\s*([A-Z][A-Z0-9\s]+(?:Index|TRI|Total Returns Index))',
                r'([A-Z][A-Z0-9\s]+(?:Index|TRI|Total Returns Index))\s*(?:\(as per|as per|\(TRI\)|TRI)',
            ],
            'riskometer': [
                r'riskometer[^.]*?(low|moderate|high|very\s*high|moderately\s*high|low\s*to\s*moderate)',
                r'risk[^.]*?level[^.]*?(low|moderate|high|very\s*high|moderately\s*high|low\s*to\s*moderate)',
                r'scheme\s*riskometer[^.]*?(low|moderate|high|very\s*high|moderately\s*high|low\s*to\s*moderate)',
            ],
            'min_lumpsum': [
                r'minimum\s*(?:lumpsum|application|amount)[^.]*?(?:₹|Rs\.?|INR)?\s?([0-9,]+)',
                r'([0-9,]+)\s*(?:₹|Rs\.?|INR)?\s*minimum\s*(?:lumpsum|application|amount)',
            ],
        }
        
        field_patterns = patterns.get(field, [])
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # Extract excerpt (20-80 chars around match)
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                excerpt = text[start:end].strip()
                # Clean excerpt
                excerpt = re.sub(r'\s+', ' ', excerpt)
                
                return {
                    'value': match.group(1) if match.lastindex else match.group(0),
                    'excerpt': excerpt,
                    'match_start': match.start(),
                    'match_end': match.end()
                }
        
        return None
    
    def _calculate_confidence(self, source_type: str, numeric_match: bool, normalized: bool) -> str:
        """Calculate confidence level"""
        if not numeric_match:
            return "LOW"
        
        # HIGH if SID/KIM and numeric match (normalization is OK for formatting)
        if source_type in ['sid_pdf', 'kim_pdf']:
            return "HIGH"
        
        # MEDIUM if factsheet/overview and numeric match
        if source_type in ['factsheet_consolidated', 'scheme_overview']:
            return "MEDIUM"
        
        # LOW if normalized or other sources
        return "LOW"
    
    def _extract_metric_strict(self, query: str, chunks: List[Dict], scheme_name: Optional[str] = None) -> Optional[Dict]:
        """Extract metric using strict authority-based rules"""
        query_lower = query.lower()
        
        # Identify field from query
        field = self._identify_field_from_query(query)
        if not field:
            return None
        
        # FIRST: Try direct lookup from field-specific chunks (fastest, most accurate)
        # These chunks have format: "Exit Load: 1.00%. Source: ..."
        for chunk in chunks:
            chunk_field = chunk.get('field', '')
            chunk_text = chunk.get('chunk_text') or chunk.get('text', '')
            
            # If this chunk is specifically for the requested field, use it directly
            if chunk_field == field:
                # Extract value from chunk_text (format: "Field Name: Value. Source: ...")
                # Try multiple patterns
                value_match = None
                patterns = [
                    r':\s*([^.]*?)(?:\.|Source)',  # "Field: Value. Source"
                    r':\s*([^.]*?)(?:\.|$)',        # "Field: Value."
                    r'\(TER\):\s*([^.]*?)(?:\.|Source)',  # "TER): Value. Source"
                ]
                
                for pattern in patterns:
                    value_match = re.search(pattern, chunk_text, re.IGNORECASE)
                    if value_match:
                        break
                
                if value_match:
                    value = value_match.group(1).strip()
                    # Clean up value (remove extra spaces, normalize)
                    value = re.sub(r'\s+', ' ', value).strip()
                    
                    # Get source info
                    source_id = chunk.get('source_id', '')
                    source_type = chunk.get('source_type', '')
                    source_url = chunk.get('source_url', '')
                    last_updated = chunk.get('last_fetched_date', '2025-11-17')
                    
                    # Format answer - clean and beautiful
                    field_display = field.replace('_', ' ').title()
                    # Make it more natural
                    if field == 'exit_load':
                        field_display = "Exit Load"
                    elif field == 'expense_ratio':
                        field_display = "Total Expense Ratio (TER)"
                    elif field == 'minimum_sip':
                        field_display = "Minimum SIP"
                    elif field == 'lock_in':
                        field_display = "Lock-in Period"
                    elif field == 'benchmark':
                        field_display = "Benchmark"
                    elif field == 'riskometer':
                        field_display = "Riskometer"
                    
                    if scheme_name:
                        answer = f"The {field_display.lower()} for {scheme_name} is {value}."
                    else:
                        answer = f"The {field_display.lower()} is {value}."
                    
                    # Calculate confidence based on source
                    if 'sid' in source_type.lower():
                        confidence = 'HIGH'
                    elif 'kim' in source_type.lower():
                        confidence = 'HIGH'
                    elif 'factsheet' in source_type.lower():
                        confidence = 'MEDIUM'
                    else:
                        confidence = 'MEDIUM'
                    
                    return {
                        'answer': answer,
                        'source_type': source_type,
                        'source_id': source_id,
                        'source_url': source_url,
                        'excerpt': chunk_text[:150],  # First 150 chars
                        'last_updated': last_updated,
                        'confidence': confidence
                    }
        
        # SECOND: If no field-specific chunk found, try direct lookup from chunks_clean.jsonl
        # This bypasses retrieval issues and goes straight to the source
        if not chunks or not any(c.get('field') == field for c in chunks):
            direct_chunk = self._get_direct_chunk_from_file(field, scheme_name)
            if direct_chunk:
                chunk_text = direct_chunk.get('chunk_text', '')
                value_match = re.search(r':\s*([^.]*?)(?:\.|Source)', chunk_text, re.IGNORECASE)
                if value_match:
                    value = value_match.group(1).strip()
                    value = re.sub(r'\s+', ' ', value).strip()
                    
                    # Format answer - clean and beautiful (use constants)
                    field_display = FIELD_DISPLAY_NAMES.get(field, field.replace('_', ' ').title())
                    
                    # Get scheme name from constants
                    scheme_tag_from_chunk = direct_chunk.get('scheme_tag', '')
                    scheme_name_used = scheme_name or SCHEME_DISPLAY_NAMES.get(scheme_tag_from_chunk, scheme_tag_from_chunk.replace('_', ' '))
                    if scheme_name_used:
                        answer = f"The {field_display.lower()} for {scheme_name_used} is {value}."
                    else:
                        answer = f"The {field_display.lower()} is {value}."
                    
                    source_type = direct_chunk.get('source_type', '')
                    confidence = 'HIGH' if 'sid' in source_type.lower() or 'kim' in source_type.lower() else 'MEDIUM'
                    
                    return {
                        'answer': answer,
                        'source_type': source_type,
                        'source_id': direct_chunk.get('source_id', ''),
                        'source_url': direct_chunk.get('source_url', ''),
                        'excerpt': chunk_text[:150],
                        'last_updated': direct_chunk.get('last_fetched_date', '2025-11-17'),
                        'confidence': confidence
                    }
        
        # FALLBACK: Use regex extraction from chunks (original method)
        # Identify metric queries
        metric_keywords = [
            'minimum sip', 'minimum lumpsum', 'exit load', 'lock-in', 'lock in',
            'expense ratio', 'ter', 'benchmark', 'riskometer', 'nav', 'amount',
            'percentage', 'percent', '%'
        ]
        
        if not any(kw in query_lower for kw in metric_keywords):
            return None
        
        # Filter chunks by scheme if specified
        if scheme_name:
            scheme_tag = None
            scheme_name_lower = scheme_name.lower()
            
            # Map query scheme name to actual scheme and tag
            for s in self.actual_schemes:
                s_lower = s.lower()
                # Check if scheme_name matches any part of actual scheme name
                if (scheme_name_lower in s_lower or 
                    s_lower in scheme_name_lower or
                    # Special cases
                    (scheme_name_lower == 'elss' and ('elss' in s_lower or 'taxsaver' in s_lower or 'tax saver' in s_lower)) or
                    (scheme_name_lower == 'taxsaver' and ('elss' in s_lower or 'taxsaver' in s_lower or 'tax saver' in s_lower)) or
                    (scheme_name_lower == 'tax saver' and ('elss' in s_lower or 'taxsaver' in s_lower or 'tax saver' in s_lower))):
                    # Map to scheme tag
                    if 'large cap' in s_lower:
                        scheme_tag = 'LARGE_CAP'
                    elif 'flexi cap' in s_lower:
                        scheme_tag = 'FLEXI_CAP'
                    elif 'elss' in s_lower or 'taxsaver' in s_lower or 'tax saver' in s_lower:
                        scheme_tag = 'ELSS'
                    elif 'hybrid' in s_lower:
                        scheme_tag = 'HYBRID'
                    break
            
            if scheme_tag:
                chunks = [c for c in chunks if c.get('scheme_tag', '').upper() == scheme_tag.upper()]
        
        # Extract numeric patterns from all chunks
        candidate_chunks = []
        for chunk in chunks:
            chunk_text = chunk.get('text', '')
            source_id = chunk.get('source_id', '')
            # Get source_type from chunk or metadata
            source_type = chunk.get('source_type', '')
            if not source_type and source_id in self.source_metadata:
                source_type = self.source_metadata[source_id].get('source_type', '')
            
            # For TER, skip chunks with "reduction" in them (unless it's the only match)
            if field == 'expense_ratio' and 'reduction' in chunk_text.lower() and len(chunks) > 1:
                # Skip reduction mentions unless it's the only option
                continue
            
            # For riskometer, prioritize AMFI sources and factsheet sources
            if field == 'riskometer':
                # Boost AMFI riskometer sources
                if 'amfi' in source_id.lower() and 'riskometer' in chunk_text.lower():
                    # This is a good riskometer source
                    pass
                elif 'expense' in chunk_text.lower() and 'riskometer' not in chunk_text.lower():
                    # Skip expense ratio chunks when looking for riskometer
                    if len(chunks) > 1:
                        continue
            
            # Try to extract numeric pattern
            numeric_match = self._extract_numeric_pattern(chunk_text, field)
            if numeric_match:
                # For TER, double-check we didn't extract a reduction amount
                if field == 'expense_ratio':
                    match_context = chunk_text[max(0, numeric_match['match_start']-50):min(len(chunk_text), numeric_match['match_end']+50)].lower()
                    if 'reduction' in match_context and len(chunks) > 1:
                        # This is likely a reduction amount, skip it
                        continue
                
                candidate_chunks.append({
                    'chunk': chunk,
                    'numeric_match': numeric_match,
                    'source_type': source_type,
                    'source_id': source_id,
                    'authority_priority': self._get_source_authority_priority(source_type)
                })
        
        if not candidate_chunks:
            return None
        
        # Sort by authority priority (lower number = higher priority)
        candidate_chunks.sort(key=lambda x: x['authority_priority'])
        
        # If same priority, prefer more recent (would need last_updated, but we'll use first match for now)
        # Select the highest authority chunk
        best_candidate = candidate_chunks[0]
        
        chunk = best_candidate['chunk']
        numeric_match = best_candidate['numeric_match']
        source_type = best_candidate['source_type']
        source_id = best_candidate['source_id']
        
        # Normalize value
        normalized_value = self._normalize_metric_value(numeric_match['value'], field)
        
        # Calculate confidence
        confidence = self._calculate_confidence(source_type, True, normalized_value != numeric_match['value'])
        
        # Get source metadata
        source_url = chunk.get('source_url', '')
        # Try to get last_updated from source metadata
        source_meta = self.source_metadata.get(source_id, {})
        last_updated = source_meta.get('last_fetched_date', chunk.get('last_updated', chunk.get('last_fetched_date', '2025-11-18')))
        # Normalize date format (MM/DD/YYYY -> YYYY-MM-DD)
        if '/' in str(last_updated):
            try:
                from datetime import datetime
                date_obj = datetime.strptime(str(last_updated), '%m/%d/%Y')
                last_updated = date_obj.strftime('%Y-%m-%d')
            except:
                pass
        
        # Format excerpt (show full text, no truncation)
        excerpt = numeric_match['excerpt']
        if len(excerpt) < 20:
            # Pad with context
            chunk_text = chunk.get('text', '')
            match_start = numeric_match['match_start']
            start = max(0, match_start - 10)
            end = min(len(chunk_text), match_start + 70)
            excerpt = chunk_text[start:end].strip()
        
        # Format answer according to template
        field_name = field.replace('_', ' ').title()
        if scheme_name:
            answer_line = f"{field_name} ({scheme_name}): {normalized_value}"
        else:
            answer_line = f"{field_name}: {normalized_value}"
        
        # Add condition if exit load
        if field == 'exit_load':
            chunk_text = chunk.get('text', '').lower()
            # Only check for "no exit load" if the extracted value is actually "nil" or "0"
            if normalized_value.lower() in ['nil', '0', '0.00%', '0%'] or ('no exit load' in chunk_text and '1.00%' not in chunk_text):
                answer_line = f"Exit Load ({scheme_name if scheme_name else 'Fund'}): Nil (No exit load)"
            elif 'year' in chunk_text:
                year_match = re.search(r'(\d+)\s*(?:year|years)', chunk.get('text', ''), re.IGNORECASE)
                if year_match:
                    answer_line += f" if redeemed within {year_match.group(1)} year"
                # Check for "after X year" condition
                after_match = re.search(r'after\s*(\d+)\s*(?:year|years)', chunk.get('text', ''), re.IGNORECASE)
                if after_match:
                    answer_line += f". No exit load after {after_match.group(1)} year"
        
        return {
            'answer': answer_line,
            'source_type': source_type,
            'source_id': source_id,
            'excerpt': excerpt,
            'last_updated': last_updated,
            'confidence': confidence,
            'source_url': source_url
        }
    
    def _handle_comparison_query(self, query: str, chunks: List[Dict], scheme_name: Optional[str] = None) -> Optional[Dict]:
        """Handle comparison queries (SID vs KIM, etc.)"""
        query_lower = query.lower()
        field = self._identify_field_from_query(query)
        if not field:
            return None
        
        # Extract from SID
        sid_chunks = [c for c in chunks if 'sid' in c.get('source_id', '').lower() or c.get('source_type', '') == 'sid_pdf']
        sid_result = None
        if sid_chunks:
            sid_result = self._extract_metric_strict(query, sid_chunks, scheme_name)
        
        # Extract from KIM
        kim_chunks = [c for c in chunks if 'kim' in c.get('source_id', '').lower() or c.get('source_type', '') == 'kim_pdf']
        kim_result = None
        if kim_chunks:
            kim_result = self._extract_metric_strict(query, kim_chunks, scheme_name)
        
        # Extract from factsheet
        factsheet_chunks = [c for c in chunks if 'factsheet' in c.get('source_id', '').lower() or c.get('source_type', '') == 'factsheet_consolidated']
        factsheet_result = None
        if factsheet_chunks:
            factsheet_result = self._extract_metric_strict(query, factsheet_chunks, scheme_name)
        
        # Compare results
        if sid_result and (kim_result or factsheet_result):
            other_result = kim_result if kim_result else factsheet_result
            other_source = 'KIM' if kim_result else 'Factsheet'
            
            sid_parts = sid_result['answer'].split(':')
            other_parts = other_result['answer'].split(':')
            sid_value = sid_parts[-1].strip() if sid_parts else sid_result['answer'].strip()
            other_value = other_parts[-1].strip() if other_parts else other_result['answer'].strip()
            
            if sid_value == other_value:
                answer = f"Answer: {field.replace('_', ' ').title()} is consistent: {sid_value} (same in SID and {other_source}).\n"
                answer += f"SID Source: {sid_result['source_type']}/{sid_result['source_id']} — excerpt: \"{sid_result['excerpt']}\"\n"
                answer += f"{other_source} Source: {other_result['source_type']}/{other_result['source_id']} — excerpt: \"{other_result['excerpt']}\"\n"
                answer += f"Last updated: {sid_result['last_updated']}."
            else:
                answer = f"Answer: {field.replace('_', ' ').title()} differs: SID shows {sid_value}, {other_source} shows {other_value}.\n"
                answer += f"SID Source: {sid_result['source_type']}/{sid_result['source_id']} — excerpt: \"{sid_result['excerpt']}\"\n"
                answer += f"{other_source} Source: {other_result['source_type']}/{other_result['source_id']} — excerpt: \"{other_result['excerpt']}\"\n"
                answer += f"Last updated: {sid_result['last_updated']}."
            
            return {
                'answer': answer,
                'source_url': sid_result['source_url'],
                'refused': False,
                'query_type': 'comparison',
                'confidence': sid_result['confidence']
            }
        
        return None
    
    def _handle_contradiction_query(self, query: str, chunks: List[Dict], scheme_name: Optional[str] = None) -> Optional[Dict]:
        """Handle contradiction detection queries"""
        # Extract the statement to check
        query_lower = query.lower()
        if 'no exit load after' in query_lower:
            # Search for text that contradicts "No exit load after X year"
            year_match = re.search(r'after\s*(\d+)\s*(?:year|years)', query_lower)
            if year_match:
                year = year_match.group(1)
                # Look for exit load mentions in chunks
                for chunk in chunks:
                    chunk_text = chunk.get('text', '').lower()
                    # Check if there's exit load mentioned for after that year
                    if f'exit load' in chunk_text and f'after {year}' in chunk_text:
                        # Check if it says "no exit load"
                        if 'no exit load' in chunk_text or 'nil' in chunk_text:
                            answer = f"Answer: No contradiction found. Text confirms: No exit load after {year} year.\n"
                        else:
                            # Check for exit load amount after that year
                            exit_load_match = re.search(r'exit\s*load[^.]*?after\s*' + year + r'[^.]*?([0-9.]+)\s?%', chunk_text)
                            if exit_load_match:
                                answer = f"Answer: Contradiction found. Text shows exit load of {exit_load_match.group(1)}% after {year} year, contradicting 'No exit load after {year} year'.\n"
                            else:
                                answer = f"Answer: No contradiction found. Text does not mention exit load after {year} year.\n"
                        
                        excerpt = chunk.get('text', '')[:80]
                        answer += f"Source: {chunk.get('source_type', 'unknown')}/{chunk.get('source_id', 'unknown')} — excerpt: \"{excerpt}\"\n"
                        answer += f"Last updated: {chunk.get('last_updated', '2025-11-17')}."
                        
                        return {
                            'answer': answer,
                            'source_url': chunk.get('source_url', ''),
                            'refused': False,
                            'query_type': 'contradiction',
                            'confidence': 'MEDIUM'
                        }
        
        return None
    
    def _handle_canonical_facts_query(self, query: str, chunks: List[Dict], scheme_name: Optional[str] = None) -> Optional[Dict]:
        """Handle canonical facts row queries"""
        # Extract requested fields
        fields = ['min_sip', 'exit_load', 'ter', 'lock_in']
        if 'min_sip' in query.lower() or 'minimum sip' in query.lower():
            fields.append('minimum_sip')
        
        facts = {}
        for field in fields:
            # Map field names
            field_map = {
                'min_sip': 'minimum_sip',
                'ter': 'expense_ratio',
                'lock_in': 'lock_in'
            }
            query_field = field_map.get(field, field)
            
            # Create a query for this field
            field_query = f"What is the {query_field.replace('_', ' ')} of {scheme_name or 'the fund'}"
            result = self._extract_metric_strict(field_query, chunks, scheme_name)
            if result:
                answer_parts = result['answer'].split(':')
                value = answer_parts[-1].strip() if answer_parts else result['answer'].strip()
                facts[field] = value
        
        if facts:
            facts_row = ", ".join([f"{k}: {v}" for k, v in facts.items()])
            answer = f"Answer: Canonical facts for {scheme_name or 'Fund'}: {facts_row}.\n"
            answer += f"Source: Multiple sources."
            
            return {
                'answer': answer,
                'source_url': chunks[0].get('source_url', '') if chunks else '',
                'refused': False,
                'query_type': 'canonical',
                'confidence': 'MEDIUM'
            }
        
        return None
    
    def _handle_business_rule_query(self, query: str, chunks: List[Dict], scheme_name: Optional[str] = None) -> Optional[Dict]:
        """Handle business rule queries (can I redeem, etc.)"""
        query_lower = query.lower()
        
        # Check for lock-in questions
        if 'redeem' in query_lower and ('elss' in query_lower or scheme_name and 'elss' in scheme_name.lower()):
            # Extract time period
            time_match = re.search(r'(\d+)\s*(?:month|months)', query_lower)
            if time_match:
                months = int(time_match.group(1))
                # Check lock-in period
                lock_in_result = self._extract_metric_strict("What is the lock-in period", chunks, scheme_name)
                if lock_in_result:
                    lock_in_value = lock_in_result['answer']
                    # Extract years from lock-in
                    year_match = re.search(r'(\d+)\s*years', lock_in_value, re.IGNORECASE)
                    if year_match:
                        lock_in_years = int(year_match.group(1))
                        lock_in_months = lock_in_years * 12
                        
                        if months < lock_in_months:
                            answer = f"Answer: No, you cannot redeem after {months} months. HDFC ELSS has a statutory lock-in period of {lock_in_years} years ({lock_in_months} months). Redemption is only allowed after the lock-in period.\n"
                            answer += f"Source: {lock_in_result['source_type']}/{lock_in_result['source_id']} — excerpt: \"{lock_in_result['excerpt']}\"\n"
                            answer += f"Last updated: {lock_in_result['last_updated']}."
                            
                            return {
                                'answer': answer,
                                'source_url': lock_in_result['source_url'],
                                'refused': False,
                                'query_type': 'business_rule',
                                'confidence': lock_in_result['confidence']
                            }
        
        return None
    
    def _apply_response_style(self, answer: str, style: str, query_type: str) -> str:
        """Apply response style (brief, detailed, beginner, etc.)"""
        if style == "brief":
            # Extract key points, limit to 2-3 sentences
            sentences = answer.split('. ')
            if len(sentences) > 3:
                answer = '. '.join(sentences[:3]) + '.'
        
        elif style == "detailed":
            # Ensure comprehensive answer (already handled by LLM, but can enhance)
            if len(answer) < 200:
                # Add more context if answer is too short
                pass  # Can be enhanced
        
        elif style == "beginner":
            # Simplify language, add explanations
            # Replace technical terms with simpler ones
            replacements = {
                'expense ratio': 'expense ratio (the annual fee charged by the fund)',
                'exit load': 'exit load (a charge when you withdraw money early)',
                'lock-in period': 'lock-in period (the minimum time you must keep your investment)',
                'benchmark': 'benchmark (a standard index used to compare fund performance)'
            }
            for term, explanation in replacements.items():
                if term in answer.lower() and explanation not in answer.lower():
                    answer = answer.replace(term, explanation)
        
        return answer
    
    def _identify_field_from_query(self, query: str) -> Optional[str]:
        """Identify field from query"""
        query_lower = query.lower()
        
        field_map = {
            'exit_load': ['exit load', 'redemption charge', 'exit charge'],
            'expense_ratio': ['expense ratio', 'ter', 'total expense ratio'],
            'minimum_sip': ['minimum sip', 'min sip', 'minimum investment'],
            'min_lumpsum': ['minimum lumpsum', 'min lumpsum', 'minimum application', 'min application'],
            'lock_in': ['lock-in', 'lock in', 'lockin'],
            'benchmark': ['benchmark', 'benchmark index'],
            'riskometer': ['riskometer', 'risk-o-meter', 'risk meter']
        }
        
        for field, keywords in field_map.items():
            if any(kw in query_lower for kw in keywords):
                return field
        
        return None
    
    def _validate_answer_against_schemes(self, answer: str) -> str:
        """Validate answer doesn't mention schemes we don't have"""
        # Known fund names that might appear in hallucinated answers
        invalid_funds = [
            "HDFC Banking & Financial Services Fund",
            "HDFC Business Cycle Fund",
            "HDFC Value Fund",
            "HDFC Defence Fund",
            "HDFC Dividend Yield Fund",
            "HDFC Focused 30 Fund",
            "HDFC Housing Opportunities Fund",
            "HDFC Infrastructure Fund",
            "HDFC Large and Mid Cap Fund",
            "HDFC Manufacturing Fund",
            "HDFC Mid-Cap Opportunities Fund",
            "HDFC MNC Fund",
            "HDFC Multi Cap Fund",
            "HDFC Non-Cyclical Consumption Fund",
            "HDFC Non-Cyclical",
            "HDFC Hybrid Debt Fund",
            "HDFC Income Fund",
            "HDFC Liquid Fund",
            "HDFC Long Duration Debt Fund",
            "HDFC Low Duration Fund",
            "HDFC Medium Term Debt Fund",
            "HDFC Money Market Fund",
            "HDFC Multi-Asset Fund",
            "HDFC Retirement Saving",
            "HDFC Retirement Saving fund",
            "HDFC Children's Fund",
            "HDFC Technology Fund",
            "HDFC Arbitrage Fund",
        ]
        
        answer_lower = answer.lower()
        mentioned_invalid = []
        
        for invalid_fund in invalid_funds:
            if invalid_fund.lower() in answer_lower:
                mentioned_invalid.append(invalid_fund)
        
        # Check if answer contains a list of funds (bullet points, asterisks, etc.)
        has_fund_list = bool(re.search(r'[*•]\s*HDFC\s+\w+', answer, re.IGNORECASE))
        
        if mentioned_invalid or has_fund_list:
            # If answer contains invalid funds or looks like a fund list, replace entirely
            correct_schemes = ", ".join(self.actual_schemes)
            # Check if this is a "what funds" type query
            if "fund" in answer_lower and any(phrase in answer_lower for phrase in ["have information", "available", "know about", "following funds"]):
                schemes_list = correct_schemes.split(", ")
                return (
                    f"I have information about the following **4 HDFC mutual fund schemes**:\n\n"
                    + "\n".join([f"- **{scheme}**" for scheme in schemes_list])
                    + "\n\nI can answer factual questions about **expense ratios**, **exit loads**, **fund managers**, **investment strategies**, "
                    "and other details for these schemes. I provide information only, not investment advice."
                )
            else:
                # Remove invalid mentions
                for invalid in mentioned_invalid:
                    answer = re.sub(re.escape(invalid), "", answer, flags=re.IGNORECASE)
                # Remove any fund list patterns
                answer = re.sub(r'[*•]\s*HDFC\s+[^\n]+', '', answer, flags=re.IGNORECASE)
                answer = re.sub(r'HDFC\s+[A-Z][a-z]+\s+Fund', '', answer, flags=re.IGNORECASE)
        
        return answer
    
    def _post_process_answer(self, answer: str, query_type: str, context: str, query: str = "") -> str:
        """
        Post-process answer to extract and format specific details
        
        Args:
            answer: Raw answer from LLM
            query_type: Type of query (entity, metric, list, etc.)
            context: Original context used
            
        Returns:
            Improved answer with extracted details
        """
        # If answer says "not found" or is too vague, try to extract from context
        answer_lower = answer.lower()
        if any(phrase in answer_lower for phrase in ['not in the context', 'not found', 'not available', 'does not contain']):
            # Try to extract from context directly
            extracted = self._extract_from_context_directly(query_type, context)
            if extracted:
                return extracted
        
        # For metric queries, ensure numbers are clearly stated
        if query_type == 'metric':
            # Check if answer has numbers (but filter out page numbers, years, etc.)
            has_valid_number = bool(re.search(r'\d+\.\d+%?|\d+%', answer))  # Decimal or percentage
            
            if not has_valid_number:
                # Try to find number in context near metric keywords
                query_lower = query.lower()
                if 'expense' in query_lower or 'ter' in query_lower:
                    # Look for expense ratio patterns
                    ter_patterns = [
                        r'(?:expense ratio|ter|total expense ratio)[:\s]+(\d+\.\d+%?)',
                        r'(\d+\.\d+%?)\s*(?:expense ratio|ter|total expense ratio)',
                    ]
                    for pattern in ter_patterns:
                        match = re.search(pattern, context[:1000], re.IGNORECASE)
                        if match:
                            answer = answer + f" The expense ratio is {match.group(1)}."
                            break
                elif 'exit load' in query_lower:
                    # Look for exit load patterns
                    exit_patterns = [
                        r'(?:exit load|redemption charge)[:\s]+(\d+\.?\d*%?)',
                        r'(\d+\.?\d*%?)\s*(?:exit load|redemption charge)',
                    ]
                    for pattern in exit_patterns:
                        match = re.search(pattern, context[:1000], re.IGNORECASE)
                        if match:
                            answer = answer + f" The exit load is {match.group(1)}."
                            break
        
        # For entity queries, extract manager name cleanly and format properly
        if query_type == 'entity':
            query_lower_entity = query.lower()
            if 'manager' in query_lower_entity or 'manages' in query_lower_entity:
                # Clean context first
                context_clean = self._clean_context_for_entity(context)
                
                # Extract manager name with improved patterns
                manager_patterns = [
                    r'(?:Fund\s+Manager|Manager|Investment\s+Manager)[:\s]+(?:Mr\.|Ms\.|Mrs\.|Dr\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)[,\s]+(?:Fund\s+Manager|Manager|Investment\s+Manager|Equity\s+Analyst)',
                    r'(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                ]
                
                found_name = None
                for pattern in manager_patterns:
                    match = re.search(pattern, context_clean[:2000], re.IGNORECASE)
                    if match:
                        name = match.group(1).strip()
                        # Validate it's a real name (2 words, each > 2 chars)
                        if len(name.split()) == 2 and all(len(word) > 2 for word in name.split()):
                            found_name = name
                            break
                
                # Extract scheme name from query
                scheme_name = None
                if 'flexi cap' in query_lower_entity:
                    scheme_name = "HDFC Flexi Cap Fund"
                elif 'large cap' in query_lower_entity:
                    scheme_name = "HDFC Large Cap Fund"
                elif 'elss' in query_lower_entity or 'taxsaver' in query_lower_entity:
                    scheme_name = "HDFC TaxSaver (ELSS)"
                elif 'hybrid' in query_lower_entity:
                    scheme_name = "HDFC Hybrid Equity Fund"
                
                # If we found a name, format answer cleanly
                if found_name:
                    if scheme_name:
                        answer = f"The **Fund Manager** of **{scheme_name}** is **{found_name}**."
                    else:
                        answer = f"The **Fund Manager** is **{found_name}**."
                elif not answer or len(answer.strip()) < 20:
                    # If no name found and answer is poor, try direct extraction
                    extracted = self._extract_from_context_directly('entity', context_clean, query)
                    if extracted and 'manager' in extracted.lower():
                        answer = extracted
        
        # For list queries, format as list if it's a paragraph
        if query_type == 'list':
            # Check if answer has list-like structure
            if not re.search(r'[0-9]+\.|•|-\s+[A-Z]', answer):
                # Try to extract list items from context
                list_items = re.findall(r'([A-Z][^.!?]*(?:\([^)]+\))?)', context[:800])
                if len(list_items) >= 2:
                    # Format as list
                    formatted = "The top items are: " + ", ".join(list_items[:5])
                    if formatted not in answer:
                        answer = answer + " " + formatted
        
        return answer
    
    def _improve_answer_presentation(self, answer: str, query: str, query_type: str, context: str, scheme_name: Optional[str] = None) -> str:
        """
        Improve answer presentation - fix abrupt endings, wrong fund names, poor formatting
        """
        if not answer or len(answer.strip()) < 20:
            return answer
        
        query_lower = query.lower()
        answer_lower = answer.lower()
        
        # Clean up artifacts from chunk separators
        answer = re.sub(r'\s*---\s*', ' ', answer)  # Remove separator artifacts
        answer = re.sub(r'\s+', ' ', answer)  # Clean up multiple spaces
        
        # Remove document headers and metadata
        answer = re.sub(r'SCHEME INFORMATION DOCUMENT\s+', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'DIRECT REGULAR\s*', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'An open ended hybrid scheme\s+', 'An open-ended hybrid scheme ', answer, flags=re.IGNORECASE)
        
        # Fix incomplete sentences (ending with numbers or incomplete words)
        if answer.rstrip() and not answer.rstrip()[-1] in '.!?':
            # Check if it ends with incomplete sentence
            last_sentence = answer.split('.')[-1].strip() if '.' in answer else answer.strip()
            if len(last_sentence) > 20 and not last_sentence.endswith(('.', '!', '?')):
                # Try to complete from context
                if context:
                    # Look for continuation
                    last_words = last_sentence.split()[-3:]
                    search_phrase = " ".join(last_words).lower()
                    for sentence in context.split('.'):
                        if search_phrase in sentence.lower() and len(sentence) > len(search_phrase) + 30:
                            continuation = sentence[sentence.lower().find(search_phrase) + len(search_phrase):].strip()
                            if continuation and len(continuation) > 10 and not continuation.startswith(('http', 'www', '---')):
                                answer += " " + continuation
                                break
                # If no continuation found, add period
                if not answer.rstrip().endswith(('.', '!', '?')):
                    answer += "."
        
        # Check if wrong fund mentioned
        wrong_fund = False
        if scheme_name:
            scheme_name_lower = scheme_name.lower()
            for fund in self.actual_schemes:
                if fund.lower() in answer_lower and fund.lower() != scheme_name_lower:
                    wrong_fund = True
                    break
        
        if wrong_fund and scheme_name:
            for fund in self.actual_schemes:
                if fund.lower() != scheme_name.lower() and fund.lower() in answer_lower:
                    answer = re.sub(re.escape(fund), scheme_name, answer, flags=re.IGNORECASE)
        
        # Remove page titles and navigation
        has_poor_formatting = any(phrase in answer_lower for phrase in [
            'nav, portfolio and performance',
            'direct growth',
            'equity direct regular',
            'hdfc large cap fund direct growth'
        ])
        
        if has_poor_formatting:
            answer = re.sub(r'HDFC\s+Large\s+Cap\s+Fund\s+Direct\s+Growth\s*-\s*NAV.*?Performance', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'HDFC\s+Mutual\s+Funds\s+HDFC\s+', 'HDFC ', answer, flags=re.IGNORECASE)
            answer = re.sub(r'Equity\s+DIRECT\s+REGULAR', '', answer, flags=re.IGNORECASE)
        
        # Clean up multiple spaces and normalize
        answer = re.sub(r'\s+', ' ', answer)
        answer = answer.strip()
        
        # Ensure proper ending
        if answer and not answer.rstrip()[-1] in '.!?':
            answer += "."
        
        return answer
    
    def _extract_from_context_directly(self, query_type: str, context: str, query: str = "") -> str:
        """Extract answer directly from context when LLM says not found"""
        if query_type == 'metric':
            # Look for numbers with metric keywords
            patterns = [
                r'(?:expense ratio|ter|total expense ratio)[:\s]+(\d+\.?\d*%?)',
                r'(?:exit load)[:\s]+(\d+\.?\d*%?)',
                r'(?:minimum sip|minimum investment)[:\s]+(?:Rs\.?|₹)?\s*(\d+(?:,\d+)*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    return f"The value is {match.group(1)}."
        
        elif query_type == 'entity':
            query_lower = query.lower()
            
            # Check if asking about investors (not fund manager)
            if 'investor' in query_lower:
                # Look for investor information - multiple patterns
                investor_info_parts = []
                
                # Pattern 1: "Ideal for" or "Suitable for"
                ideal_pattern = r'(?:ideal for|suitable for)[:\s]+([^.\n]{10,150})'
                match = re.search(ideal_pattern, context, re.IGNORECASE)
                if match:
                    ideal_text = match.group(1).strip()
                    # Clean up common artifacts
                    ideal_text = re.sub(r'\s+', ' ', ideal_text)
                    if len(ideal_text) > 5:
                        investor_info_parts.append(ideal_text)
                
                # Pattern 2: "This product is suitable for investors who are seeking"
                seeking_pattern = r'(?:suitable for investors who are seeking|investors who are seeking)[:\s]+([^~]{20,300})'
                match = re.search(seeking_pattern, context, re.IGNORECASE)
                if match:
                    seeking_text = match.group(1).strip()
                    seeking_text = re.sub(r'\s+', ' ', seeking_text)
                    if len(seeking_text) > 10:
                        investor_info_parts.append(seeking_text)
                
                # Pattern 3: Investment objective that mentions target investors
                objective_pattern = r'(?:investment objective|aims to|designed for)[:\s]+([^.\n]{30,200})'
                match = re.search(objective_pattern, context, re.IGNORECASE)
                if match:
                    obj_text = match.group(1).strip()
                    obj_text = re.sub(r'\s+', ' ', obj_text)
                    if 'investor' in obj_text.lower() or 'suitable' in obj_text.lower():
                        investor_info_parts.append(obj_text)
                
                if investor_info_parts:
                    combined = ". ".join(investor_info_parts[:2])  # Take first 2 matches
                    return f"The HDFC Hybrid Equity Fund is suitable for: {combined[:300]}."
                
                return "I don't have specific information about the investor base in my sources. The scheme is a hybrid equity fund that invests in both equity and debt instruments, suitable for investors seeking long-term wealth creation."
            
            # Look for fund manager names (multiple patterns) - IMPROVED
            manager_patterns = [
                r'(?:Fund\s+Manager|Manager|Investment\s+Manager)[:\s]+(?:Mr\.|Ms\.|Mrs\.|Dr\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)[,\s]+(?:Fund\s+Manager|Manager|Investment\s+Manager|Equity\s+Analyst)',
                r'(?:Name\s+of\s+the\s+Fund\s+Manager|Fund\s+Manager\s+Name)[:\s]+(?:Mr\.|Ms\.|Mrs\.|Dr\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            ]
            
            # Clean context first for better matching
            context_clean = re.sub(r'Exit\s+Load.*?\.', '', context, flags=re.IGNORECASE | re.DOTALL)
            context_clean = re.sub(r'Top\s+\d+\s+Holdings.*?Downloads', '', context_clean, flags=re.IGNORECASE | re.DOTALL)
            context_clean = re.sub(r'OVERSEAS.*?\.', '', context_clean, flags=re.IGNORECASE | re.DOTALL)
            
            for pattern in manager_patterns:
                match = re.search(pattern, context_clean[:3000], re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    # Validate it's a real name (2 words, each > 2 chars)
                    if len(name.split()) == 2 and all(len(word) > 2 for word in name.split()):
                        # Extract scheme name from query if available
                        scheme_name = None
                        if 'flexi cap' in query.lower():
                            scheme_name = "HDFC Flexi Cap Fund"
                        elif 'large cap' in query.lower():
                            scheme_name = "HDFC Large Cap Fund"
                        elif 'elss' in query.lower() or 'taxsaver' in query.lower():
                            scheme_name = "HDFC TaxSaver (ELSS)"
                        elif 'hybrid' in query.lower():
                            scheme_name = "HDFC Hybrid Equity Fund"
                        
                        # Also try to find tenure if available
                        tenure_match = re.search(r'(?:since|from|tenure)[:\s]+(\d{4})', context_clean[:3000], re.IGNORECASE)
                        if scheme_name:
                            if tenure_match:
                                return f"The **Fund Manager** of **{scheme_name}** is **{name}**, managing since **{tenure_match.group(1)}**."
                            return f"The **Fund Manager** of **{scheme_name}** is **{name}**."
                        else:
                            if tenure_match:
                                return f"The **Fund Manager** is **{name}**, managing since **{tenure_match.group(1)}**."
                            return f"The **Fund Manager** is **{name}**."
        
        return None
    
    def _build_simplified_context(self, scored_chunks: List[Dict], query_type: str, query_lower: str, max_length: int = 10000) -> str:
        """
        Simplified context building (Phase 1 & 2 optimization)
        - Increased context size (10000 chars)
        - Minimal filtering (only obvious noise)
        - Clear chunk separators
        - Let LLM do intelligent filtering
        """
        context_parts = []
        total_length = 0
        
        # Use top 25 chunks (more data for LLM to work with)
        chunks_to_use = scored_chunks[:25]
        
        for item in chunks_to_use:
            chunk = item['chunk']
            chunk_text = chunk.get('text', '')
            
            # Basic cleaning (remove obvious noise only)
            chunk_text = self._clean_chunk_text(chunk_text, query_type)
            
            # Skip if chunk is too short after cleaning
            if len(chunk_text.strip()) < 20:
                continue
            
            # Only filter obviously irrelevant chunks (minimal filtering)
            if self._is_obviously_noise(chunk_text):
                continue
            
            # Add chunk with clear separator
            if total_length + len(chunk_text) + 10 <= max_length:  # +10 for separator
                context_parts.append(chunk_text)
                total_length += len(chunk_text) + 10
            else:
                # Add partial chunk if space allows
                remaining = max_length - total_length - 10
                if remaining > 200:
                    context_parts.append(chunk_text[:remaining])
                break
        
        # Join with clear separators (Phase 2: better chunk separators)
        context = "\n\n---\n\n".join(context_parts)
        
        return context
    
    def _is_obviously_noise(self, text: str) -> bool:
        """
        Minimal noise detection - only filter obviously irrelevant content
        (Phase 1: simplified filtering)
        """
        text_lower = text.lower().strip()
        
        # Only filter if it's CLEARLY not relevant (very strict criteria)
        if len(text_lower) < 10:
            return True
        
        # Filter obvious document lists/navigation
        noise_patterns = [
            r'^downloads?$',
            r'^\.pdf$',
            r'^page \d+ of \d+$',
            r'^table of contents$',
            r'^top \d+ holdings downloads?$',
        ]
        
        for pattern in noise_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Filter if it's mostly document names and dates (metadata chunk)
        if self._is_metadata_chunk(text):
            return True
        
        return False
    
    def _clean_chunk_text(self, text: str, query_type: str) -> str:
        """Clean chunk text by removing document metadata and noise - AGGRESSIVE CLEANING"""
        # Remove SEBI circular references and regulatory citations
        text = re.sub(r'SEBI\s+Circular\s+No\.?\s*[A-Z0-9/]+\s+dated\s+[^,]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'CIR/\d+/\d+/\d+\s+dated\s+[^,]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'MRD/[^,]+dated\s+[^,]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'notifying\s+fram[^.]*', '', text, flags=re.IGNORECASE)
        
        # Remove common document metadata patterns
        # Pattern 1: "p 10 Holdings As on 31 Oct 2025 Downloads..."
        text = re.sub(r'^p\s+\d+\s+[A-Z][^.]*?Downloads[^.]*?', '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Pattern 2: Document lists like "SID - HDFC Large Cap Fund dated May 30, 2025 KIM..."
        text = re.sub(r'(?:SID|KIM|Leaflet|Presentation|Fund Facts)[\s\-:]+[^.]*?(?:dated|as on|as of)[^.]*?(?:\d{4}|\d{1,2}\s+\w+\s+\d{4})[^.]*?', '', text, flags=re.IGNORECASE)
        
        # Pattern 2b: PDF file names and document references - MORE AGGRESSIVE
        text = re.sub(r'[A-Z][^.]*?\.pdf', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Fund\s+Facts\s*-\s*[^.]*?\.pdf', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Presentation\s+[^.]*?\.pdf', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Leaflet\s*\([^)]+\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\.pdf', '', text, flags=re.IGNORECASE)
        
        # Pattern 3: "As on 31 Oct 2025" or "As of September 2025" standalone
        text = re.sub(r'As\s+on\s+\d{1,2}\s+\w+\s+\d{4}', '', text, flags=re.IGNORECASE)
        text = re.sub(r'As\s+of\s+\w+\s+\d{4}', '', text, flags=re.IGNORECASE)
        
        # Pattern 4: Remove standalone dates at start of line
        text = re.sub(r'^\d{1,2}\s+\w+\s+\d{4}\s*', '', text, flags=re.MULTILINE)
        
        # Pattern 5: Remove "Holdings" headers with dates and "Top 10 Holdings Downloads"
        text = re.sub(r'Holdings\s+As\s+on[^.]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Top\s+\d+\s+Holdings\s+Downloads?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Downloads?\s*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'Top\s+\d+\s+Holdings', '', text, flags=re.IGNORECASE)
        
        # For entity queries, remove exit load and other irrelevant info
        if query_type == 'entity':
            text = re.sub(r'Exit\s+Load[^.]*\.', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r'In\s+respect\s+of\s+each\s+purchase[^.]*\.', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r'OVERSEAS[^.]*\.', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r'is\s+payable\s+if[^.]*\.', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r'redeemed\s+/\s+switched-out[^.]*\.', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r'within\s+\d+\s+year[^.]*\.', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove position/role metadata that's not relevant
        text = re.sub(r'Last\s+Position\s+Held:\s*[^.]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\*\s*excluding\s+[^.]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\^\s*Cut-off\s+date[^.]*', '', text, flags=re.IGNORECASE)
        
        # Clean up multiple spaces and fragments
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.\,\:\-\(\)]', '', text)  # Remove special chars except basic punctuation
        text = text.strip()
        
        return text
    
    def _clean_context_for_entity(self, context: str) -> str:
        """Special cleaning for entity queries - removes all irrelevant info"""
        text = context
        # Remove all document metadata
        text = re.sub(r'Top\s+\d+\s+Holdings.*?Downloads', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'Fund\s+Facts.*?\.pdf', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'Exit\s+Load.*?\.', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'OVERSEAS.*?\.', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'is\s+payable\s+if.*?\.', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'In\s+respect\s+of.*?\.', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _clean_answer_metadata(self, answer: str) -> str:
        """Remove metadata, SEBI circulars, and regulatory citations from answer - AGGRESSIVE"""
        if not answer:
            return answer
        
        # Remove SEBI circular references
        answer = re.sub(r'SEBI\s+Circular\s+No\.?\s*[A-Z0-9/]+\s+dated\s+[^,\.]+', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'CIR/\d+/\d+/\d+\s+dated\s+[^,\.]+', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'MRD/[^,\.]+dated\s+[^,\.]+', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'notifying\s+fram[^\.]*', '', answer, flags=re.IGNORECASE)
        
        # Remove document metadata patterns - MORE AGGRESSIVE
        answer = re.sub(r'Top\s+\d+\s+Holdings\s+Downloads?', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'Fund\s+Facts\s*-\s*[^\.]*?\.pdf', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'Presentation\s+[^\.]*?\.pdf', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'Leaflet\s*\([^)]+\)', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'[A-Z][^\.]*?\.pdf', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'\.pdf', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'As\s+of\s+\w+\s+\d{4}', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'As\s+on\s+\d{1,2}\s+\w+\s+\d{4}', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'Downloads?\s*$', '', answer, flags=re.IGNORECASE | re.MULTILINE)
        answer = re.sub(r'Top\s+\d+\s+Holdings', '', answer, flags=re.IGNORECASE)
        
        # Remove position/role metadata
        answer = re.sub(r'Last\s+Position\s+Held:\s*[^\.]*', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'\*\s*excluding\s+[^\.]*', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'\^\s*Cut-off\s+date[^\.]*', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'Franklin\s+Templeton[^\.]*', '', answer, flags=re.IGNORECASE)
        
        # Remove exit load and irrelevant info when asking about fund managers
        if 'manager' in answer.lower() or 'manages' in answer.lower():
            answer = re.sub(r'\s+Exit\s+Load[^\.]*\.', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\s+In\s+respect\s+of\s+each\s+purchase[^\.]*\.', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\s+OVERSEAS[^\.]*\.', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\s+is\s+payable\s+if[^\.]*\.', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\s+redeemed\s+/\s+switched-out[^\.]*\.', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\s+within\s+\d+\s+year[^\.]*\.', '', answer, flags=re.IGNORECASE)
            # Remove fragments like "nd Manager - Equities" or ")00%"
            answer = re.sub(r'nd\s+Manager[^\.]*\.', '', answer, flags=re.IGNORECASE)
            answer = re.sub(r'\)\d+%', '', answer)
            answer = re.sub(r'Equity\s+Analyst\s+and\s+Fund\s+Manager\s+for\s+Overseas', '', answer, flags=re.IGNORECASE)
        
        # Remove trailing commas and clean up
        answer = re.sub(r',\s*,', ',', answer)  # Remove double commas
        answer = re.sub(r'\s+', ' ', answer)  # Multiple spaces to single
        answer = answer.strip()
        
        # Remove leading/trailing punctuation artifacts and fragments
        answer = re.sub(r'^[,\.\s]+', '', answer)
        answer = re.sub(r'[,\.\s]+$', '', answer)
        # Remove single character fragments at start
        answer = re.sub(r'^[a-z]\s+', '', answer, flags=re.IGNORECASE)
        
        return answer
    
    def _is_metadata_chunk(self, text: str) -> bool:
        """Check if chunk is just metadata/document list"""
        text_lower = text.lower()
        
        # If it's mostly document names and dates, it's metadata
        doc_patterns = [
            r'sid\s*-\s*.*?\s+dated',
            r'kim\s*-\s*.*?\s+dated',
            r'leaflet.*?presentation',
            r'fund facts.*?october',
            r'holdings\s+as\s+on.*?downloads',
        ]
        
        doc_matches = sum(1 for pattern in doc_patterns if re.search(pattern, text_lower))
        
        # If more than 2 document patterns, likely metadata
        if doc_matches >= 2:
            return True
        
        # If it's very short and contains mostly dates/document names
        if len(text) < 100 and (doc_matches >= 1 or re.search(r'\d{1,2}\s+\w+\s+\d{4}', text_lower)):
            return True
        
        return False
    
    def _get_direct_chunk_from_file(self, field: str, scheme_name: Optional[str] = None) -> Optional[Dict]:
        """Directly load chunk from chunks_clean.jsonl file (bypasses retrieval)"""
        try:
            import json
            from pathlib import Path
            
            chunks_file = Path("chunks_clean/chunks_clean.jsonl")
            if not chunks_file.exists():
                return None
            
            # Map scheme_name to scheme_tag
            scheme_tag = None
            if scheme_name:
                scheme_name_lower = scheme_name.lower()
                if 'large cap' in scheme_name_lower:
                    scheme_tag = 'LARGE_CAP'
                elif 'flexi cap' in scheme_name_lower:
                    scheme_tag = 'FLEXI_CAP'
                elif 'elss' in scheme_name_lower or 'taxsaver' in scheme_name_lower or 'tax saver' in scheme_name_lower:
                    scheme_tag = 'ELSS'
                elif 'hybrid' in scheme_name_lower:
                    scheme_tag = 'HYBRID'
            
            # Read chunks file and find matching chunk
            # Priority: scheme-specific chunks first, then "ALL" chunks
            scheme_specific_chunk = None
            all_chunk = None
            
            with open(chunks_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    chunk_field = chunk.get('field', '')
                    chunk_scheme = chunk.get('scheme_tag', '')
                    
                    # Match field
                    if chunk_field == field:
                        if scheme_tag and chunk_scheme.upper() == scheme_tag.upper():
                            # Found scheme-specific chunk - return immediately
                            return chunk
                        elif chunk_scheme.upper() == 'ALL':
                            # Store "ALL" chunk as fallback
                            all_chunk = chunk
                        elif not scheme_tag:
                            # No scheme specified, return first match
                            return chunk
            
            # If no scheme-specific chunk found, return "ALL" chunk if available
            if all_chunk:
                return all_chunk
            
            return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Direct chunk lookup failed: {e}")
            return None
    
    def _direct_lookup_manager(self, query: str) -> Optional[str]:
        """Direct lookup of fund manager from overview files as fallback (STEP 3)"""
        query_lower = query.lower()
        
        # Determine scheme from query
        scheme_name = None
        overview_file = None
        
        if 'flexi cap' in query_lower:
            scheme_name = "HDFC Flexi Cap Fund"
            overview_file = "data_processed/amc_flexicap_overview.txt"
        elif 'large cap' in query_lower:
            scheme_name = "HDFC Large Cap Fund"
            overview_file = "data_processed/amc_largecap_overview.txt"
        elif 'elss' in query_lower or 'taxsaver' in query_lower:
            scheme_name = "HDFC TaxSaver (ELSS)"
            overview_file = "data_processed/amc_elss_overview.txt"
        elif 'hybrid' in query_lower:
            scheme_name = "HDFC Hybrid Equity Fund"
            overview_file = "data_processed/amc_hybrid_overview.txt"
        else:
            return None
        
        if not overview_file:
            return None
        
        try:
            # Read overview file and search for manager
            with open(overview_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for manager patterns - prioritize first manager listed (usually Senior Fund Manager)
            # Pattern 1: "Fund Managers\nMs. Roshi Jain\nSenior Fund Manager"
            pattern1 = r'Fund\s+Managers?\s+(?:Ms\.|Mr\.|Mrs\.|Dr\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)'
            match1 = re.search(pattern1, content, re.IGNORECASE | re.MULTILINE)
            if match1:
                name = match1.group(1).strip()
                if len(name.split()) == 2 and all(len(word) > 2 for word in name.split()):
                    return f"The **Fund Manager** of **{scheme_name}** is **{name}**."
            
            # Pattern 2: "Ms. Roshi Jain\nSenior Fund Manager"
            pattern2 = r'(?:Ms\.|Mr\.|Mrs\.|Dr\.)\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*\n\s*Senior\s+Fund\s+Manager'
            match2 = re.search(pattern2, content, re.IGNORECASE | re.MULTILINE)
            if match2:
                name = match2.group(1).strip()
                if len(name.split()) == 2 and all(len(word) > 2 for word in name.split()):
                    return f"The **Fund Manager** of **{scheme_name}** is **{name}**."
            
            # Pattern 3: Fallback - any name followed by "Fund Manager"
            pattern3 = r'(?:Ms\.|Mr\.|Mrs\.|Dr\.)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)[^.]*?(?:Senior\s+)?Fund\s+Manager'
            match3 = re.search(pattern3, content, re.IGNORECASE | re.DOTALL)
            if match3:
                name = match3.group(1).strip()
                if len(name.split()) == 2 and all(len(word) > 2 for word in name.split()):
                    return f"The **Fund Manager** of **{scheme_name}** is **{name}**."
        except Exception as e:
            # If file read fails, return None
            pass
        
        return None

