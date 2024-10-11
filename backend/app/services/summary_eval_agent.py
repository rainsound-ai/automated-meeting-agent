# summary_eval_agent.py
from openai import OpenAI
from app.lib.Env import open_ai_api_key
from fastapi import HTTPException
from typing import Dict, List
import json

client = OpenAI(api_key=open_ai_api_key)

def safe_json_loads(content: str) -> Dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract JSON-like content
        import re
        json_like = re.search(r'\{.*\}', content, re.DOTALL)
        if json_like:
            return json.loads(json_like.group())
        else:
            raise ValueError("Could not extract JSON from response")

def evaluate_section(transcription: str, section_summary: str, section_name: str) -> Dict[str, any]:
    try:
        # Generate expected outcome for the specific section
        expected_outcome = generate_expected_outcome(transcription, section_name)
        
        # Evaluate the section
        if section_name.lower() == "intro":
            evaluation = evaluate_intro(section_summary, expected_outcome)
        elif section_name.lower() == "direct quotes":
            evaluation = evaluate_quotes(transcription, section_summary, expected_outcome)
        elif section_name.lower() == "next steps":
            evaluation = evaluate_actions(transcription, section_summary, expected_outcome)
        else:
            raise ValueError(f"Unknown section name: {section_name}")
        
        return evaluation
    except Exception as e:
        print(f"Evaluation failed with error: {e}")
        raise HTTPException(status_code=500, detail="Error while evaluating summary section.")


def generate_expected_outcome(transcription: str, section_name: str) -> str:
    prompt = f"""
    Based on the following transcript, generate an expected {section_name} section for a meeting summary.

    Transcript:
    {{transcription}}

    Provide your response as a string representing the expected {section_name} section.
    """
    
    response = client.chat.completions.create(
        model="o1-mini",
        messages=[
            # {"role": "system", "content": f"You are an AI assistant that analyzes meeting transcripts and generates expected {section_name} sections for summaries."},
            {"role": "user", "content": prompt.format(transcription=transcription)}
        ]
    )
    
    return response.choices[0].message.content

def evaluate_intro(actual: str, expected: str) -> Dict[str, any]:
    prompt = f"""
    Evaluate the following intro section of a meeting summary:

    Actual intro:
    {actual}

    Expected intro:
    {expected}

    Criteria:
    1. Conciseness: Is it 3 sentences or fewer?
    2. Completeness: Does it cover the meeting's purpose, main topics, and any relevant context?
    3. Clarity: Is it written in a clear and professional manner?
    4. Accuracy: Does it stick to facts from the transcript without inferring or making assumptions?

    Provide your evaluation in the following JSON format:
    {{
        "score": <score between 0 and 1>,
        "feedback": "Detailed feedback here",
        "conciseness": "Comment on length and adherence to 3-sentence limit",
        "completeness": "Comment on coverage of key points",
        "clarity": "Comment on writing style and professionalism",
        "accuracy": "Comment on factual accuracy and avoidance of assumptions"
    }}
    """
    
    response = client.chat.completions.create(
        model="o1-mini",
        messages=[
            # {"role": "system", "content": "You are an AI assistant that evaluates meeting summaries."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return safe_json_loads(response.choices[0].message.content)

def evaluate_quotes(transcription: str, actual_quotes: str, expected_quotes: str) -> Dict[str, any]:
    prompt = f"""
    Evaluate the following quotes extracted from a meeting summary:

    Actual quotes:
    {actual_quotes}

    Expected quotes:
    {expected_quotes}

    Original Transcript:
    {transcription}

    Criteria:
    1. Relevance: Do the quotes shed light on the main issues or challenges discussed?
    2. Impact: Are the quotes significant in the context of the discussion?
    3. Clarity: Are the quotes clear, concise, and effectively conveying the speaker's intent?
    4. Accuracy: Are the quotes verbatim from the transcript?
    5. Formatting: Are the quotes presented without speaker attribution and within quotation marks?

    Provide your evaluation in the following JSON format:
    {{
        "score": <score between 0 and 1>,
        "feedback": "Detailed feedback here",
        "relevance": "Comment on how well the quotes represent key discussion points",
        "impact": "Comment on the significance of the selected quotes",
        "clarity": "Comment on the clarity and conciseness of the quotes",
        "accuracy": "Comment on whether the quotes are verbatim from the transcript",
        "formatting": "Comment on adherence to formatting guidelines"
    }}
    """
    
    response = client.chat.completions.create(
        model="o1-mini",
        messages=[
            # {"role": "system", "content": "You are an AI assistant that evaluates meeting quote extractions."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return safe_json_loads(response.choices[0].message.content)

def evaluate_actions(transcription: str, actual_actions: str, expected_actions: str) -> Dict[str, any]:
    prompt = f"""
    Evaluate the following next actions extracted from a meeting summary:

    Actual next actions:
    {actual_actions}

    Expected next actions:
    {expected_actions}

    Original Transcript:
    {transcription}

    Criteria:
    1. Clarity: Are the actions clearly defined and achievable?
    2. Relevance: Do the actions directly relate to the discussion in the transcript?
    3. Impact: Are these high-impact actions that will affect project outcomes or business goals?
    4. Completeness: Are all important actions captured (up to 3)?
    5. Formatting: Are the actions presented with a title and description?

    Provide your evaluation in the following JSON format:
    {{
        "score": <score between 0 and 1>,
        "feedback": "Detailed feedback here",
        "clarity": "Comment on how clearly defined and achievable the actions are",
        "relevance": "Comment on how well the actions relate to the discussion",
        "impact": "Comment on the potential impact of the actions",
        "completeness": "Comment on whether all important actions are captured",
        "formatting": "Comment on adherence to formatting guidelines"
    }}
    """
    
    response = client.chat.completions.create(
        model="o1-mini",
        messages=[
            # {"role": "system", "content": "You are an AI assistant that evaluates meeting action item extractions."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return safe_json_loads(response.choices[0].message.content)