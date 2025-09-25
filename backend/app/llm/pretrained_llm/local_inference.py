# Pretrained LLM Integration for NutriScope AI
# This module provides local inference using our trained FLAN-T5 model
# Can be used as an alternative to API-based LLM calls

import os
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class PretrainedLLMService:
    """Service for local pretrained model inference"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.tokenizer = None
        self.model_path = model_path or self._get_default_model_path()
        self.is_loaded = False
    
    def _get_default_model_path(self) -> str:
        """Get the default path to the trained model"""
        # Use the exact same path resolution as the working standalone script
        return r"C:\Users\by4412\Desktop\NutriScope AI\v2_code\backend\llm\results\checkpoint-15000"
    
    def load_model(self) -> bool:
        """Load the pretrained model and tokenizer"""
        try:
            logger.info(f"Loading pretrained model from: {self.model_path}")
            # Use local_files_only=True to force local loading and bypass repo validation
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_path, 
                local_files_only=True
            )
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, 
                local_files_only=True
            )
            self.is_loaded = True
            logger.info("Pretrained model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load pretrained model: {e}")
            self.is_loaded = False
            return False
    
    def generate_clinical_analysis(
        self, 
        test_name: str, 
        value: str, 
        reference_range: str,
        max_length: int = 256
    ) -> Optional[str]:
        """
        Generate clinical analysis for a lab test result
        
        Args:
            test_name: Name of the lab test
            value: Test result value
            reference_range: Normal reference range
            max_length: Maximum response length
            
        Returns:
            Generated clinical analysis or None if error
        """
        if not self.is_loaded:
            if not self.load_model():
                return None
        
        # Format prompt similar to training data
        prompt = f"""Test: {test_name}
Value: {value}
Range: {reference_range}
Why important?
If low: reasons and risks
If high: reasons and risks
Meal plan recommendation?"""
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True)
            with torch.no_grad():
                outputs = self.model.generate(**inputs, max_length=max_length)
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response
        except Exception as e:
            logger.error(f"Error generating clinical analysis: {e}")
            return None
    
    def generate_structured_summary(
        self,
        context: Dict[str, Any],
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate structured summary matching API format
        
        Args:
            context: User context (age, sex, etc.)
            results: List of lab test results with status
            
        Returns:
            Structured summary matching API format
        """
        if not self.is_loaded:
            if not self.load_model():
                return {"error": "Failed to load model"}
        
        # Process each test result
        per_test = {}
        meal_recommendations = []
        
        for result in results:
            test_name = result.get("test_name", result.get("test", ""))
            value = result.get("value", "")
            unit = result.get("unit", "")
            status = result.get("status", "normal")
            range_info = result.get("applied_range", {})
            
            # Format range for our model
            if range_info:
                range_str = f"{range_info.get('min', '')}-{range_info.get('max', '')}"
            elif "ref_range" in result:
                range_str = result["ref_range"]
            else:
                range_str = "N/A"
            
            # Generate analysis using our trained model
            analysis = self.generate_clinical_analysis(
                test_name, f"{value} {unit}".strip(), range_str, max_length=256
            )
            
            # Generate structured analysis based on test name and status
            importance, why_reasons, risks, meal_plan = self._generate_test_insights(test_name, status)
            
            per_test[test_name] = {
                "test": test_name,
                "value": str(value),
                "unit": unit,
                "status": status,
                "importance": importance,
                "why_low": why_reasons if status == "low" else [],
                "why_high": why_reasons if status == "high" else [],
                "risks_if_low": risks if status == "low" else [],
                "risks_if_high": risks if status == "high" else [],
                "next_steps": [meal_plan] if meal_plan else []
            }
            
            if meal_plan:
                meal_recommendations.append(meal_plan)
        
        # Create diet plan
        diet_plan = {
            "add": [],
            "limit": [],
            "meals": self._generate_meal_ideas(meal_recommendations)
        }
        
        # Extract dietary recommendations
        for rec in meal_recommendations:
            if "increase" in rec.lower() or "consume" in rec.lower():
                # Extract foods to add
                foods = self._extract_foods_to_add(rec)
                diet_plan["add"].extend(foods)
            if "limit" in rec.lower() or "avoid" in rec.lower():
                # Extract foods to limit
                foods = self._extract_foods_to_limit(rec)
                diet_plan["limit"].extend(foods)
        
        # Remove duplicates
        diet_plan["add"] = list(set(diet_plan["add"]))
        diet_plan["limit"] = list(set(diet_plan["limit"]))
        
        return {
            "per_test": per_test,
            "diet_plan": diet_plan,
            "overall_message": self._generate_overall_message(results, context)
        }
    
    def _generate_test_insights(self, test_name: str, status: str) -> tuple:
        """Generate structured insights for common lab tests"""
        test_lower = test_name.lower()
        
        # Vitamin D insights
        if "vitamin d" in test_lower:
            importance = "Vitamin D is crucial for bone health, immune function, and mood regulation."
            if status == "low":
                reasons = ["Limited sun exposure", "Inadequate dietary intake", "Kidney or liver disease"]
                risks = ["Osteoporosis", "Increased fracture risk", "Immune dysfunction", "Mood disorders"]
                meal_plan = "Increase sunlight exposure, consume fortified dairy, fatty fish, and mushrooms"
            else:
                reasons = ["Excessive supplementation", "Over-fortified foods"]
                risks = ["Kidney stones", "Hypercalcemia", "Nausea"]
                meal_plan = "Reduce vitamin D supplements and fortified foods"
        
        # Calcium insights
        elif "calcium" in test_lower:
            importance = "Calcium is vital for bone health, muscle function, and nerve transmission."
            if status == "low":
                reasons = ["Vitamin D deficiency", "Poor dietary intake", "Kidney disease", "Hypoparathyroidism"]
                risks = ["Osteoporosis", "Muscle cramps", "Numbness", "Bone pain"]
                meal_plan = "Consume dairy products, leafy greens, and calcium-fortified foods"
            else:
                reasons = ["Hyperparathyroidism", "Excessive supplements", "Kidney disease"]
                risks = ["Kidney stones", "Heart arrhythmias", "Confusion"]
                meal_plan = "Limit calcium supplements and dairy intake"
        
        # Bilirubin insights
        elif "bilirubin" in test_lower:
            importance = "Bilirubin levels help assess liver function and red blood cell breakdown."
            if status == "high":
                reasons = ["Liver damage", "Bile duct obstruction", "Hemolytic anemia"]
                risks = ["Jaundice", "Liver disease progression", "Fatigue"]
                meal_plan = "Avoid alcohol, eat liver-supporting foods like leafy greens"
            else:
                reasons = ["Normal liver function"]
                risks = ["Generally not concerning"]
                meal_plan = "Maintain balanced diet"
        
        # Hemoglobin insights
        elif "hemoglobin" in test_lower:
            importance = "Hemoglobin is essential for oxygen transport throughout the body."
            if status == "low":
                reasons = ["Iron deficiency", "Blood loss", "Chronic disease"]
                risks = ["Fatigue", "Weakness", "Shortness of breath"]
                meal_plan = "Consume iron-rich foods like red meat, spinach, and lentils"
            else:
                reasons = ["Dehydration", "Smoking", "Living at high altitude"]
                risks = ["Blood clotting issues", "Stroke risk"]
                meal_plan = "Stay hydrated, avoid smoking"
        
        # Default for unknown tests
        else:
            importance = f"{test_name} is important for overall health assessment."
            reasons = ["Various factors can affect this test"]
            risks = ["Consult healthcare provider for interpretation"]
            meal_plan = "Maintain a balanced, nutritious diet"
        
        return importance, reasons, risks, meal_plan

    def _extract_importance(self, analysis: str) -> str:
        """Extract importance from analysis"""
        if "Why important:" in analysis:
            parts = analysis.split("Why important:")
            if len(parts) > 1:
                importance = parts[1].split("Reasons for")[0].split("Meal plan:")[0].strip()
                return importance
        return "Important for overall health."
    
    def _extract_reasons_low(self, analysis: str) -> List[str]:
        """Extract reasons for low values"""
        if "Reasons for low:" in analysis:
            parts = analysis.split("Reasons for low:")
            if len(parts) > 1:
                reasons = parts[1].split("Risks if low:")[0].split("Reasons for high:")[0].strip()
                return [reasons] if reasons else []
        return []
    
    def _extract_reasons_high(self, analysis: str) -> List[str]:
        """Extract reasons for high values"""
        if "Reasons for high:" in analysis:
            parts = analysis.split("Reasons for high:")
            if len(parts) > 1:
                reasons = parts[1].split("Risks if high:")[0].split("Meal plan:")[0].strip()
                return [reasons] if reasons else []
        return []
    
    def _extract_risks_low(self, analysis: str) -> List[str]:
        """Extract risks for low values"""
        if "Risks if low:" in analysis:
            parts = analysis.split("Risks if low:")
            if len(parts) > 1:
                risks = parts[1].split("Risks if high:")[0].split("Meal plan:")[0].strip()
                return [risks] if risks else []
        return []
    
    def _extract_risks_high(self, analysis: str) -> List[str]:
        """Extract risks for high values"""
        if "Risks if high:" in analysis:
            parts = analysis.split("Risks if high:")
            if len(parts) > 1:
                risks = parts[1].split("Meal plan:")[0].strip()
                return [risks] if risks else []
        return []
    
    def _extract_meal_plan(self, analysis: str) -> str:
        """Extract meal plan from analysis"""
        if "Meal plan:" in analysis:
            parts = analysis.split("Meal plan:")
            if len(parts) > 1:
                return parts[1].strip()
        return ""
    
    def _extract_foods_to_add(self, recommendation: str) -> List[str]:
        """Extract foods to add from recommendation"""
        foods = []
        rec_lower = recommendation.lower()
        if "dairy" in rec_lower:
            foods.append("dairy products")
        if "fish" in rec_lower:
            foods.append("fatty fish")
        if "meat" in rec_lower:
            foods.append("lean meats")
        if "spinach" in rec_lower or "leafy greens" in rec_lower:
            foods.append("leafy greens")
        if "nuts" in rec_lower:
            foods.append("nuts")
        if "fruits" in rec_lower:
            foods.append("fruits")
        if "vegetables" in rec_lower:
            foods.append("vegetables")
        return foods
    
    def _extract_foods_to_limit(self, recommendation: str) -> List[str]:
        """Extract foods to limit from recommendation"""
        foods = []
        rec_lower = recommendation.lower()
        if "alcohol" in rec_lower:
            foods.append("alcohol")
        if "processed" in rec_lower:
            foods.append("processed foods")
        if "fried" in rec_lower:
            foods.append("fried foods")
        if "soy" in rec_lower:
            foods.append("soy products")
        return foods
    
    def _generate_meal_ideas(self, recommendations: List[str]) -> List[Dict[str, Any]]:
        """Generate dynamic meal ideas based on test results and recommendations"""
        meals = []
        
        # Analyze recommendations to determine what nutrients are needed
        rec_text = ' '.join(recommendations).lower()
        
        # Vitamin D meals
        if any(keyword in rec_text for keyword in ['vitamin d', 'sunlight', 'fortified', 'fish']):
            meals.append({
                "name": "Fortified Cereal with Milk",
                "youtube_link": "https://youtube.com/watch?v=breakfast-cereal",
                "ingredients": [
                    {"name": "fortified cereal", "purchase_link": "https://example.com/cereal"},
                    {"name": "milk", "purchase_link": "https://example.com/milk"},
                    {"name": "fresh fruit", "purchase_link": "https://example.com/fruit"}
                ],
                "instructions": "Prepare cereal with milk and add fresh fruit for extra nutrition.",
                "why_this_meal": "This meal is rich in calcium and vitamin D, essential for bone health.",
                "supports_tests": ["Vitamin D (25-oh)", "S. Calcium"]
            })
            
            meals.append({
                "name": "Grilled Salmon with Vegetables",
                "youtube_link": "https://youtube.com/watch?v=grilled-salmon",
                "ingredients": [
                    {"name": "salmon", "purchase_link": "https://example.com/salmon"},
                    {"name": "mixed vegetables", "purchase_link": "https://example.com/vegetables"},
                    {"name": "olive oil", "purchase_link": "https://example.com/olive-oil"}
                ],
                "instructions": "Grill salmon and serve with a variety of steamed vegetables.",
                "why_this_meal": "Salmon is a good source of vitamin D, and vegetables provide essential minerals and fiber.",
                "supports_tests": ["Vitamin D (25-oh)", "S. Bilirubin D"]
            })
        
        # Calcium meals
        if any(keyword in rec_text for keyword in ['calcium', 'dairy', 'bone']):
            meals.append({
                "name": "Yogurt Parfait with Granola and Berries",
                "youtube_link": "https://youtube.com/watch?v=yogurt-parfait",
                "ingredients": [
                    {"name": "yogurt", "purchase_link": "https://example.com/yogurt"},
                    {"name": "granola", "purchase_link": "https://example.com/granola"},
                    {"name": "mixed berries", "purchase_link": "https://example.com/berries"}
                ],
                "instructions": "Layer yogurt, granola, and berries in a bowl for a nutritious snack.",
                "why_this_meal": "Yogurt is rich in calcium, and berries provide antioxidants and fiber.",
                "supports_tests": ["S. Calcium"]
            })
        
        # Iron/Hemoglobin meals
        if any(keyword in rec_text for keyword in ['iron', 'hemoglobin', 'red meat', 'spinach', 'lentils']):
            meals.append({
                "name": "Iron-Rich Spinach Salad",
                "youtube_link": "https://youtube.com/watch?v=spinach-salad",
                "ingredients": [
                    {"name": "spinach", "purchase_link": "https://example.com/spinach"},
                    {"name": "lean beef", "purchase_link": "https://example.com/beef"},
                    {"name": "citrus dressing", "purchase_link": "https://example.com/dressing"}
                ],
                "instructions": "Combine fresh spinach with grilled lean beef and citrus dressing.",
                "why_this_meal": "Iron from beef with vitamin C from citrus helps with iron absorption.",
                "supports_tests": ["Hemoglobin", "Iron"]
            })
            
            meals.append({
                "name": "Lentil and Bean Power Bowl",
                "youtube_link": "https://youtube.com/watch?v=lentil-bowl",
                "ingredients": [
                    {"name": "red lentils", "purchase_link": "https://example.com/lentils"},
                    {"name": "quinoa", "purchase_link": "https://example.com/quinoa"},
                    {"name": "bell peppers", "purchase_link": "https://example.com/peppers"}
                ],
                "instructions": "Cook lentils and quinoa, serve with roasted bell peppers.",
                "why_this_meal": "Lentils are high in iron and protein, quinoa provides complete amino acids.",
                "supports_tests": ["Hemoglobin", "Protein levels"]
            })
        
        # Liver support meals
        if any(keyword in rec_text for keyword in ['liver', 'bilirubin', 'alcohol']):
            meals.append({
                "name": "Liver-Support Green Smoothie",
                "youtube_link": "https://youtube.com/watch?v=green-smoothie",
                "ingredients": [
                    {"name": "kale", "purchase_link": "https://example.com/kale"},
                    {"name": "green apple", "purchase_link": "https://example.com/apple"},
                    {"name": "lemon", "purchase_link": "https://example.com/lemon"}
                ],
                "instructions": "Blend kale, apple, and lemon with water for a liver-cleansing drink.",
                "why_this_meal": "Green vegetables support liver detoxification and overall health.",
                "supports_tests": ["S. Bilirubin D", "Liver function"]
            })
        
        # Default meal if no specific needs detected
        if not meals:
            meals.append({
                "name": "Balanced Mediterranean Bowl",
                "youtube_link": "https://youtube.com/watch?v=mediterranean-bowl",
                "ingredients": [
                    {"name": "quinoa", "purchase_link": "https://example.com/quinoa"},
                    {"name": "chickpeas", "purchase_link": "https://example.com/chickpeas"},
                    {"name": "olive oil", "purchase_link": "https://example.com/olive-oil"}
                ],
                "instructions": "Combine quinoa, chickpeas, and vegetables with olive oil dressing.",
                "why_this_meal": "A balanced meal with protein, healthy fats, and complex carbohydrates.",
                "supports_tests": ["Overall health"]
            })
        
        # Limit to 3-4 meals to avoid overwhelming the user
        return meals[:4]
        return meals
    
    def _generate_overall_message(self, results: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """Generate overall message"""
        flagged_count = len([r for r in results if r.get("status") in ["high", "low"]])
        if flagged_count > 0:
            return f"Your lab results show {flagged_count} values outside normal range. Following the meal plan can help improve these levels."
        else:
            return "Your lab results are within normal ranges. Continue maintaining a balanced diet for optimal health."

    def unload_model(self):
        """Unload model to free memory"""
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Pretrained model unloaded")

# Global instance for reuse
_pretrained_llm_service = None

def get_pretrained_llm_service() -> PretrainedLLMService:
    """Get singleton instance of pretrained LLM service"""
    global _pretrained_llm_service
    if _pretrained_llm_service is None:
        _pretrained_llm_service = PretrainedLLMService()
    return _pretrained_llm_service

def generate_clinical_summary_local(
    test_name: str, 
    value: str, 
    reference_range: str
) -> Optional[str]:
    """
    Convenience function for generating clinical summary using local model
    Compatible with existing API interface
    """
    service = get_pretrained_llm_service()
    return service.generate_clinical_analysis(test_name, value, reference_range)

def generate_structured_summary_local(
    context: Dict[str, Any], 
    results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convenience function for generating structured summary using local model
    Compatible with existing API interface (replaces summarize_results_structured)
    """
    service = get_pretrained_llm_service()
    return service.generate_structured_summary(context, results)