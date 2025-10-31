import json
import os
from typing import List, Dict, Any

def format_example(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a single parsed test row into an LLM training example.
    """
    test = row.get('raw') or row.get('test')
    value = row.get('value')
    unit = row.get('unit')
    status = row.get('status')
    low = row.get('applied', {}).get('low')
    high = row.get('applied', {}).get('high')
    ref_unit = row.get('applied', {}).get('unit')
    kb_key = row.get('kb_key_resolved')
    # Placeholder summary fields (to be filled by LLM or knowledge base)
    summary = {
        "why_important": f"Why is {test} important?",
        "why_high": f"Why is {test} high?",
        "why_low": f"Why is {test} low?",
        "risks_if_high": f"Risks if {test} is high.",
        "risks_if_low": f"Risks if {test} is low."
    }
    example = {
        "input": {
            "test": test,
            "value": value,
            "unit": unit,
            "status": status,
            "low": low,
            "high": high,
            "ref_unit": ref_unit,
            "kb_key": kb_key
        },
        "output": summary
    }
    return example

def main():
    # Load parser debug output (replace with actual parser output file)
    input_path = os.path.join(os.path.dirname(__file__), 'parser_debug_output.json')
    output_path = os.path.join(os.path.dirname(__file__), 'llm_formatted_examples.jsonl')
    with open(input_path, 'r', encoding='utf-8') as f:
        rows = json.load(f)
    examples = [format_example(row) for row in rows]
    with open(output_path, 'w', encoding='utf-8') as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')
    print(f"Wrote {len(examples)} formatted examples to {output_path}")

if __name__ == "__main__":
    main()
