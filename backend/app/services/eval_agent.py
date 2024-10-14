import os
import random
from typing import Optional, Dict, Tuple
from openai import OpenAI
from app.lib.Env import open_ai_api_key
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=open_ai_api_key)

GOLD_STANDARD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'gold_standard_evals')

def load_section_specific_gold_standard_data(section_name: str) -> Optional[Tuple[str, str]]:
    try:
        folders = [f for f in os.listdir(GOLD_STANDARD_DIR) if os.path.isdir(os.path.join(GOLD_STANDARD_DIR, f))]
        if not folders:
            logger.warning("No gold standard folders found.")
            return None
        
        random_folder = random.choice(folders)
        folder_path = os.path.join(GOLD_STANDARD_DIR, random_folder)
        
        transcript_file = next((f for f in os.listdir(folder_path) if f.startswith('gold_standard_transcript')), None)
        summary_file = next((f for f in os.listdir(folder_path) if f.startswith('gold_standard_summary')), None)
        
        if not transcript_file or not summary_file:
            logger.warning(f"Missing gold standard files in {random_folder}.")
            return None
        
        with open(os.path.join(folder_path, transcript_file), 'r') as f:
            transcript = f.read()
        
        with open(os.path.join(folder_path, summary_file), 'r') as f:
            full_summary = f.read()
            
        # Extract the relevant section from the full summary
        section_pattern = rf"## {section_name}\n(.*?)(?=\n## |\Z)"
        section_match = re.search(section_pattern, full_summary, re.DOTALL | re.IGNORECASE)
        section_summary = section_match.group(1).strip() if section_match else ""
        
        return transcript, section_summary
    except Exception as e:
        logger.error(f"Error loading gold standard data: {str(e)}")
        return None

def evaluate_section(transcription: str, section_summary: str, section_name: str) -> Dict[str, any]:
    try:
        gold_standard_data = load_section_specific_gold_standard_data(section_name)
        gold_standard_transcript, gold_standard_summary = gold_standard_data or (None, None)

        prompt = f"""
        Evaluate the following {section_name} section of a meeting summary:

        Actual transcript (excerpt):
        {transcription}...  # Limit transcript length to avoid token limits

        {section_name} summary to evaluate:
        {section_summary}

        Gold standard transcript (excerpt):
        {gold_standard_transcript}...

        Gold standard {section_name} summary:
        {gold_standard_summary}

        Instructions:
        1. The gold standard summary provided above is an example of a high-quality {section_name} section based on the gold standard transcript.
        2. Use this as a reference for what a good {section_name} section should cover and how it should be structured.
        3. Evaluate the provided {section_name} summary based on how well it captures the key information from the actual transcript, compared to how the gold standard summary captures information from its transcript.

        Criteria:
        1. Conciseness: Is the summary concise while covering key points?
        2. Completeness: Does it cover the main topics and relevant context for this section?
        3. Clarity: Is it written in a clear and professional manner?
        4. Accuracy: Does it stick to facts from the transcript without inferring or making assumptions?
        5. Structure: Does it follow a logical structure appropriate for a {section_name} section?

        Provide your evaluation in the following format:
        Score: [A single number between 0 and 1, where 1 is the best]
        Feedback: [Your detailed feedback here, including strengths and areas for improvement]
        """
        
        response = get_openai_response(prompt)
        evaluation = parse_evaluation_response(response)
        
        logger.info(f"Evaluation for {section_name}: {evaluation}")
        return {"section_score": evaluation["score"], "feedback": evaluation["feedback"]}
    except Exception as e:
        logger.error(f"Evaluation failed with error: {str(e)}")
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
        logger.info(f"OpenAI API response: {content}")
        return content
    except Exception as e:
        logger.error(f"Error getting OpenAI response: {str(e)}")
        return ""

def parse_evaluation_response(response: str) -> Dict[str, any]:
    try:
        score_match = re.search(r'Score:\s*(0\.\d+|1\.0|1)', response)
        feedback_match = re.search(r'Feedback:\s*(.+)', response, re.DOTALL)

        score = float(score_match.group(1)) if score_match else 0.5
        feedback = feedback_match.group(1).strip() if feedback_match else "No feedback provided."

        return {"score": score, "feedback": feedback}
    except Exception as e:
        logger.error(f"Error parsing evaluation response: {str(e)}")
        raise

def calculate_f1_score(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0
    return 2 * (precision * recall) / (precision + recall)
