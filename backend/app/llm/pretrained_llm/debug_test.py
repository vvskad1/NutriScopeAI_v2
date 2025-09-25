#!/usr/bin/env python3
"""
Debug test to see what's happening with the LLM processing
"""

import json
from local_inference import PretrainedLLMService

def debug_llm_processing():
    """Debug the LLM processing step by step"""
    service = PretrainedLLMService()
    
    # Sample test data matching your actual results
    test_data = [
        {
            "test_name": "Vitamin D (25-oh)",
            "value": 7.3,
            "unit": "ng/mL",
            "status": "low",
            "ref_range": "30-100 ng/mL"
        },
        {
            "test_name": "S. Calcium",
            "value": 8.6,
            "unit": "mg/dL", 
            "status": "low",
            "ref_range": "8.8-10.6 mg/dL"
        },
        {
            "test_name": "S. Bilirubin D",
            "value": 0.24,
            "unit": "mg/dL",
            "status": "high", 
            "ref_range": "0.0-0.20 mg/dL"
        }
    ]
    
    print("🔍 Debugging LLM Processing")
    print("=" * 50)
    
    # Check if model loads
    if service.load_model():
        print("✅ Model loaded successfully")
    else:
        print("❌ Model failed to load")
        return
    
    # Test individual analysis generation
    print("\n🔬 Testing individual test analysis:")
    for test in test_data:
        print(f"\nProcessing: {test['test_name']}")
        print(f"Value: {test['value']} {test['unit']}")
        print(f"Status: {test['status']}")
        print(f"Range: {test['ref_range']}")
        
        # Generate analysis for this test
        analysis = service.generate_clinical_analysis(
            test['test_name'], 
            f"{test['value']} {test['unit']}", 
            test['ref_range'], 
            max_length=256
        )
        
        if analysis:
            print(f"✅ Analysis generated: {analysis[:100]}...")
        else:
            print("❌ No analysis generated")
    
    print("\n📊 Testing structured summary generation:")
    result = service.generate_structured_summary(test_data, {})
    
    print(f"Per-test keys: {list(result['per_test'].keys())}")
    print(f"Diet plan add: {result['diet_plan']['add']}")
    print(f"Overall message: {result['overall_message']}")

if __name__ == "__main__":
    debug_llm_processing()