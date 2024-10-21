import functools
from typing import Optional, Tuple
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOLD_STANDARD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'gold_standard_evals')

@functools.lru_cache(maxsize=None)
def get_gold_standard_files() -> Optional[Tuple[str, str]]:
    try:
        
        transcript_file = 'gold_standard_transcript.txt'
        summary_file = 'gold_standard_summary.txt'
        
        transcript_path = os.path.join(GOLD_STANDARD_DIR, transcript_file)
        summary_path = os.path.join(GOLD_STANDARD_DIR, summary_file)
        
        if not os.path.exists(transcript_path) or not os.path.exists(summary_path):
            logger.error(f"🚨 Gold standard files not found at {transcript_path} or {summary_path}")
            return None
        
        with open(transcript_path, 'r') as f:
            transcript = f.read()
        
        with open(summary_path, 'r') as f:
            summary_section = f.read()
            
        
        return transcript, summary_section
    except Exception as e:
        logger.error(f"🚨 Error loading gold standard data: {str(e)}")
        return None
def build_evaluation_prompt(original_article: str, summary_to_evaluate: str, is_llm_conversation=False) -> str:
    if is_llm_conversation:
        return f"""
        # Guardrails Agent Prompt for Evaluating Summaries Of my Conversations With LLMs
        Evaluate the following summary of a conevrsatio I had with an LLM:

        Original Conversation:
        {original_article}

        Summary of conversation to evaluate:
        {summary_to_evaluate}

        Instructions:
        1. Carefully read both the original conversation and the provided summary.
        2. Evaluate the summary based on how well it captures the key information from the conversation.
        3. Use the criteria below to assess the quality and effectiveness of the summary.

        Criteria:
        1. Format: Does the summary consist of one key point as a headline/title, followed by 3-5 supporting sub-bullets, and is it suitable for a flashcard (not exceeding 2000 characters in total)?
        2. Focus: Does it identify and prioritize the most significant or groundbreaking aspects of the conversation?
        3. Depth: Do the sub-bullets effectively support and expand on the main point?
        4. Balance: Does it strike a good balance between technical and non-technical information?
        5. Clarity: Is it written in clear, accessible language for a general audience with some tech background?
        6. Technical Accuracy: Are key technical terms included when essential, without overuse of jargon?
        7. Completeness: Does the summary provide a clear understanding of the most crucial aspect of the conversation?
        8. Blog Inclusion: Is this ready to be included in a weekly blog post? Will a reader be hungry for more after reading this knowledge snack?

        Provide your evaluation in the following format from which you shall never deviate - do not add any additional formatting or decorations:
        Score: [A single number between 0 and 1, where 1 is the best]
        Feedback: [Your detailed feedback here, including strengths and areas for improvement]
        """
            
    else: 
        gold_standard_transcript, gold_standard_summary = get_gold_standard_files()

        return f"""
        # Guardrails Agent Prompt for Evaluating AI Tech Summaries
        Evaluate the following summary of an article about emerging AI technology:

        Original article:
        {original_article}

        Summary to evaluate:
        {summary_to_evaluate}

        Gold standard transcript:
        {gold_standard_transcript}

        Gold standard summary:
        {gold_standard_summary}

        Instructions:
        1. Carefully read both the original article and the provided summary.
        2. Evaluate the summary based on how well it captures the key information from the original article about emerging AI technology.
        3. Use the criteria below to assess the quality and effectiveness of the summary.
        4. The gold standard summary provided above is an example of a high-quality summary based on the gold standard transcript.
        5. Use this as a reference for what a good summary should cover and how it should be structured.
        6. **Do not replicate the gold standard summary verbatim.** Instead, focus on understanding the quality, completeness, and clarity it demonstrates.
        7. Evaluate the provided summary to evaluate based on how well it captures the key information from the actual transcript, comparing this effectiveness to how the gold standard summary captures information from its transcript.


        Criteria:
        1. Format: Does the summary consist of one key point as a headline/title, followed by 3-5 supporting sub-bullets, and is it suitable for a flashcard (not exceeding 2000 characters in total)?
        2. Focus: Does it identify and prioritize the most significant or groundbreaking aspect of the technology discussed?
        3. Depth: Do the sub-bullets effectively support and expand on the main point?
        4. Balance: Does it strike a good balance between technical and non-technical information?
        5. Clarity: Is it written in clear, accessible language for a general audience with some tech background?
        6. Technical Accuracy: Are key technical terms included when essential, without overuse of jargon?
        7. Completeness: Does the summary provide a clear understanding of the most crucial aspect of the emerging AI technology discussed?
        8. Credit: Does the summary list who did what when listing a thing that was done or an accomplishment? Does it give credit where credit is due?
        9. Blog Inclusion: Is this ready to be included in a weekly blog post. Will a reader be hungry for more after reading this knowledge snack?

        Provide your evaluation in the following format - do not add any additional formatting or decorations:
        Score: [A single number between 0 and 1, where 1 is the best]
        Feedback: [Your detailed feedback here, including strengths and areas for improvement]
        """