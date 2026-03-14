#!/usr/bin/env python3
"""
🔍 QUALITY AUDITOR
Validates generated maritime training samples

Checks:
- Maritime terminology accuracy
- Regulatory citation validity  
- Answer completeness
- Dangerous misinformation
- Format compliance

Usage:
  python quality_audit.py [--sample-size 50] [--category filter]
"""

import json
import random
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict
import re

OUTPUT_FILE = Path("/home/mohanganesh/ship/training/orchestrated_60k/maritime_60k.jsonl")
AUDIT_DIR = Path("/home/mohanganesh/ship/training/orchestrated_60k/audits")
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

# === VALIDATION CRITERIA ===

MARITIME_TERMS = {
    # Navigation
    "navigation": ["bearing", "course", "heading", "position", "latitude", "longitude", "nautical mile", "knot", "compass", "chart", "ecdis", "gps", "radar", "ais"],
    
    # Safety
    "safety": ["solas", "marpol", "stcw", "ism", "isps", "muster", "drill", "lifeboat", "fire", "emergency", "abandon ship", "man overboard"],
    
    # Operations
    "operations": ["cargo", "ballast", "bunker", "mooring", "anchor", "watch", "bridge", "engine room", "deck", "hold", "tank"],
    
    # Equipment
    "equipment": ["gmdss", "epirb", "sart", "vhf", "radar", "gyro", "sonar", "echo sounder", "autopilot", "steering gear"],
    
    # Emergency
    "emergency": ["enclosed space", "permit to work", "rescue", "evacuation", "damage control", "flooding", "collision", "grounding", "fire fighting"],
}

REGULATORY_CITATIONS = {
    "marpol": r"(?:MARPOL|Annex [I-VI])",
    "solas": r"(?:SOLAS|Chapter [IVX]+)",
    "stcw": r"(?:STCW|Regulation [IVX]+/\d+|Competence)",
    "ism": r"(?:ISM Code|International Safety Management)",
    "isps": r"(?:ISPS Code|International Ship and Port Facility Security)",
}

DANGEROUS_KEYWORDS = [
    "ignore safety", "skip procedure", "not necessary", "optional safety",
    "fire extinguisher not needed", "no gas test", "enter without permit",
    "no ventilation needed", "rescue alone", "no backup",
]

# === SCORING FUNCTIONS ===

def score_maritime_terminology(text: str) -> float:
    """Score based on maritime terminology usage."""
    text_lower = text.lower()
    
    found_terms = 0
    total_categories = len(MARITIME_TERMS)
    
    for category, terms in MARITIME_TERMS.items():
        if any(term in text_lower for term in terms):
            found_terms += 1
    
    return found_terms / total_categories

def score_regulatory_citations(text: str, category: str) -> float:
    """Score based on regulatory citations."""
    
    # Categories that MUST have citations
    regulatory_categories = ["marpol", "solas", "stcw", "ism", "isps", "mlc", "port_state"]
    
    if not any(cat in category for cat in regulatory_categories):
        return 1.0  # Not applicable
    
    # Check for citations
    for reg, pattern in REGULATORY_CITATIONS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return 1.0  # Found citation
    
    return 0.0  # Missing citation

def score_completeness(question: str, answer: str) -> float:
    """Score answer completeness."""
    
    # Answer should be substantially longer than question
    if len(answer) < len(question) * 1.5:
        return 0.3
    
    # Answer should have multiple sentences
    sentences = len([s for s in answer.split('.') if len(s.strip()) > 10])
    if sentences < 3:
        return 0.5
    
    # Answer should have structure (steps, points, etc)
    has_structure = any(marker in answer for marker in ['1.', '2.', '- ', 'First', 'Second', 'Step'])
    
    score = 0.7
    if sentences >= 5:
        score += 0.15
    if has_structure:
        score += 0.15
    
    return min(score, 1.0)

def check_dangerous_misinformation(text: str) -> List[str]:
    """Check for dangerous misinformation."""
    
    issues = []
    text_lower = text.lower()
    
    for keyword in DANGEROUS_KEYWORDS:
        if keyword in text_lower:
            issues.append(f"Dangerous: '{keyword}' found")
    
    # Check for missing critical safety steps in specific contexts
    if "enclosed space" in text_lower:
        if not any(term in text_lower for term in ["gas test", "oxygen", "atmosphere", "ventilation"]):
            issues.append("Enclosed space procedure missing gas testing")
    
    if "fire" in text_lower and "emergency" in text_lower:
        if not any(term in text_lower for term in ["muster", "alarm", "evacuation", "assembly"]):
            issues.append("Fire emergency missing muster/alarm procedures")
    
    return issues

def validate_format(sample: Dict) -> List[str]:
    """Validate sample format."""
    
    issues = []
    
    if "question" not in sample:
        issues.append("Missing 'question' field")
    elif len(sample["question"]) < 50:
        issues.append("Question too short (<50 chars)")
    
    if "answer" not in sample:
        issues.append("Missing 'answer' field")
    elif len(sample["answer"]) < 150:
        issues.append("Answer too short (<150 chars)")
    
    if "category" not in sample:
        issues.append("Missing 'category' field")
    
    return issues

# === AUDIT FUNCTIONS ===

def audit_sample(sample: Dict) -> Dict:
    """Perform comprehensive audit on a sample."""
    
    question = sample.get("question", "")
    answer = sample.get("answer", "")
    category = sample.get("category", "")
    
    # Scores
    terminology_score = score_maritime_terminology(question + " " + answer)
    citation_score = score_regulatory_citations(answer, category)
    completeness_score = score_completeness(question, answer)
    
    # Issues
    format_issues = validate_format(sample)
    safety_issues = check_dangerous_misinformation(question + " " + answer)
    
    # Overall score
    overall_score = (terminology_score * 0.3 + citation_score * 0.3 + completeness_score * 0.4)
    
    return {
        "sample_id": sample.get("worker_id", "unknown"),
        "category": category,
        "scores": {
            "terminology": round(terminology_score, 2),
            "citations": round(citation_score, 2),
            "completeness": round(completeness_score, 2),
            "overall": round(overall_score, 2),
        },
        "issues": {
            "format": format_issues,
            "safety": safety_issues,
        },
        "passed": overall_score >= 0.7 and len(safety_issues) == 0,
    }

def load_samples(category_filter: str = None) -> List[Dict]:
    """Load samples from output file."""
    
    samples = []
    
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for line in f:
                try:
                    sample = json.loads(line)
                    if category_filter is None or sample.get("category") == category_filter:
                        samples.append(sample)
                except:
                    pass
    
    return samples

def run_audit(sample_size: int = 50, category_filter: str = None):
    """Run quality audit."""
    
    print("=" * 80)
    print("🔍 QUALITY AUDIT")
    print("=" * 80)
    print()
    
    # Load samples
    print(f"Loading samples from: {OUTPUT_FILE}")
    all_samples = load_samples(category_filter)
    
    if not all_samples:
        print("❌ No samples found!")
        return
    
    print(f"✅ Loaded {len(all_samples)} samples")
    
    # Random sample
    audit_samples = random.sample(all_samples, min(sample_size, len(all_samples)))
    print(f"🎲 Auditing {len(audit_samples)} random samples")
    print()
    
    # Audit each sample
    results = []
    passed = 0
    failed = 0
    
    for i, sample in enumerate(audit_samples, 1):
        result = audit_sample(sample)
        results.append(result)
        
        if result["passed"]:
            passed += 1
        else:
            failed += 1
        
        # Progress
        if i % 10 == 0:
            print(f"  Audited {i}/{len(audit_samples)}...")
    
    print()
    
    # Summary statistics
    print("=" * 80)
    print("📊 AUDIT SUMMARY")
    print("=" * 80)
    print()
    
    print(f"Total audited: {len(results)}")
    print(f"✅ Passed: {passed} ({100*passed/len(results):.1f}%)")
    print(f"❌ Failed: {failed} ({100*failed/len(results):.1f}%)")
    print()
    
    # Score distribution
    avg_scores = {
        "terminology": sum(r["scores"]["terminology"] for r in results) / len(results),
        "citations": sum(r["scores"]["citations"] for r in results) / len(results),
        "completeness": sum(r["scores"]["completeness"] for r in results) / len(results),
        "overall": sum(r["scores"]["overall"] for r in results) / len(results),
    }
    
    print("Average Scores:")
    print(f"  Maritime Terminology: {avg_scores['terminology']:.2f}")
    print(f"  Regulatory Citations: {avg_scores['citations']:.2f}")
    print(f"  Answer Completeness:  {avg_scores['completeness']:.2f}")
    print(f"  Overall Quality:      {avg_scores['overall']:.2f}")
    print()
    
    # Issues breakdown
    format_issues = sum(len(r["issues"]["format"]) for r in results)
    safety_issues = sum(len(r["issues"]["safety"]) for r in results)
    
    print(f"Issues Found:")
    print(f"  Format issues:  {format_issues}")
    print(f"  Safety issues:  {safety_issues}")
    
    if safety_issues > 0:
        print()
        print("⚠️  CRITICAL SAFETY ISSUES DETECTED:")
        for r in results:
            if r["issues"]["safety"]:
                print(f"  Category: {r['category']}")
                for issue in r["issues"]["safety"]:
                    print(f"    - {issue}")
    
    print()
    
    # Category breakdown
    by_category = defaultdict(list)
    for r in results:
        by_category[r["category"]].append(r["scores"]["overall"])
    
    print("Quality by Category:")
    for cat, scores in sorted(by_category.items()):
        avg = sum(scores) / len(scores)
        print(f"  {cat:30} {avg:.2f} ({len(scores)} samples)")
    
    print()
    
    # Save detailed report
    from datetime import datetime
    report_file = AUDIT_DIR / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "sample_size": len(results),
        "category_filter": category_filter,
        "summary": {
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(results),
        },
        "average_scores": avg_scores,
        "issues": {
            "format": format_issues,
            "safety": safety_issues,
        },
        "detailed_results": results,
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"💾 Detailed report saved to: {report_file}")
    print()
    
    # Recommendations
    print("=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    if avg_scores["overall"] < 0.8:
        print("⚠️  Overall quality below target (0.80)")
        print("   → Review prompts for clarity and specificity")
        print("   → Consider adding more context to generation prompts")
    
    if avg_scores["citations"] < 0.7:
        print("⚠️  Regulatory citations below target")
        print("   → Emphasize citation requirements in prompts")
        print("   → Add examples with proper citations")
    
    if safety_issues > 0:
        print("🚨 CRITICAL: Safety issues detected")
        print("   → HALT generation for affected categories")
        print("   → Review and revise prompts immediately")
        print("   → Re-audit after fixes")
    
    if passed / len(results) >= 0.95:
        print("✅ Quality metrics meet targets - continue generation!")
    
    print()

def main():
    """Main function."""
    
    parser = argparse.ArgumentParser(description="Quality audit for maritime training data")
    parser.add_argument("--sample-size", type=int, default=50, help="Number of samples to audit")
    parser.add_argument("--category", type=str, help="Filter by specific category")
    
    args = parser.parse_args()
    
    run_audit(sample_size=args.sample_size, category_filter=args.category)

if __name__ == "__main__":
    main()
