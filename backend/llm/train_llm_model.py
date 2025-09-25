# (Moved from backend/ to backend/llm/)
# Seq2Seq Q&A Training Script for T5
import os
import json
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, Seq2SeqTrainer, Seq2SeqTrainingArguments, DataCollatorForSeq2Seq
from datasets import Dataset

MODEL_NAME = "google/flan-t5-large"
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "preprocessed_dataset")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def prepare_dataset(split):
    data = load_jsonl(os.path.join(DATA_DIR, f"{split}.jsonl"))
    return Dataset.from_list([
        {"prompt": item["prompt"], "response": item["response"]} for item in data
    ])

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def preprocess_function(examples):
    inputs = examples["prompt"]
    targets = examples["response"]
    model_inputs = tokenizer(inputs, max_length=128, truncation=True)
    labels = tokenizer(targets, max_length=128, truncation=True)
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

train_dataset = prepare_dataset("train").map(preprocess_function, batched=True)
val_dataset = prepare_dataset("val").map(preprocess_function, batched=True)

data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=MODEL_NAME)

model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

training_args = Seq2SeqTrainingArguments(
    output_dir=RESULTS_DIR,
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    logging_dir=LOGS_DIR,
    logging_steps=10,
    predict_with_generate=True,
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

if __name__ == "__main__":
    trainer.train()
    trainer.save_model(os.path.join(BASE_DIR, "trained_llm_model_t5"))
    print(f"Model training complete. Saved to {os.path.join(BASE_DIR, 'trained_llm_model_t5')}")