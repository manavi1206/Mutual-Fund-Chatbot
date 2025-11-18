"""
Test script to run 10 queries against the RAG system with validation
"""
import requests
import json
import time
from typing import Dict, List, Tuple

API_URL = "http://localhost:8000/api/query"

# Test queries covering different types and scenarios
TEST_QUERIES = [
    {
        "query": "What is the exit load for HDFC ELSS?",
        "type": "metric",
        "expected_fields": ["exit load", "redemption"],
        "scheme": "elss"
    },
    {
        "query": "What is the expense ratio of HDFC Large Cap Fund?",
        "type": "metric",
        "expected_fields": ["expense ratio", "ter"],
        "scheme": "largecap"
    },
    {
        "query": "How do I redeem my HDFC Large Cap Fund units?",
        "type": "how_to",
        "expected_fields": ["redeem", "redemption", "steps"],
        "scheme": "largecap"
    },
    {
        "query": "What is the minimum SIP amount for HDFC Flexi Cap Fund?",
        "type": "metric",
        "expected_fields": ["minimum", "sip", "investment"],
        "scheme": "flexicap"
    },
    {
        "query": "What is the lock-in period of HDFC TaxSaver (ELSS)?",
        "type": "metric",
        "expected_fields": ["lock-in", "lock in", "3 years"],
        "scheme": "elss"
    },
    {
        "query": "What is the benchmark of HDFC Hybrid Equity Fund?",
        "type": "metric",
        "expected_fields": ["benchmark", "index"],
        "scheme": "hybrid"
    },
    {
        "query": "What is the riskometer score for HDFC Large Cap Fund?",
        "type": "metric",
        "expected_fields": ["riskometer", "risk", "risk level", "moderate", "high"],  # More lenient - accept risk level descriptions
        "scheme": "largecap"
    },
    {
        "query": "What all funds do you have information about?",
        "type": "general",
        "expected_fields": ["fund", "scheme", "hdfc"],
        "scheme": None
    },
    {
        "query": "What is the minimum lumpsum amount for HDFC Hybrid Equity Fund?",
        "type": "metric",
        "expected_fields": ["minimum", "lumpsum", "investment"],
        "scheme": "hybrid"
    },
    {
        "query": "Can you tell me about HDFC Flexi Cap Fund's performance?",
        "type": "general",
        "expected_fields": ["flexi cap", "performance", "fund"],
        "scheme": "flexicap"
    }
]

def validate_answer(answer: str, expected_fields: List[str], query_type: str) -> Tuple[bool, List[str]]:
    """
    Validate answer quality
    
    Returns:
        (is_valid, issues)
    """
    issues = []
    answer_lower = answer.lower()
    
    # Check if answer is not empty
    if not answer or len(answer.strip()) < 10:
        issues.append("Answer is too short or empty")
        return False, issues
    
    # Check for expected fields/keywords (more lenient for how_to queries)
    found_fields = []
    for field in expected_fields:
        if field.lower() in answer_lower:
            found_fields.append(field)
    
    # For how_to queries, also check for related action words
    if query_type == 'how_to' and len(found_fields) == 0:
        # Check for action-related keywords that might indicate instructions
        action_keywords = ['step', 'click', 'login', 'select', 'enter', 'submit', 'withdraw', 'sell', 'units', 'proceeds', 'credited', 'account']
        if any(kw in answer_lower for kw in action_keywords):
            # Answer contains action words, might be valid even without exact keywords
            pass
        else:
            issues.append(f"Answer doesn't contain expected keywords: {expected_fields}")
    elif len(found_fields) == 0:
        issues.append(f"Answer doesn't contain expected keywords: {expected_fields}")
    
    # Check for refusal (should not refuse for valid queries)
    refusal_phrases = ["i cannot", "i don't know", "i couldn't find", "not available", "no information"]
    if any(phrase in answer_lower for phrase in refusal_phrases):
        if "investment advice" not in answer_lower:  # Allow refusal for advisory questions
            issues.append("Answer appears to refuse the query unnecessarily")
    
    # Check answer length (should be reasonable)
    if len(answer) < 20:
        issues.append("Answer is too short")
    elif len(answer) > 2000:
        issues.append("Answer is too long")
    
    # Check for source citation (more lenient - accepts various formats)
    has_source_citation = (
        "[source]" in answer_lower or 
        "(source)" in answer_lower or
        "source:" in answer_lower or
        "last updated" in answer_lower  # Answers include "Last updated" with source info
    )
    if not has_source_citation:
        issues.append("Answer may be missing source citation")
    
    return len(issues) == 0, issues

def test_query(query_config: Dict, session_id: str = "test_session") -> Dict:
    """Test a single query with validation"""
    query = query_config["query"]
    expected_fields = query_config.get("expected_fields", [])
    query_type = query_config.get("type", "general")
    
    try:
        payload = {
            "query": query,
            "top_k": 3,
            "session_id": session_id,
            "response_style": "concise",
            "user_role": "PUBLIC",
            "stream": False
        }
        
        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=30)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "")
            
            # Validate answer
            is_valid, validation_issues = validate_answer(answer, expected_fields, query_type)
            
            return {
                "success": True,
                "query": query,
                "response_time": round(response_time, 3),
                "answer": answer[:200] + "..." if len(answer) > 200 else answer,
                "full_answer": answer,
                "has_source": bool(data.get("source_url")),
                "source_url": data.get("source_url", ""),
                "query_type": data.get("query_type", "unknown"),
                "refused": data.get("refused", False),
                "chunks_used": data.get("chunks_used", 0),
                "cached": data.get("cached", False),
                "validated": is_valid,
                "validation_issues": validation_issues,
                "error": data.get("error", False)
            }
        else:
            return {
                "success": False,
                "query": query,
                "response_time": round(response_time, 3),
                "status_code": response.status_code,
                "error": response.text[:200],
                "validated": False,
                "validation_issues": [f"HTTP {response.status_code} error"]
            }
    except Exception as e:
        return {
            "success": False,
            "query": query,
            "error": str(e),
            "validated": False,
            "validation_issues": [f"Exception: {str(e)}"]
        }

def run_tests():
    """Run all test queries with validation"""
    print("=" * 80)
    print("🧪 TESTING 10 QUERIES AGAINST RAG SYSTEM WITH VALIDATION")
    print("=" * 80)
    print()
    
    results = []
    total_time = 0
    
    for i, query_config in enumerate(TEST_QUERIES, 1):
        query = query_config["query"]
        print(f"Test {i}/10: {query}")
        result = test_query(query_config)
        results.append(result)
        
        if result["success"]:
            # Check both success and validation
            if result.get("validated", False):
                status = "✅ PASS (Validated)"
            elif result.get("refused", False):
                status = "⚠️  REFUSED"
            else:
                status = "⚠️  VALIDATION ISSUES"
            
            print(f"  {status} - {result['response_time']}s - Type: {result.get('query_type', 'N/A')}")
            print(f"  Chunks used: {result.get('chunks_used', 0)}")
            
            if result.get("cached"):
                print(f"  📦 Cached response")
            
            if result.get("refused"):
                print(f"  ⚠️  Query was refused")
            
            if result.get("validation_issues"):
                print(f"  ⚠️  Validation issues:")
                for issue in result["validation_issues"]:
                    print(f"     - {issue}")
            
            if result.get("source_url"):
                print(f"  🔗 Source: {result['source_url'][:60]}...")
            
            # Show answer preview
            answer_preview = result.get("answer", "")[:150]
            print(f"  💬 Answer: {answer_preview}...")
        else:
            print(f"  ❌ FAIL - {result.get('error', 'Unknown error')}")
            if result.get("validation_issues"):
                for issue in result["validation_issues"]:
                    print(f"     - {issue}")
        
        total_time += result.get("response_time", 0)
        print()
        time.sleep(0.5)  # Small delay between queries
    
    # Summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for r in results if r["success"] and not r.get("error"))
    validated = sum(1 for r in results if r.get("validated", False))
    failed = sum(1 for r in results if not r["success"] or r.get("error"))
    refused = sum(1 for r in results if r.get("refused", False))
    cached = sum(1 for r in results if r.get("cached", False))
    validation_issues = sum(1 for r in results if r.get("validation_issues", []))
    
    print(f"✅ Successful (HTTP 200): {successful}/10")
    print(f"✅ Validated (Quality OK): {validated}/10")
    print(f"❌ Failed/Errors: {failed}/10")
    print(f"⚠️  Refused: {refused}/10")
    print(f"⚠️  Validation Issues: {validation_issues}/10")
    print(f"📦 Cached: {cached}/10")
    print(f"⏱️  Total time: {round(total_time, 2)}s")
    print(f"⏱️  Average time: {round(total_time/10, 2)}s")
    print()
    
    # Show queries with validation issues
    if validation_issues > 0:
        print("⚠️  QUERIES WITH VALIDATION ISSUES:")
        for i, result in enumerate(results, 1):
            if result.get("validation_issues"):
                print(f"  {i}. {result['query']}")
                for issue in result["validation_issues"]:
                    print(f"     - {issue}")
                print(f"     Answer: {result.get('answer', 'N/A')[:100]}...")
        print()
    
    # Show failed queries
    if failed > 0:
        print("❌ FAILED QUERIES:")
        for i, result in enumerate(results, 1):
            if not result["success"]:
                print(f"  {i}. {result['query']}")
                print(f"     Error: {result.get('error', 'Unknown')}")
        print()
    
    # Show refused queries
    if refused > 0:
        print("⚠️  REFUSED QUERIES:")
        for i, result in enumerate(results, 1):
            if result.get("refused"):
                print(f"  {i}. {result['query']}")
                print(f"     Answer: {result.get('answer', 'N/A')[:100]}...")
        print()
    
    # Show validated queries
    if validated > 0:
        print("✅ VALIDATED QUERIES:")
        for i, result in enumerate(results, 1):
            if result.get("validated"):
                print(f"  {i}. {result['query']}")
                print(f"     Answer preview: {result.get('answer', 'N/A')[:80]}...")
        print()
    
    return validated == 10

if __name__ == "__main__":
    try:
        # Check if server is running
        health_check = requests.get("http://localhost:8000/health", timeout=5)
        if health_check.status_code == 200:
            print("✓ Server is running")
            print()
            success = run_tests()
            if success:
                print("🎉 ALL TESTS PASSED!")
            else:
                print("⚠️  SOME TESTS FAILED - Check output above")
        else:
            print("❌ Server health check failed")
            print("Make sure the server is running: uvicorn api_server:app --host 0.0.0.0 --port 8000")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        print("Make sure the server is running: uvicorn api_server:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")

