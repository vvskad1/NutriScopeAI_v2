import os
import json
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from datasets import Dataset

MODEL_DIR = os.path.join(os.path.dirname(__file__), "trained_llm_model_flan_t5")
VAL_PATH = os.path.join(os.path.dirname(__file__), "preprocessed_dataset", "val.jsonl")

# Load model and tokenizer
# You can use "google/flan-t5-base" or "google/flan-t5-large" for direct loading, or load from MODEL_DIR after training
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_DIR)
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

# Load validation data
with open(VAL_PATH, "r", encoding="utf-8") as f:
    val_data = [json.loads(line) for line in f]

val_dataset = Dataset.from_list(val_data)

# Evaluate
def evaluate(model, tokenizer, dataset, num_samples=100):
    import re
    total = 0
    mismatch_count = 0
    output_lines = []
    for item in dataset.select(range(min(num_samples, len(dataset)))):
        prompt = item["prompt"]
        true_response = item["response"]
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
        outputs = model.generate(**inputs, max_length=128)
        pred_response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract value and range from prompt
        value_match = re.search(r"Value: ([^\n]+)", prompt)
        range_match = re.search(r"Range: ([^\n]+)", prompt)
        value = value_match.group(1).strip() if value_match else None
        range_str = range_match.group(1).strip() if range_match else None

        # Determine status (low/normal/high)
        status = None
        try:
            val_num = float(re.findall(r"[\d.]+", value)[0]) if value else None
            if range_str and range_str.lower() != "none":
                minmax = re.findall(r"[\d.]+", range_str)
                if len(minmax) == 2:
                    min_v, max_v = float(minmax[0]), float(minmax[1])
                    if val_num < min_v:
                        status = "low"
                    elif val_num > max_v:
                        status = "high"
                    else:
                        status = "normal"
        except Exception:
            pass

        mismatch = False
        if status == "low":
            if "Reasons for high" in pred_response or "Risks if high" in pred_response:
                mismatch = True
        elif status == "high":
            if "Reasons for low" in pred_response or "Risks if low" in pred_response:
                mismatch = True
        elif status == "normal":
            if ("Reasons for low" in pred_response or "Risks if low" in pred_response or
                "Reasons for high" in pred_response or "Risks if high" in pred_response):
                mismatch = True

        output_lines.append(f"Prompt: {prompt}\nTrue: {true_response}\nPred: {pred_response}")
        if mismatch:
            output_lines.append("*** STATUS MISMATCH DETECTED ***")
            mismatch_count += 1
        output_lines.append("-"*40)
        total += 1
    output_lines.append(f"Evaluated {total} samples. Status mismatches: {mismatch_count}")
    # Write to file
    out_path = os.path.join(os.path.dirname(__file__), "llm_eval_results.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"Results written to {out_path}")

if __name__ == "__main__":
    evaluate(model, tokenizer, val_dataset)
