import os
from typing import Optional, Dict, Tuple
from openai import OpenAI
from app.lib.Env import open_ai_api_key
import logging
import re
import functools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=open_ai_api_key)

GOLD_STANDARD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'gold_standard_evals')

@functools.lru_cache(maxsize=None)
def get_gold_standard_file(section_name: str) -> Optional[Tuple[str, str]]:
    try:
        fotmatted_section_name = section_name.lower().replace(' ', '_')
        transcript_file = 'gold_standard_transcript.txt'
        summary_file = f'gold_standard_{fotmatted_section_name}.txt'
        
        transcript_path = os.path.join(GOLD_STANDARD_DIR, transcript_file)
        summary_path = os.path.join(GOLD_STANDARD_DIR, summary_file)
        
        if not os.path.exists(transcript_path) or not os.path.exists(summary_path):
            logger.warning(f"🚨 Missing gold standard files for {section_name}.")
            return None
        
        with open(transcript_path, 'r') as f:
            transcript = f.read()
        
        with open(summary_path, 'r') as f:
            summary_section = f.read()
            
        
        return transcript, summary_section
    except Exception as e:
        logger.error(f"🚨 Error loading gold standard data for {section_name}: {str(e)}")
        return None


def evaluate_section(transcript: str, section_summary: str, section_name: str) -> Dict[str, any]:
    try:
        gold_standard_data = get_gold_standard_file(section_name)
        gold_standard_transcript, gold_standard_summary = gold_standard_data or (None, None)

        prompt = f"""
        Evaluate the following {section_name} section of a meeting summary:

        Actual transcript:
        {transcript}

        {section_name} summary to evaluate:
        {section_summary}

        Gold standard transcript:
        {gold_standard_transcript}

        Gold standard {section_name} summary:
        {gold_standard_summary}

        Instructions:
        1. The gold standard summary provided above is an example of a high-quality {section_name} section based on the gold standard transcript.
        2. Use this as a reference for what a good {section_name} section should cover and how it should be structured.
        3. **Do not replicate the gold standard summary verbatim.** Instead, focus on understanding the quality, completeness, and clarity it demonstrates.
        4. Evaluate the provided {section_name} summary based on how well it captures the key information from the actual transcript, comparing this effectiveness to how the gold standard summary captures information from its transcript.

        Criteria:
        1. Conciseness: Is the summary concise while covering key points?
        2. Completeness: Does it cover the main topics and relevant context for this section?
        3. Clarity: Is it written in a clear and professional manner?
        4. Accuracy: Does it stick to facts from the transcript without inferring or making assumptions?
        5. Structure: Does it follow a logical structure appropriate for a {section_name} section?

        Provide your evaluation in the following format - do not add any additional formatting or decorations:
        Score: [A single number between 0 and 1, where 1 is the best]
        Feedback: [Your detailed feedback here, including strengths and areas for improvement]
        """
        
        response = get_openai_response(prompt)
        evaluation = parse_evaluation_response(response)
        
        logger.info(f"💡 Evaluation for {section_name}: {evaluation}")
        return evaluation
    except Exception as e:
        logger.error(f"🚨 Evaluation failed with error: {str(e)}")
        raise

def get_openai_response(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="o1-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content
        logger.info(f"💡 OpenAI API response: {content}")
        return content
    except Exception as e:
        logger.error(f"🚨 Error getting OpenAI response: {str(e)}")
        return ""

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