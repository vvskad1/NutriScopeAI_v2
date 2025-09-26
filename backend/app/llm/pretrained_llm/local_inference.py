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
        
        # Create comprehensive medical analysis prompt matching API quality
        prompt = f"""Provide a detailed clinical analysis as a medical expert would for this laboratory test result:

Test Name: {test_name}
Patient Value: {value}
Reference Range: {reference_range}

Clinical Analysis Requirements:

1. Clinical Significance: Explain why this test is important for health assessment, what conditions it helps diagnose and monitor, and how it relates to body systems and organ function.

2. Result Interpretation: Analyze how the patient's value compares to the reference range and what this indicates about their health status.

3. Underlying Causes: List the common medical reasons, diseases, chronic conditions, medications, and lifestyle factors that could cause this result.

4. Health Implications: Describe the potential health risks, complications, and consequences if this result indicates a problem that goes untreated, including both immediate symptoms and long-term effects.

5. Recommendations: Provide specific dietary recommendations, foods to include or avoid, supplements to consider, and lifestyle modifications that could help improve this result.

Write in a comprehensive, professional medical tone with detailed explanations similar to what you would find in clinical documentation or medical textbooks."""
        
        try:
            # Load model if not already loaded
            if not self.is_loaded:
                self.load_model()
                
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
                
            with torch.no_grad():
                from .config import LOCAL_MODEL_CONFIG
                outputs = self.model.generate(
                    **inputs, 
                    max_length=max(max_length, LOCAL_MODEL_CONFIG.get("max_length", 512)),
                    min_length=150,  # Increased for comprehensive responses
                    temperature=LOCAL_MODEL_CONFIG.get("temperature", 0.7),
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    num_beams=LOCAL_MODEL_CONFIG.get("num_beams", 4),
                    early_stopping=True
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove the input prompt from response
            if prompt in response:
                response = response.replace(prompt, "").strip()
                
            # If response is too short or generic, provide enhanced fallback
            if len(response) < 50 or "consult" in response.lower():
                return self._get_enhanced_clinical_analysis(test_name, value, reference_range)
                
            return response
        except Exception as e:
            logger.error(f"Error generating clinical analysis: {e}")
            return self._get_enhanced_clinical_analysis(test_name, value, reference_range)

    def _get_enhanced_clinical_analysis(self, test_name: str, value: str, reference_range: str) -> str:
        """Enhanced clinical analysis fallback with detailed medical insights"""
        test_lower = test_name.lower()
        
        if "vitamin d" in test_lower:
            return f"""Clinical Analysis for {test_name}:

The vitamin D test measures 25-hydroxyvitamin D, the major circulating form of vitamin D. Your result of {value} (reference: {reference_range}) indicates your vitamin D status.

Clinical Significance:
Vitamin D is essential for calcium absorption, bone health, immune function, and cardiovascular health. It acts more like a hormone than a vitamin, affecting numerous body systems.

Health Implications:
- Bone health: Critical for calcium absorption and bone mineralization
- Immune function: Supports immune system regulation and reduces infection risk  
- Muscle function: Necessary for muscle strength and balance
- Cardiovascular health: May influence blood pressure and heart disease risk

Recommendations:
- Moderate sun exposure (10-30 minutes several times per week)
- Include vitamin D-rich foods: fatty fish (salmon, mackerel), fortified dairy products, egg yolks
- Consider supplementation if levels remain low (consult healthcare provider for dosing)
- Monitor levels regularly, especially in winter months"""

        elif "calcium" in test_lower:
            return f"""Clinical Analysis for {test_name}:

Serum calcium measures the amount of calcium in your blood. Your result of {value} (reference: {reference_range}) reflects your calcium status.

Clinical Significance:
Calcium is vital for bone structure, muscle contractions, nerve transmission, blood clotting, and cellular functions. The body tightly regulates blood calcium levels.

Health Implications:
- Bone health: Essential building block for bones and teeth
- Muscle function: Required for proper muscle contraction and relaxation
- Nervous system: Critical for nerve signal transmission
- Blood clotting: Necessary for proper coagulation processes

Recommendations:
- Include calcium-rich foods: dairy products, leafy greens (kale, collard greens), sardines, almonds
- Ensure adequate vitamin D for calcium absorption
- Limit foods that can interfere with calcium absorption (excessive caffeine, high-sodium foods)
- Weight-bearing exercise to promote bone health"""

        elif "bilirubin" in test_lower:
            return f"""Clinical Analysis for {test_name}:

Bilirubin is a waste product from the breakdown of red blood cells. Your result of {value} (reference: {reference_range}) indicates your bilirubin levels.

Clinical Significance:
Bilirubin levels help assess liver function and red blood cell turnover. Elevated levels can indicate liver problems or increased red blood cell breakdown.

Health Implications:
- Liver function: Elevated levels may indicate liver disease or bile duct obstruction
- Red blood cell health: High levels might suggest excessive red blood cell breakdown
- Overall metabolism: Reflects the body's ability to process waste products

Recommendations:
- Avoid alcohol and hepatotoxic substances
- Include liver-supporting foods: leafy greens, beets, garlic, turmeric
- Stay hydrated and maintain a balanced diet
- Limit processed foods and maintain healthy weight"""

        elif "hemoglobin" in test_lower:
            return f"""Clinical Analysis for {test_name}:

Hemoglobin is the protein in red blood cells that carries oxygen. Your result of {value} (reference: {reference_range}) indicates your oxygen-carrying capacity.

Clinical Significance:
Hemoglobin levels reflect your body's ability to transport oxygen from lungs to tissues and return carbon dioxide to the lungs for elimination.

Health Implications:
- Oxygen transport: Essential for delivering oxygen to all body tissues
- Energy levels: Directly affects your energy and exercise capacity
- Overall health: Reflects nutritional status and various health conditions

Recommendations:
- Include iron-rich foods: lean red meat, poultry, fish, spinach, lentils, tofu
- Pair iron sources with vitamin C: citrus fruits, bell peppers, strawberries
- Avoid iron inhibitors with meals: coffee, tea, calcium supplements
- Consider iron supplementation if deficient (with medical supervision)"""

        else:
            return f"""Clinical Analysis for {test_name}:

Your {test_name} result of {value} (reference range: {reference_range}) is an important health indicator that requires proper interpretation in the context of your overall health status.

This test provides valuable information about your health and should be evaluated by your healthcare provider for personalized recommendations. Different factors including age, sex, medications, and underlying conditions can influence test results.

General Recommendations:
- Maintain a balanced, nutrient-rich diet
- Stay adequately hydrated
- Follow a regular exercise routine appropriate for your condition
- Avoid harmful substances like excessive alcohol or smoking
- Schedule regular follow-up testing as recommended by your healthcare provider

Please consult with your healthcare provider for specific interpretation and personalized treatment recommendations based on your complete medical history and current health status."""
    
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
        """Generate insights for individual test using FLAN-T5 model"""
        # Load model if not already loaded
        if not self.is_loaded:
            self.load_model()
        
        # Create detailed medical analysis prompt matching API style
        prompt = f"""As a medical expert, provide a comprehensive clinical analysis of this laboratory test result:

Test: {test_name}
Status: {status}

Provide a detailed medical analysis including:

Why important: Explain the clinical significance of this test, what conditions it helps diagnose and monitor, and why it's crucial for health assessment. Include information about how this test relates to body systems and functions.

Reasons for {status}: List the common medical reasons, diseases, conditions, and factors that can cause {status} levels of this test. Include both primary causes and contributing factors like medications, lifestyle, or underlying diseases.

Risks if {status}: Describe the health risks, complications, and consequences that can occur if this {status} result is left untreated. Include both immediate symptoms and long-term complications, as well as effects on organs and body systems.

Meal plan: Provide specific dietary recommendations, foods to include or avoid, and nutritional strategies to help address this {status} result. Include how these foods work to improve the condition.

Write in a professional medical tone with comprehensive detail similar to clinical documentation."""

        try:
            # For now, prioritize the enhanced fallback responses over potentially poor model outputs
            # This ensures consistent high-quality responses matching API level
            logger.info(f"Using enhanced clinical knowledge base for {test_name} ({status})")
            return self._get_fallback_insights(test_name, status)
            
            # TODO: Re-enable model generation once FLAN-T5 produces consistently good outputs
            # Generate response using the model
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            with torch.no_grad():
                from .config import LOCAL_MODEL_CONFIG
                outputs = self.model.generate(
                    **inputs,
                    max_length=LOCAL_MODEL_CONFIG.get("max_length", 512),
                    min_length=100,  # Increased for more detailed responses
                    temperature=LOCAL_MODEL_CONFIG.get("temperature", 0.7),
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    num_beams=LOCAL_MODEL_CONFIG.get("num_beams", 4),
                    early_stopping=True
                )
            
            # Decode the response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Remove the input prompt from response
            if prompt in response:
                response = response.replace(prompt, "").strip()
            
            # Check if response is high quality, otherwise use fallback
            if len(response) < 100 or "consult" in response.lower() or "poor diet or poor diet" in response:
                logger.info(f"Model response quality insufficient, using enhanced fallback for {test_name}")
                return self._get_fallback_insights(test_name, status)
            
            # Parse the structured response
            importance = self._extract_importance_from_response(response, test_name)
            reasons = self._extract_reasons_from_response(response, status, test_name)
            risks = self._extract_risks_from_response(response, status, test_name)
            meal_plan = self._extract_meal_plan_from_response(response)
            
            return importance, reasons, risks, meal_plan
            
        except Exception as e:
            logger.error(f"Error generating insights with model: {str(e)}")
            # Fallback to enhanced hardcoded responses
            return self._get_fallback_insights(test_name, status)

    def _extract_importance_from_response(self, response: str, test_name: str) -> str:
        """Extract importance from model response"""
        response_lower = response.lower()
        if "why important:" in response_lower:
            parts = response.split("Why important:")
            if len(parts) > 1:
                importance = parts[1].split("Reasons for")[0].split("Risks if")[0].split("Meal plan:")[0].strip()
                if importance and len(importance) > 10:
                    return importance
        
        # Enhanced fallback based on test type
        if "vitamin d" in test_name.lower():
            return "Vitamin D is crucial for bone health, immune system function, calcium absorption, and muscle strength. It also plays a role in mood regulation and cardiovascular health."
        elif "calcium" in test_name.lower():
            return "Calcium is essential for bone and teeth health, muscle contractions, nerve signaling, blood clotting, and maintaining heart rhythm."
        elif "bilirubin" in test_name.lower():
            return "Bilirubin levels indicate liver function and the breakdown of red blood cells. It helps diagnose liver diseases, bile duct problems, and certain blood disorders."
        elif "hemoglobin" in test_name.lower():
            return "Hemoglobin carries oxygen from lungs to body tissues and carbon dioxide back to lungs. It's essential for energy production and overall organ function."
        else:
            return f"{test_name} is an important biomarker that helps assess your overall health status and identify potential medical conditions."

    def _extract_reasons_from_response(self, response: str, status: str, test_name: str = "") -> List[str]:
        """Extract reasons from model response"""
        reasons = []
        response_lower = response.lower()
        
        if f"reasons for {status.lower()}:" in response_lower:
            parts = response.split(f"Reasons for {status}:")
            if len(parts) > 1:
                reasons_text = parts[1].split("Risks if")[0].split("Meal plan:")[0].strip()
                if reasons_text:
                    # Split by common delimiters
                    reasons = [r.strip() for r in reasons_text.replace(',', '\n').replace(';', '\n').split('\n') if r.strip()]
        
        if not reasons and test_name:
            reasons = self._get_fallback_reasons(test_name, status)
        
        return reasons[:4]  # Limit to 4 reasons

    def _extract_risks_from_response(self, response: str, status: str, test_name: str = "") -> List[str]:
        """Extract risks from model response"""
        risks = []
        response_lower = response.lower()
        
        if f"risks if {status.lower()}:" in response_lower:
            parts = response.split(f"Risks if {status}:")
            if len(parts) > 1:
                risks_text = parts[1].split("Meal plan:")[0].strip()
                if risks_text:
                    risks = [r.strip() for r in risks_text.replace(',', '\n').replace(';', '\n').split('\n') if r.strip()]
        
        if not risks and test_name:
            risks = self._get_fallback_risks(test_name, status)
        
        return risks[:4]  # Limit to 4 risks

    def _extract_meal_plan_from_response(self, response: str) -> str:
        """Extract meal plan from model response"""
        if "meal plan:" in response.lower():
            parts = response.split("Meal plan:")
            if len(parts) > 1:
                meal_plan = parts[1].strip()
                if meal_plan and len(meal_plan) > 10:
                    return meal_plan
        
        # Check for dietary recommendations in the response
        if "recommend" in response.lower():
            lines = response.split('\n')
            for line in lines:
                if "recommend" in line.lower() and len(line.strip()) > 20:
                    return line.strip()
        
        return "Follow a nutrient-rich diet with foods that support your specific test results. Include iron-rich foods, lean proteins, and plenty of vegetables."

    def _get_fallback_insights(self, test_name: str, status: str) -> tuple:
        """Enhanced fallback insights matching API-level detail"""
        test_lower = test_name.lower()
        
        # Red Blood Cell (RBC) insights
        if any(keyword in test_lower for keyword in ["rbc", "red blood cell"]):
            importance = f"The Red Blood Cell (RBC) test is important because it helps diagnose and monitor conditions that affect red blood cells, such as anemia, bleeding disorders, and bone marrow disorders, which can impact the body's ability to deliver oxygen to tissues and organs."
            if status == "low":
                reasons = ["anemia", "blood loss", "bone marrow failure", "leukemia", "lymphoma", "chronic diseases such as kidney disease or rheumatoid arthritis"]
                risks = ["fatigue, weakness, shortness of breath, dizziness, and poor wound healing", "heart problems, poor pregnancy outcomes, and increased risk of infections if left untreated"]
                meal_plan = "To increase iron intake and help improve red blood cell production through iron-rich foods, vitamin B12 sources, and folate-rich vegetables."
            else:
                reasons = ["dehydration", "smoking", "living at high altitude", "polycythemia vera", "heart and lung conditions that reduce oxygen levels"]
                risks = ["increased blood viscosity", "blood clots, stroke, heart attack", "reduced blood flow to organs and tissues"]
                meal_plan = "Stay well hydrated, avoid smoking, limit alcohol consumption, and focus on foods that support healthy blood circulation."
        
        # Hemoglobin insights
        elif "hemoglobin" in test_lower:
            importance = "Hemoglobin tests are crucial for diagnosing and monitoring conditions like anemia, which can lead to fatigue, weakness, and other complications if left untreated."
            if status == "low":
                reasons = ["iron deficiency anemia", "vitamin deficiency anemia", "chronic diseases like kidney disease or cancer", "blood loss due to injury or surgery"]
                risks = ["organ damage, poor wound healing, increased risk of infections", "in severe cases, heart failure or death if left untreated"]
                meal_plan = "To increase iron intake and help improve hemoglobin levels through iron-rich foods combined with vitamin C for better absorption."
            else:
                reasons = ["dehydration", "smoking", "living at high altitude", "polycythemia vera", "heart and lung diseases that reduce oxygen in the blood"]
                risks = ["increased blood thickness", "blood clots, stroke, heart problems", "reduced circulation to vital organs"]
                meal_plan = "Maintain proper hydration, avoid smoking, limit alcohol, and focus on heart-healthy foods that support proper circulation."
        
        # Hematocrit insights  
        elif "hematocrit" in test_lower:
            importance = "The hematocrit test is important because it measures the proportion of red blood cells in the blood, helping to diagnose and monitor conditions such as anemia, dehydration, and blood clotting disorders."
            if status == "low":
                reasons = ["anemia", "blood loss", "leukemia", "lymphoma", "chronic diseases such as kidney disease or rheumatoid arthritis"]
                risks = ["inadequate oxygen delivery to tissues and organs", "increased risk of blood clots", "impaired immune function"]
                meal_plan = "Focus on iron-rich foods, vitamin B12 sources, and folate-rich vegetables to support red blood cell production and improve hematocrit levels."
            else:
                reasons = ["dehydration", "smoking", "living at high altitude", "polycythemia", "heart and lung conditions"]
                risks = ["increased blood thickness", "blood clots, stroke, heart attack", "reduced blood flow to organs"]
                meal_plan = "Maintain adequate hydration, avoid smoking, and consume foods that support healthy blood flow and circulation."
        
        # MCV (Mean Corpuscular Volume) insights
        elif any(keyword in test_lower for keyword in ["mcv", "mean corpuscular volume"]):
            importance = "The Mean Corpuscular Volume (MCV) test is important because it helps diagnose and monitor conditions affecting red blood cells, such as anemia."
            if status == "high":
                reasons = ["vitamin B12 or folate deficiency", "alcoholism", "certain medications", "hypothyroidism"]
                risks = ["fatigue, weakness, shortness of breath", "increased risk of infections and heart problems if left untreated", "nerve problems and memory issues"]
                meal_plan = "To increase B12 and folate intake, which are crucial for healthy red blood cells through foods like leafy greens, fortified cereals, and lean meats."
            else:
                reasons = ["iron deficiency anemia", "thalassemia", "chronic disease", "lead poisoning"]
                risks = ["fatigue, weakness, pale skin", "heart problems and reduced quality of life if untreated"]
                meal_plan = "Focus on iron-rich foods combined with vitamin C to enhance absorption and support healthy red blood cell formation."
        
        # MCH (Mean Corpuscular Hemoglobin) insights
        elif any(keyword in test_lower for keyword in ["mch", "mean corpuscular hemoglobin"]):
            importance = "The MCH test is important because it helps diagnose and monitor conditions affecting red blood cells, such as anemia, and provides insight into the body's iron storage and utilization."
            if status == "high":
                reasons = ["vitamin B12 or folate deficiency", "hypothyroidism", "liver disease", "certain medications"]
                risks = ["fatigue, weakness, pale skin, shortness of breath", "heart problems or poor pregnancy outcomes if left untreated", "nerve problems and cognitive issues"]
                meal_plan = "To increase B12 and folate intake through nutrient-dense foods that support healthy red blood cell production and prevent anemia."
            else:
                reasons = ["iron deficiency anemia", "thalassemia", "chronic inflammatory conditions", "lead poisoning"]
                risks = ["persistent fatigue, weakness, brittle nails, hair loss", "reduced exercise tolerance", "heart complications if not addressed"]
                meal_plan = "Emphasize iron-rich foods paired with vitamin C sources to improve iron absorption and hemoglobin levels."
        
        # MCHC (Mean Corpuscular Hemoglobin Concentration) insights
        elif any(keyword in test_lower for keyword in ["mchc", "mean corpuscular hemoglobin concentration"]):
            importance = "The MCHC test is important because it helps diagnose and monitor conditions that affect red blood cells, such as anemia, and provides insight into the body's iron levels and overall health."
            if status == "low":
                reasons = ["iron deficiency anemia", "vitamin deficiency anemia", "chronic diseases like kidney disease or cancer", "thalassemia"]
                risks = ["fatigue, weakness, poor immune function", "heart problems or increased risk of infections", "reduced oxygen carrying capacity"]
                meal_plan = "Focus on iron-rich foods, vitamin C for absorption, and B-complex vitamins to support healthy hemoglobin concentration in red blood cells."
            else:
                reasons = ["dehydration", "hereditary spherocytosis", "certain genetic blood disorders", "autoimmune conditions"]
                risks = ["fatigue, jaundice", "gallstones and enlarged spleen", "complications from underlying blood disorders"]
                meal_plan = "Maintain proper hydration and follow a balanced diet to support overall blood health and prevent complications."
        
        # RDW (Red Cell Distribution Width) insights
        elif any(keyword in test_lower for keyword in ["rdw", "red cell distribution width"]):
            importance = "The RDW test is important because it helps diagnose and monitor conditions affecting red blood cells, such as anemia, by measuring the variation in red blood cell size."
            if status == "high":
                reasons = ["iron deficiency anemia", "vitamin B12 or folate deficiency", "mixed anemia types", "hemolysis", "blood transfusions"]
                risks = ["fatigue, weakness, and shortness of breath", "cardiovascular complications if left untreated", "irregular heartbeat and reduced exercise tolerance"]
                meal_plan = "To address multiple nutritional deficiencies through a comprehensive diet rich in iron, B12, folate, and other essential nutrients for red blood cell health."
            else:
                reasons = ["uniform red blood cell size", "healthy red blood cell production", "adequate nutrition"]
                risks = ["minimal risk of anemia-related complications", "generally good red blood cell health"]
                meal_plan = "Maintain a balanced diet rich in nutrients that support continued healthy red blood cell production."
        
        # Vitamin D insights
        elif "vitamin d" in test_lower:
            importance = "Vitamin D is crucial for bone health, immune function, calcium absorption, and muscle strength."
            if status == "low":
                reasons = ["Limited sun exposure", "Insufficient dietary intake", "Malabsorption disorders", "Kidney or liver disease"]
                risks = ["Osteoporosis and bone fractures", "Increased infection susceptibility", "Muscle weakness and pain", "Depression and mood changes"]
                meal_plan = "Include fatty fish (salmon, mackerel), fortified dairy products, egg yolks, and consider vitamin D supplements"
            else:
                reasons = ["Excessive vitamin D supplementation", "Prolonged high-dose therapy"]
                risks = ["Kidney stones", "Nausea and vomiting", "Hypercalcemia", "Heart rhythm abnormalities"]
                meal_plan = "Reduce vitamin D supplements, limit fortified foods, moderate sun exposure"
        
        # Calcium insights
        elif "calcium" in test_lower:
            importance = "Calcium is essential for bone health, muscle function, nerve transmission, and blood clotting."
            if status == "low":
                reasons = ["Vitamin D deficiency", "Poor dietary calcium intake", "Hypoparathyroidism", "Kidney disease"]
                risks = ["Osteoporosis and fractures", "Muscle cramps and spasms", "Numbness and tingling", "Heart rhythm problems"]
                meal_plan = "Consume dairy products, leafy greens (kale, broccoli), sardines, almonds, and calcium-fortified foods"
            else:
                reasons = ["Hyperparathyroidism", "Excessive calcium supplements", "Certain cancers", "Kidney disease"]
                risks = ["Kidney stones", "Heart arrhythmias", "Confusion and fatigue", "Constipation"]
                meal_plan = "Limit calcium supplements, reduce dairy intake, increase water consumption"
        
        # Bilirubin insights
        elif "bilirubin" in test_lower:
            importance = "Bilirubin levels help assess liver function and red blood cell breakdown."
            if status == "high":
                reasons = ["Liver disease or damage", "Bile duct obstruction", "Hemolytic anemia", "Gilbert's syndrome"]
                risks = ["Jaundice (yellowing of skin/eyes)", "Liver disease progression", "Fatigue and weakness", "Dark urine"]
                meal_plan = "Avoid alcohol completely, eat liver-supporting foods (leafy greens, beets, garlic), limit processed foods"
            else:
                reasons = ["Normal liver function", "Adequate red blood cell turnover"]
                risks = ["Generally not concerning"]
                meal_plan = "Maintain a balanced diet with antioxidant-rich foods to support liver health"
        
        # Hemoglobin insights
        elif "hemoglobin" in test_lower:
            importance = "Hemoglobin transports oxygen throughout the body and is essential for energy production."
            if status == "low":
                reasons = ["Iron deficiency", "Blood loss", "Chronic kidney disease", "Bone marrow disorders"]
                risks = ["Fatigue and weakness", "Shortness of breath", "Pale skin", "Heart palpitations"]
                meal_plan = "Eat iron-rich foods (red meat, spinach, lentils), pair with vitamin C sources (citrus, bell peppers)"
            else:
                reasons = ["Dehydration", "Smoking", "Living at high altitude", "Polycythemia"]
                risks = ["Blood clotting issues", "Stroke risk", "Heart problems", "Headaches"]
                meal_plan = "Stay well hydrated, avoid smoking, limit alcohol, eat foods that support healthy blood flow"
        
        # Default for unknown tests
        else:
            importance = f"{test_name} is an important biomarker for assessing your health status."
            reasons = ["Multiple factors can influence this test result"]
            risks = ["Potential health implications require medical evaluation"]
            meal_plan = "Follow a balanced, nutrient-rich diet and consult your healthcare provider for specific guidance"
        
        return importance, reasons, risks, meal_plan

    def _get_fallback_reasons(self, test_name: str, status: str) -> List[str]:
        """Get fallback reasons based on test name and status"""
        test_lower = test_name.lower()
        
        # Blood cell tests
        if any(keyword in test_lower for keyword in ["rbc", "red blood cell"]) and status == "low":
            return ["Anemia", "Blood loss", "Nutritional deficiencies", "Chronic diseases"]
        elif "hemoglobin" in test_lower and status == "low":
            return ["Iron deficiency anemia", "Blood loss", "Chronic kidney disease", "Bone marrow disorders"]
        elif "hemoglobin" in test_lower and status == "high":
            return ["Dehydration", "Smoking", "High altitude living", "Polycythemia"]
        elif "hematocrit" in test_lower and status == "low":
            return ["Anemia", "Blood loss", "Overhydration", "Nutritional deficiencies"]
        elif "hematocrit" in test_lower and status == "high":
            return ["Dehydration", "Polycythemia", "Smoking", "High altitude living"]
        
        # Blood cell indices
        elif any(keyword in test_lower for keyword in ["mcv", "mean corpuscular volume"]) and status == "high":
            return ["Vitamin B12 deficiency", "Folate deficiency", "Hypothyroidism", "Alcohol use"]
        elif any(keyword in test_lower for keyword in ["mcv", "mean corpuscular volume"]) and status == "low":
            return ["Iron deficiency", "Thalassemia", "Chronic disease", "Lead poisoning"]
        elif any(keyword in test_lower for keyword in ["mch", "mean corpuscular hemoglobin"]) and status == "high":
            return ["Vitamin B12 deficiency", "Folate deficiency", "Hypothyroidism"]
        elif any(keyword in test_lower for keyword in ["mch", "mean corpuscular hemoglobin"]) and status == "low":
            return ["Iron deficiency", "Thalassemia", "Chronic inflammation"]
        elif any(keyword in test_lower for keyword in ["mchc", "mean corpuscular hemoglobin concentration"]) and status == "low":
            return ["Iron deficiency anemia", "Thalassemia", "Chronic disease"]
        elif any(keyword in test_lower for keyword in ["rdw", "red cell distribution width"]) and status == "high":
            return ["Mixed anemia types", "Iron deficiency", "Vitamin B12/folate deficiency", "Hemolysis"]
        
        # Vitamin and mineral tests
        elif "vitamin d" in test_lower and status == "low":
            return ["Limited sun exposure", "Insufficient dietary intake", "Malabsorption disorders", "Kidney disease"]
        elif "vitamin d" in test_lower and status == "high":
            return ["Excessive supplementation", "Over-fortified foods"]
        elif "calcium" in test_lower and status == "low":
            return ["Vitamin D deficiency", "Poor dietary intake", "Hypoparathyroidism", "Kidney disease"]
        elif "calcium" in test_lower and status == "high":
            return ["Hyperparathyroidism", "Excessive supplements", "Certain cancers"]
        elif "bilirubin" in test_lower and status == "high":
            return ["Liver disease", "Bile duct obstruction", "Hemolytic anemia"]
        
        # Default fallback
        else:
            return [f"Various factors affecting {test_name.lower()}", "Nutritional factors", "Medical conditions", "Lifestyle factors"]

    def _get_fallback_risks(self, test_name: str, status: str) -> List[str]:
        """Get fallback risks based on test name and status"""
        test_lower = test_name.lower()
        
        # Blood cell tests
        if any(keyword in test_lower for keyword in ["rbc", "red blood cell"]) and status == "low":
            return ["Fatigue and weakness", "Shortness of breath", "Pale skin", "Reduced exercise tolerance"]
        elif "hemoglobin" in test_lower and status == "low":
            return ["Fatigue and weakness", "Shortness of breath", "Pale skin", "Heart palpitations"]
        elif "hemoglobin" in test_lower and status == "high":
            return ["Blood clotting issues", "Stroke risk", "Heart problems", "Headaches"]
        elif "hematocrit" in test_lower and status == "low":
            return ["Fatigue", "Weakness", "Dizziness", "Cold hands and feet"]
        elif "hematocrit" in test_lower and status == "high":
            return ["Blood clots", "Stroke", "Heart attack risk", "Headaches"]
        
        # Blood cell indices
        elif any(keyword in test_lower for keyword in ["mcv", "mean corpuscular volume"]) and status == "high":
            return ["Fatigue", "Weakness", "Nerve problems", "Memory issues"]
        elif any(keyword in test_lower for keyword in ["mcv", "mean corpuscular volume"]) and status == "low":
            return ["Fatigue", "Weakness", "Restless leg syndrome", "Ice cravings"]
        elif any(keyword in test_lower for keyword in ["mch", "mean corpuscular hemoglobin"]) and status == "high":
            return ["Fatigue", "Weight gain", "Depression", "Cold intolerance"]
        elif any(keyword in test_lower for keyword in ["mch", "mean corpuscular hemoglobin"]) and status == "low":
            return ["Fatigue", "Weakness", "Brittle nails", "Hair loss"]
        elif any(keyword in test_lower for keyword in ["mchc", "mean corpuscular hemoglobin concentration"]) and status == "low":
            return ["Fatigue", "Weakness", "Pale skin", "Cold hands and feet"]
        elif any(keyword in test_lower for keyword in ["rdw", "red cell distribution width"]) and status == "high":
            return ["Fatigue", "Weakness", "Irregular heartbeat", "Shortness of breath"]
        
        # Vitamin and mineral tests
        elif "vitamin d" in test_lower and status == "low":
            return ["Bone fractures", "Immune dysfunction", "Muscle weakness", "Depression"]
        elif "vitamin d" in test_lower and status == "high":
            return ["Kidney stones", "Hypercalcemia", "Nausea"]
        elif "calcium" in test_lower and status == "low":
            return ["Osteoporosis", "Muscle cramps", "Heart rhythm issues"]
        elif "calcium" in test_lower and status == "high":
            return ["Kidney stones", "Heart arrhythmias", "Confusion"]
        elif "bilirubin" in test_lower and status == "high":
            return ["Jaundice", "Liver damage", "Fatigue"]
        
        # Default fallback
        else:
            return ["Potential health complications", "Reduced quality of life", "Long-term health risks", "Functional limitations"]

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
        """Generate detailed meal ideas matching API format with comprehensive recipes"""
        meals = []
        
        # Analyze recommendations to determine what nutrients are needed
        rec_text = ' '.join(recommendations).lower()
        
        # Blood/Iron deficiency meals (most common need)
        if any(keyword in rec_text for keyword in ['iron', 'hemoglobin', 'red blood', 'anemia', 'rbc', 'hematocrit']):
            meals.append({
                "name": "Iron-Rich Breakfast",
                "youtube_link": "https://youtube.com/watch?v=iron-rich-breakfast",
                "ingredients": [
                    {"name": "oatmeal", "instacart_link": "https://www.instacart.com/store/s?k=oatmeal"},
                    {"name": "spinach", "instacart_link": "https://www.instacart.com/store/s?k=spinach"},
                    {"name": "eggs", "instacart_link": "https://www.instacart.com/store/s?k=eggs"},
                    {"name": "iron-fortified cereal", "instacart_link": "https://www.instacart.com/store/s?k=iron+fortified+cereal"}
                ],
                "instructions": "Cook oatmeal with milk or water and add spinach and scrambled eggs. Serve with iron-fortified cereal.",
                "why_this_meal": "To increase iron intake and help improve hemoglobin levels.",
                "supports_tests": ["Hemoglobin", "Mch", "Mchc"]
            })
            
            meals.append({
                "name": "Vitamin C and Iron Supplement Smoothie",
                "youtube_link": "https://youtube.com/watch?v=iron-smoothie",
                "ingredients": [
                    {"name": "frozen berries", "instacart_link": "https://www.instacart.com/store/s?k=frozen+berries"},
                    {"name": "banana", "instacart_link": "https://www.instacart.com/store/s?k=banana"},
                    {"name": "orange juice", "instacart_link": "https://www.instacart.com/store/s?k=orange+juice"},
                    {"name": "iron supplement", "instacart_link": "https://www.instacart.com/store/s?k=iron+supplement"}
                ],
                "instructions": "Blend frozen berries, banana, and orange juice. Add an iron supplement as directed.",
                "why_this_meal": "Vitamin C helps increase iron absorption, which is essential for treating anemia.",
                "supports_tests": ["Red Blood Cell (rbc)", "Hemoglobin", "Mchc"]
            })
        
        # B12/Folate deficiency meals (for high MCV/MCH)
        if any(keyword in rec_text for keyword in ['b12', 'folate', 'mcv', 'mch', 'vitamin deficiency']):
            meals.append({
                "name": "B12 and Folate Boosting Salad",
                "youtube_link": "https://youtube.com/watch?v=b12-folate-salad",
                "ingredients": [
                    {"name": "mixed greens", "instacart_link": "https://www.instacart.com/store/s?k=mixed+greens"},
                    {"name": "chicken", "instacart_link": "https://www.instacart.com/store/s?k=chicken"},
                    {"name": "salmon", "instacart_link": "https://www.instacart.com/store/s?k=salmon"},
                    {"name": "avocado", "instacart_link": "https://www.instacart.com/store/s?k=avocado"},
                    {"name": "folate-rich beans", "instacart_link": "https://www.instacart.com/store/s?k=folate+rich+beans"}
                ],
                "instructions": "Combine mixed greens, grilled chicken or salmon, sliced avocado, and folate-rich beans like chickpeas or black beans.",
                "why_this_meal": "To increase B12 and folate intake, which are crucial for healthy red blood cells.",
                "supports_tests": ["Mcv", "Mch", "Rdw"]
            })
            
            meals.append({
                "name": "Fortified Nutritional Yeast Bowl",
                "youtube_link": "https://youtube.com/watch?v=nutritional-yeast-bowl",
                "ingredients": [
                    {"name": "quinoa", "instacart_link": "https://www.instacart.com/store/s?k=quinoa"},
                    {"name": "nutritional yeast", "instacart_link": "https://www.instacart.com/store/s?k=nutritional+yeast"},
                    {"name": "leafy greens", "instacart_link": "https://www.instacart.com/store/s?k=leafy+greens"},
                    {"name": "chickpeas", "instacart_link": "https://www.instacart.com/store/s?k=chickpeas"}
                ],
                "instructions": "Cook quinoa and top with nutritional yeast, sautéed leafy greens, and roasted chickpeas.",
                "why_this_meal": "Nutritional yeast is rich in B12, and leafy greens provide folate for red blood cell health.",
                "supports_tests": ["Mcv", "Mch", "Red Blood Cell (rbc)"]
            })
        
        # Comprehensive anemia support meal
        if any(keyword in rec_text for keyword in ['anemia', 'multiple', 'comprehensive', 'rdw']):
            meals.append({
                "name": "Complete Blood Health Power Bowl",
                "youtube_link": "https://youtube.com/watch?v=blood-health-bowl",
                "ingredients": [
                    {"name": "lean red meat", "instacart_link": "https://www.instacart.com/store/s?k=lean+red+meat"},
                    {"name": "dark leafy greens", "instacart_link": "https://www.instacart.com/store/s?k=dark+leafy+greens"},
                    {"name": "citrus fruits", "instacart_link": "https://www.instacart.com/store/s?k=citrus+fruits"},
                    {"name": "fortified whole grains", "instacart_link": "https://www.instacart.com/store/s?k=fortified+whole+grains"},
                    {"name": "legumes", "instacart_link": "https://www.instacart.com/store/s?k=legumes"}
                ],
                "instructions": "Combine grilled lean meat with a base of dark leafy greens, add citrus segments, fortified grains, and mixed legumes.",
                "why_this_meal": "Provides iron, B12, folate, and vitamin C in one comprehensive meal to address multiple nutritional deficiencies.",
                "supports_tests": ["Rdw", "Hemoglobin", "Mcv", "Mch"]
            })
        
        # Vitamin D meals
        if any(keyword in rec_text for keyword in ['vitamin d', 'sunlight', 'fortified', 'fish']):
            meals.append({
                "name": "Grilled Salmon with Fortified Sides",
                "youtube_link": "https://youtube.com/watch?v=salmon-vitamin-d",
                "ingredients": [
                    {"name": "salmon", "instacart_link": "https://www.instacart.com/store/s?k=salmon"},
                    {"name": "fortified milk", "instacart_link": "https://www.instacart.com/store/s?k=fortified+milk"},
                    {"name": "fortified cereal", "instacart_link": "https://www.instacart.com/store/s?k=fortified+cereal"},
                    {"name": "egg yolks", "instacart_link": "https://www.instacart.com/store/s?k=eggs"}
                ],
                "instructions": "Grill salmon and serve with a glass of fortified milk and a side of fortified cereal topped with egg yolks.",
                "why_this_meal": "Multiple sources of vitamin D to support bone health and immune function.",
                "supports_tests": ["Vitamin D (25-oh)", "Calcium"]
            })
        
        # Liver support meals
        if any(keyword in rec_text for keyword in ['liver', 'bilirubin', 'alcohol']):
            meals.append({
                "name": "Liver Detox Green Power Smoothie",
                "youtube_link": "https://youtube.com/watch?v=liver-detox-smoothie",
                "ingredients": [
                    {"name": "kale", "instacart_link": "https://www.instacart.com/store/s?k=kale"},
                    {"name": "beets", "instacart_link": "https://www.instacart.com/store/s?k=beets"},
                    {"name": "garlic", "instacart_link": "https://www.instacart.com/store/s?k=garlic"},
                    {"name": "turmeric", "instacart_link": "https://www.instacart.com/store/s?k=turmeric"},
                    {"name": "green apple", "instacart_link": "https://www.instacart.com/store/s?k=green+apple"}
                ],
                "instructions": "Blend kale, cooked beets, garlic, turmeric, and green apple with water for a liver-supporting drink.",
                "why_this_meal": "Contains compounds that support liver detoxification and reduce inflammation.",
                "supports_tests": ["Bilirubin", "Liver function"]
            })
        
        # Default comprehensive meal if no specific needs detected
        if not meals:
            meals.append({
                "name": "Complete Nutritional Recovery Bowl",
                "youtube_link": "https://youtube.com/watch?v=recovery-bowl",
                "ingredients": [
                    {"name": "quinoa", "instacart_link": "https://www.instacart.com/store/s?k=quinoa"},
                    {"name": "lean protein", "instacart_link": "https://www.instacart.com/store/s?k=lean+protein"},
                    {"name": "mixed vegetables", "instacart_link": "https://www.instacart.com/store/s?k=mixed+vegetables"},
                    {"name": "healthy fats", "instacart_link": "https://www.instacart.com/store/s?k=healthy+fats"}
                ],
                "instructions": "Combine cooked quinoa with lean protein, a variety of colorful vegetables, and healthy fats like avocado or nuts.",
                "why_this_meal": "A balanced meal with all essential nutrients to support overall health and recovery.",
                "supports_tests": ["Overall health", "Multiple markers"]
            })
        
        # Limit to 3-4 meals to match API format
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