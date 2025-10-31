import json
import random
import os

TESTS = [
    {"test": "Hemoglobin", "unit": "g/dL", "low": 13.0, "high": 17.0, "kb_key": "hemoglobin"},
    {"test": "WBC", "unit": "x10^3/uL", "low": 4.0, "high": 10.0, "kb_key": "wbc"},
    {"test": "Platelets", "unit": "x10^3/uL", "low": 150, "high": 400, "kb_key": "platelets"},
    {"test": "ALT", "unit": "U/L", "low": 7, "high": 56, "kb_key": "alt"},
    {"test": "TSH", "unit": "uIU/mL", "low": 0.35, "high": 5.5, "kb_key": "tsh"},
    {"test": "Vitamin D (25-oh)", "unit": "ng/mL", "low": 30, "high": 100, "kb_key": "vitamin d (25-oh)"},
    {"test": "S. Calcium", "unit": "mg/dL", "low": 8.8, "high": 10.6, "kb_key": "s. calcium"},
    {"test": "Random Blood Glucose", "unit": "mmol/L", "low": 4.1, "high": 7.8, "kb_key": "random blood glucose"},
    {"test": "Vitamin B12", "unit": "pg/mL", "low": 120.0, "high": 914.0, "kb_key": "vitamin b12"},
    {"test": "S. Bilirubin D", "unit": "mg/dL", "low": None, "high": 0.2, "kb_key": "s. bilirubin d"}
]

REASONS = {
    "Hemoglobin": {
        "why_important": "Hemoglobin is essential for oxygen transport in the blood.",
        "why_high": "High hemoglobin may be due to dehydration, lung disease, or living at high altitude.",
        "why_low": "Low hemoglobin is often caused by anemia, blood loss, or nutritional deficiencies.",
        "risks_if_high": "High hemoglobin can increase risk of blood clots and stroke.",
        "risks_if_low": "Low hemoglobin can cause fatigue, weakness, and shortness of breath."
    },
    "WBC": {
        "why_important": "White blood cells are crucial for fighting infection.",
        "why_high": "High WBC may indicate infection, inflammation, or leukemia.",
        "why_low": "Low WBC can be due to bone marrow disorders, viral infections, or medications.",
        "risks_if_high": "High WBC can signal underlying disease or infection.",
        "risks_if_low": "Low WBC increases risk of infections."
    },
    "Platelets": {
        "why_important": "Platelets help with blood clotting.",
        "why_high": "High platelets may be due to inflammation, infection, or bone marrow disorders.",
        "why_low": "Low platelets can result from viral infections, medications, or autoimmune diseases.",
        "risks_if_high": "High platelets increase risk of clotting disorders.",
        "risks_if_low": "Low platelets increase risk of bleeding."
    },
    "ALT": {
        "why_important": "ALT is a liver enzyme used to assess liver health.",
        "why_high": "High ALT may indicate liver damage, hepatitis, or fatty liver disease.",
        "why_low": "Low ALT is usually not clinically significant.",
        "risks_if_high": "High ALT can signal liver injury or disease.",
        "risks_if_low": "Low ALT is not typically a concern."
    },
    "TSH": {
        "why_important": "TSH regulates thyroid function.",
        "why_high": "High TSH may indicate hypothyroidism.",
        "why_low": "Low TSH may indicate hyperthyroidism.",
        "risks_if_high": "High TSH can cause fatigue, weight gain, and depression.",
        "risks_if_low": "Low TSH can cause anxiety, weight loss, and palpitations."
    },
    "Vitamin D (25-oh)": {
        "why_important": "Vitamin D is crucial for bone health, immune function, and mood regulation.",
        "why_high": "High Vitamin D may be due to excessive supplements or certain diseases.",
        "why_low": "Low Vitamin D is often caused by limited sun exposure or poor diet.",
        "risks_if_high": "High Vitamin D can cause hypercalcemia and kidney stones.",
        "risks_if_low": "Low Vitamin D increases risk of osteoporosis and immune dysfunction."
    },
    "S. Calcium": {
        "why_important": "Calcium is vital for bone health and muscle function.",
        "why_high": "High calcium may be due to hyperparathyroidism or vitamin D toxicity.",
        "why_low": "Low calcium can be caused by vitamin D deficiency or kidney disease.",
        "risks_if_high": "High calcium can cause kidney stones and cardiac arrhythmias.",
        "risks_if_low": "Low calcium can cause muscle cramps and seizures."
    },
    "Random Blood Glucose": {
        "why_important": "Blood glucose testing is essential for diabetes management.",
        "why_high": "High glucose may result from diabetes or stress.",
        "why_low": "Low glucose can be due to insulin overdose or fasting.",
        "risks_if_high": "High glucose increases risk of complications.",
        "risks_if_low": "Low glucose can cause confusion and seizures."
    },
    "Vitamin B12": {
        "why_important": "Vitamin B12 is vital for nerve function and red blood cell production.",
        "why_high": "High B12 may be due to supplementation or liver disease.",
        "why_low": "Low B12 is often caused by poor diet or malabsorption.",
        "risks_if_high": "High B12 is rarely harmful but may indicate disease.",
        "risks_if_low": "Low B12 can cause anemia and neuropathy."
    },
    "S. Bilirubin D": {
        "why_important": "Bilirubin D helps diagnose liver and bile duct disorders.",
        "why_high": "High bilirubin may be due to liver damage or obstruction.",
        "why_low": "Low bilirubin is usually not a concern.",
        "risks_if_high": "High bilirubin can cause jaundice and fatigue.",
        "risks_if_low": "Low bilirubin is not clinically significant."
    }
}

STATUSES = ["normal", "high", "low"]

def random_value(test):
    low, high = test["low"], test["high"]
    if low is not None and high is not None:
        status = random.choice(STATUSES)
        if status == "normal":
            value = round(random.uniform(low + 0.1, high - 0.1), 2)
        elif status == "high":
            value = round(random.uniform(high + 0.1, high * 1.5), 2)
        else:
            value = round(random.uniform(low * 0.5, low - 0.1), 2)
    elif high is not None:
        status = random.choice(["normal", "high"])
        if status == "normal":
            value = round(random.uniform(0, high - 0.01), 2)
        else:
            value = round(random.uniform(high + 0.01, high * 1.5), 2)
    else:
        status = "normal"
        value = round(random.uniform(1, 100), 2)
    return value, status

def main():
    out_path = os.path.join(os.path.dirname(__file__), "llm_training_dataset.jsonl")
    MEAL_PLANS = {
        "Hemoglobin": {
            "low": "Increase iron-rich foods (red meat, spinach, lentils), vitamin C for absorption.",
            "high": "Stay hydrated, avoid excess iron supplements.",
            "normal": "Maintain balanced diet with lean meats, vegetables, and grains."
        },
        "WBC": {
            "low": "Eat foods rich in zinc and vitamin C (citrus, bell peppers, nuts).",
            "high": "Focus on anti-inflammatory foods (berries, leafy greens, fatty fish).",
            "normal": "Balanced diet with fruits, vegetables, and lean proteins."
        },
        "Platelets": {
            "low": "Consume foods with vitamin K (broccoli, kale), avoid alcohol.",
            "high": "Limit vitamin K, avoid processed foods, stay hydrated.",
            "normal": "Balanced diet with whole grains, fruits, and vegetables."
        },
        "ALT": {
            "low": "No specific dietary changes needed.",
            "high": "Limit alcohol, fried foods, and processed snacks; increase fruits and vegetables.",
            "normal": "Maintain healthy liver with balanced diet, moderate alcohol."
        },
        "TSH": {
            "low": "Increase iodine-rich foods (seaweed, dairy, eggs).",
            "high": "Limit soy, cruciferous vegetables; increase selenium (brazil nuts, fish).",
            "normal": "Balanced diet with adequate iodine and selenium."
        },
        "Vitamin D (25-oh)": {
            "low": "Increase sunlight exposure, consume fortified dairy, fatty fish, and mushrooms.",
            "high": "Limit supplements, maintain moderate intake of vitamin D-rich foods.",
            "normal": "Continue balanced intake of vitamin D sources."
        },
        "S. Calcium": {
            "low": "Increase dairy, leafy greens, almonds, and fortified foods.",
            "high": "Limit calcium supplements, avoid excess dairy, increase hydration.",
            "normal": "Maintain regular intake of calcium-rich foods."
        },
        "Random Blood Glucose": {
            "low": "Eat frequent small meals, include complex carbs (whole grains, fruits).",
            "high": "Limit sugars, refined carbs; increase fiber, lean proteins, and vegetables.",
            "normal": "Balanced diet with whole grains, lean proteins, and vegetables."
        },
        "Vitamin B12": {
            "low": "Increase animal products (meat, eggs, dairy) or fortified cereals.",
            "high": "No specific dietary changes needed.",
            "normal": "Maintain regular intake of B12-rich foods."
        },
        "S. Bilirubin D": {
            "low": "No specific dietary changes needed.",
            "high": "Increase hydration, eat liver-supportive foods (beets, leafy greens, berries).",
            "normal": "Balanced diet with fruits and vegetables."
        }
    }
    with open(out_path, "w", encoding="utf-8") as f:
        for i in range(50000):
            test = random.choice(TESTS)
            value, _ = random_value(test)
            low = test["low"]
            high = test["high"]
            # Determine status
            if low is not None and value < low:
                status = "low"
            elif high is not None and value > high:
                status = "high"
            else:
                status = "normal"
            reasons = REASONS[test["test"]]
            meal_plan = MEAL_PLANS[test["test"]][status]
            output = {
                "why_important": reasons["why_important"],
                "status": status
            }
            if status == "low":
                output["reasons_for_low"] = reasons["why_low"]
                output["risks_if_low"] = reasons["risks_if_low"]
            elif status == "high":
                output["reasons_for_high"] = reasons["why_high"]
                output["risks_if_high"] = reasons["risks_if_high"]
            output["meal_plan"] = meal_plan
            example = {
                "input": {
                    "test_name": test["test"],
                    "value": value,
                    "unit": test["unit"],
                    "low_range": low,
                    "high_range": high
                },
                "output": output
            }
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
    print(f"Generated 10,000 examples in {out_path} with required input/output fields.")

if __name__ == "__main__":
    main()
