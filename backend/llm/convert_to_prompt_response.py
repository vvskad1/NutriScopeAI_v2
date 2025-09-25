import json
import os

SPLITS = ["train", "val", "test"]
IN_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.join(os.path.dirname(__file__), "preprocessed_dataset")

PROMPT_TEMPLATE = (
    "Test: {test_name}\nValue: {value} {unit}\nRange: {low_range}-{high_range}\n"
    "Why important?\n"
    "If low: reasons and risks\n"
    "If high: reasons and risks\n"
    "Meal plan recommendation?"
)

def make_prompt(item):
    return (
        f"Test: {item['input']['test_name']}\n"
        f"Value: {item['input']['value']} {item['input']['unit']}\n"
        f"Range: {item['input']['low_range']}-{item['input']['high_range']}\n"
        f"Why important?\n"
        f"If low: reasons and risks\n"
        f"If high: reasons and risks\n"
        f"Meal plan recommendation?"
    )

def make_response(item):
    out = item["output"]
    parts = [f"Why important: {out.get('why_important','')}\n"]
    if out.get("status") == "low":
        parts.append(f"Reasons for low: {out.get('reasons_for_low','')}\nRisks if low: {out.get('risks_if_low','')}\n")
    elif out.get("status") == "high":
        parts.append(f"Reasons for high: {out.get('reasons_for_high','')}\nRisks if high: {out.get('risks_if_high','')}\n")
    parts.append(f"Meal plan: {out.get('meal_plan','')}\n")
    return "".join(parts)

def convert_split(split):
    in_path = os.path.join(IN_DIR, f"{split}.jsonl")
    out_path = os.path.join(OUT_DIR, f"{split}.jsonl")
    with open(in_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            item = json.loads(line)
            prompt = make_prompt(item)
            response = make_response(item)
            fout.write(json.dumps({"prompt": prompt, "response": response}, ensure_ascii=False) + "\n")
    print(f"Converted {split} to prompt-response format at {out_path}")

if __name__ == "__main__":
    for split in SPLITS:
        convert_split(split)
