# Test script for pretrained LLM integration
# Run this to verify your local model works in the app context

import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from llm.pretrained_llm import generate_clinical_summary_local, generate_structured_summary_local

def test_clinical_summary():
    """Test clinical summary generation"""
    print("Testing clinical summary generation...")
    
    result = generate_clinical_summary_local(
        test_name="Vitamin D (25-oh)",
        value="15.5 ng/mL",
        reference_range="30-100"
    )
    
    if result:
        print("✅ Clinical Summary Generated:")
        print(result)
        print("-" * 50)
    else:
        print("❌ Failed to generate clinical summary")

def test_structured_summary():
    """Test structured summary generation (API-compatible format)"""
    print("Testing structured summary generation...")
    
    context = {"age": 30, "sex": "M"}
    results = [
        {
            "test": "Vitamin D (25-oh)",
            "value": 15.5,
            "unit": "ng/mL",
            "status": "low",
            "applied_range": {"min": 30, "max": 100}
        },
        {
            "test": "Hemoglobin",
            "value": 10.5,
            "unit": "g/dL",
            "status": "low", 
            "applied_range": {"min": 13.0, "max": 17.0}
        },
        {
            "test": "Calcium",
            "value": 7.5,
            "unit": "mg/dL",
            "status": "low",
            "applied_range": {"min": 8.8, "max": 10.6}
        }
    ]
    
    result = generate_structured_summary_local(context, results)
    
    if result and not result.get("error"):
        print("✅ Structured Summary Generated:")
        print("Per-test analysis:")
        for test in result.get("per_test", []):
            print(f"  • {test['test']}: {test['importance']}")
        
        print("\nDiet Plan:")
        diet = result.get("diet_plan", {})
        if diet.get("add"):
            print(f"  Add: {', '.join(diet['add'])}")
        if diet.get("limit"):
            print(f"  Limit: {', '.join(diet['limit'])}")
        
        print(f"\nOverall: {result.get('overall_message', 'N/A')}")
        print("-" * 50)
    else:
        print("❌ Failed to generate structured summary")
        if result.get("error"):
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    print("Testing Pretrained LLM Integration")
    print("=" * 50)
    
    test_clinical_summary()
    test_structured_summary()
    
    print("Testing complete!")