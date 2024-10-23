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
def build_evaluation_prompt(original_transcript: str, summary_to_evaluate: str, is_llm_conversation=False) -> str:
    if is_llm_conversation:
        return f"""
        # Guardrails Agent Prompt for Evaluating Summaries Of my Conversations With LLMs
        Evaluate the following summary of a conevrsatio I had with an LLM:

        Original Conversation:
        {original_transcript}

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
        # gold_standard_transcript, gold_standard_summary = get_gold_standard_files()

        return f"""
        Guardrails Agent Prompt for Evaluating AI Tech Summaries

        Task:  
        Evaluate the following summary of a transcript about emerging AI technology.

        Inputs:
        - Original Transcript:

        {original_transcript}

        - Summary to Evaluate:

        {summary_to_evaluate}

        Instructions:

        1. Understand the Content:
        - Carefully read the entire Original Transcript to fully grasp the key information, topics, and context related to emerging AI technology.

        2. Evaluate the Summary:
        - Assess how well the Summary to Evaluate aligns with the Summarization Agent's instructions based on the criteria outlined below.
        - Do not use any external references or gold standard summaries for comparison. Base your evaluation solely on the Original Transcript and the Summary to Evaluate.

        3. Scoring Criteria:

        Evaluate the summary based on the following nine criteria. For each criterion, determine whether the summary meets the standard (Yes) or does not (No). Provide specific comments to justify your assessment.

        1. Format Adherence:
            - Criteria: 
                - The summary uses an H1 heading for the Title. 
                - The summary uses H2 headings for each category (Tools, Technologies, Concepts, People, Events).
                - The summary uses H3 subheadings for each instance within a category.
                - Bullet points contain concise, rich, and active summaries.
            - Assessment: Does the summary strictly follow the specified formatting? Is there only 1 Tools section, 1 Technologies section, 1 Concepts section, 1 People section, and 1 Events section. 
            - Comment:

        2. Correct Categorization:
            - Criteria: 
                - Each instance is correctly categorized as a Tool, Technology, Concept, Person, or Event based on the definitions provided.
            - Assessment: Are all instances accurately categorized?
            - Comment:

        3. Active Voice & Rich Detail:
            - Criteria: 
                - Summaries are written in active voice.
                - Each bullet point includes specific details, reasons, or explanations that provide a deeper understanding of the instance.
            - Assessment: Are the summaries in active voice and sufficiently detailed?
            - Comment:

        4. Prioritization:
            - Criteria: 
                - Newer or emerging topics are prioritized over established ones.
                - Within each category, the most critical or novel instances are listed first.
            - Assessment: Does the summary prioritize novel and critical instances appropriately?
            - Comment:

        5. Conciseness:
            - Criteria: 
                - Summaries are concise, focusing on essential information without unnecessary verbosity.
            - Assessment: Are the summaries concise and to the point?
            - Comment:

        6. Accuracy:
            - Criteria: 
                - No information is included that is not present in the transcript.
                - Summaries accurately reflect the content of the transcript without embellishment.
            - Assessment: Is the summary free from inaccuracies and extraneous information?
            - Comment:

        7. Completeness:
            - Criteria: 
                - All relevant instances within each category present in the transcript are included in the summary.
                - No critical information from the transcript is omitted.
            - Assessment: Does the summary cover all necessary instances without omitting key information?
            - Comment:

        8. Clarity:
            - Criteria: 
                - The summary is written in clear, precise language suitable for an expert audience.
                - Technical terms are used appropriately without overuse of jargon.
            - Assessment: Is the summary clear and easy to understand for the intended audience?
            - Comment:

        9. Educational Value:
            - Criteria: 
                - The summary provides new insights or knowledge that would be valuable to intermediate to expert AI engineers.
                - It encourages further learning or exploration.
            - Assessment: Does the summary add educational value and promote further learning?
            - Comment:

        4. Scoring Framework:

        - Score Calculation:
            - Each criterion is worth up to 1 point.
            - Total Possible Score: 9 points.
            - Final Score: Sum of points awarded divided by 9, resulting in a score between 0 and 1.

        - An Example Of How To Score:
            - If a summary meets 7 out of the 9 criteria, the score would be 7/9 ≈ 0.78.

        5. Provide Your Evaluation in the Following Format:

        Score: [A single number between 0 and 1, rounded to two decimal places]
        Feedback: [Your detailed feedback here, including strengths and areas for improvement]


        Example Evaluation:


        Score: 0.89
        Feedback: The summary adheres to the specified format with correct use of H1 and H2 headings. All instances are accurately categorized, and the summaries are written in active voice with rich details. Prioritization of emerging technologies like Quantum Computing is well-executed. The content is concise and free from inaccuracies, covering all critical information from the transcript. However, the section on People could provide more specific contributions to enhance educational value. Overall, the summary is clear, accurate, and highly informative.

        -------------

        Usage Example

        Original Transcript:
        In the recent AI Summit 2024, Satya Nadella announced the integration of Quantum Computing with Microsoft's Azure platform. This advancement aims to enhance cloud-based AI services by leveraging quantum algorithms for faster data processing. Additionally, the introduction of Pinecone.db as a new vector database promises to optimize AI model performance through efficient similarity searches. Fei-Fei Li presented her latest research on federated learning, emphasizing its role in improving data privacy across decentralized devices. The summit also highlighted breakthroughs in natural language processing showcased at CES 2024.

        Summary to Evaluate:
        # AI Summit 2024: Quantum Computing Integration, Pinecone.db Launch, and Federated Learning Breakthroughs
        ## Tools
        ### Pinecone.db
            - Pinecone.db is introduced as a new vector database that optimizes AI model performance by enabling efficient similarity searches and real-time data indexing.

        ## Technologies
        ### Quantum Computing
            - Quantum computing has the potential to revolutionize cryptography and data processing by leveraging quantum bits to perform complex calculations exponentially faster than classical computers.

        ## Concepts
        ### Federated Learning
            - Federated Learning is explained as a method to train AI models across decentralized devices, enhancing data privacy and reducing the need for centralized data storage.

        ## People
        ### Fei-Fei Li
            - Fei-Fei Li's recent research contributions to computer vision include advancements in image recognition algorithms that improve accuracy and efficiency.

        ## Events
        ### CES 2024
            - CES 2024 showcased key AI innovations, including breakthroughs in natural language processing and autonomous vehicle technologies.

        Evaluation Output:
 
        Score: 0.89
        Feedback: The summary adheres to the specified format with correct use of H1 and H2 headings. All instances are accurately categorized, and the summaries are written in active voice with rich details. Prioritization of emerging technologies like Quantum Computing is well-executed. The content is concise and free from inaccuracies, covering all critical information from the transcript. However, the section on People could provide more specific contributions to enhance educational value. Additionally, the Events section could include more detailed descriptions of the breakthroughs presented at CES 2024. Overall, the summary is clear, accurate, and highly informative.

        ---------------------
        Important Instructions:

        - Adherence to Summarization Instructions: Ensure that the evaluation strictly follows the criteria based on the summarization agent's instructions without introducing external standards or references.
        
        - Constructive Feedback: Provide balanced feedback that highlights both strengths and areas for improvement, offering clear guidance on how the summary can be enhanced.
        
        - Objectivity: Maintain an objective stance, focusing on factual accuracy, completeness, clarity, and adherence to formatting and prioritization guidelines.
        
        - Consistency: Apply the scoring criteria uniformly across all evaluations to maintain consistency in assessments.
        
        - No External Comparisons: Do not reference or compare the summary to any external documents, standards, or previous summaries.
        """