import json
import random
import os

DATASET_PATH = os.path.join(os.path.dirname(__file__), 'llm_training_dataset.jsonl')
TRAIN_PATH = os.path.join(os.path.dirname(__file__), 'train.jsonl')
VAL_PATH = os.path.join(os.path.dirname(__file__), 'val.jsonl')
TEST_PATH = os.path.join(os.path.dirname(__file__), 'test.jsonl')


def load_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def save_jsonl(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def split_dataset(data, train_ratio=0.8, val_ratio=0.1):
    random.shuffle(data)
    n = len(data)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    return data[:train_end], data[train_end:val_end], data[val_end:]

def main():
    data = load_jsonl(DATASET_PATH)
    train, val, test = split_dataset(data)
    save_jsonl(train, TRAIN_PATH)
    save_jsonl(val, VAL_PATH)
    save_jsonl(test, TEST_PATH)
    print(f"Split: {len(train)} train, {len(val)} val, {len(test)} test")

if __name__ == "__main__":
    main()
