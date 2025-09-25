# Configuration for LLM usage
# Set USE_LOCAL_MODEL = True to use pretrained model, False for API calls

USE_LOCAL_MODEL = True  # Change to True to use local pretrained model

# Local model settings
LOCAL_MODEL_CONFIG = {
    "max_length": 256,
    "model_path": None,  # Uses default path if None
    "enable_caching": True
}

# API model settings (existing)
API_MODEL_CONFIG = {
    "model_name": "gpt-3.5-turbo",  # or whatever API model you use
    "max_tokens": 256,
    "temperature": 0.7
}