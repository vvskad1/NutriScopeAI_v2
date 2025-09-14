from groq import Groq
import json

client = Groq()

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful nutrition assistant. Always return your answer as a JSON object with a 'meal_plan' key containing a list of meals. Each meal should have: name, ingredients, instructions, why_this_meal."
        },
        {
            "role": "user",
            "content": (
                "Given these flagged lab results: Red Blood Cell (RBC): 1.8 million/μl (low), "
                "Hemoglobin: 6.5 g/dL (low), Hematocrit: 19.5% (low). "
                "What are 3 specific meal ideas (with ingredients and instructions) that would help improve these results? "
                "Please explain why each meal is helpful. Return your answer as a JSON object with a 'meal_plan' key containing a list of meals."
            )
        }
    ],
    model="llama-3-70b",
    temperature=0.3,
    max_tokens=600,
)


# Debug: Print raw response, type, length, and first 500 chars
raw_response = chat_completion.choices[0].message.content
print("\n[LLM RAW RESPONSE]\n", raw_response)
print("\n[DEBUG] Type:", type(raw_response))
print("[DEBUG] Length:", len(raw_response))
print("[DEBUG] First 500 chars:\n", raw_response[:500])

# Save raw response to file for inspection
with open("llm_mealplan_raw.txt", "w", encoding="utf-8") as f:
    f.write(raw_response)
    print("\n[DEBUG] Raw response saved to llm_mealplan_raw.txt")

# Try to parse the output as JSON
try:
    result = json.loads(raw_response)
    print("\nParsed meal plan:", json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print("\nCould not parse as JSON:", e)
