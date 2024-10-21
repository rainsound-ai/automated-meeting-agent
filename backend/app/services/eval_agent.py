from typing import Dict
import logging
import re
from app.helpers.build_evaluation_prompt import build_evaluation_prompt
from app.services.get_openai_chat_response import get_openai_chat_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_evaluation_response(response: str) -> Dict[str, any]:
    try:
        # Extract score
        score_match = re.search(r'Score:\s*(0\.\d+|1\.0)', response)
        score = float(score_match.group(1)) if score_match else "Couldnt find score"

        # Extract feedback (everything after "Feedback:")
        feedback_pattern = f'{re.escape("Feedback:")}(.*)'
        feedback_match = re.search(feedback_pattern, response, re.DOTALL)
        feedback = feedback_match.group(1).strip() if feedback_match else "Couldnt find feedback"

        return {
            "score": score,
            "feedback": feedback
        }

    except Exception as e:
        return logger.error(f"🚨 Error parsing evaluation response: {str(e)}")
    
    

async def evaluate_section(original_article: str, summary_to_evaluate: str, is_llm_conversation=False) -> Dict[str, any]:
    try:
        # Build prompt (your existing code)
        prompt = build_evaluation_prompt(original_article, summary_to_evaluate, is_llm_conversation)
        
        # Get OpenAI response
        response = await get_openai_chat_response(prompt)
        
        # Parse response
        evaluation = parse_evaluation_response(response)
        if not evaluation:
            raise ValueError("Failed to parse evaluation response")
            
        return evaluation
        
    except Exception as e:
        logger.error(f"🚨 Evaluation failed with error: {str(e)}")
        raise  # Propagate the error up