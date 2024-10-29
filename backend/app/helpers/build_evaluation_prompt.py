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

def build_evaluation_prompt(original_transcript: str, summary_to_evaluate: str, is_llm_conversation,  is_jumpshare_link) -> str:
    if is_llm_conversation:
        return f"""
        # Evaluation Agent Instructions

        ## Input Format
        You will receive two pieces of content to compare:

        1. Original Conversation:
        ```
        BEGINNING OF ORIGINAL CONVERSATION WITH LLM
        {original_transcript}
        END OF ORIGINAL CONVERSATION WITH LLM
        ```

        2. Summary to Evaluate:
        ```
        BEGINNING OF SUMMARY TO EVALUATE
        {summary_to_evaluate}
        END OF SUMMARY TO EVALUATE
        ```

        ## Critical Scoring Criteria

        ### 1. Role and Format Adherence (CRITICAL - 40% of score)
        Automatic failure criteria - if ANY of these occur, maximum possible score is 0.40:
        - Uses conversational language ("Let's...", "We should...", "I think...")
        - Includes introductions or conclusions
        - Offers help or invites questions
        - Uses first person pronouns (I, we, our)
        - Directly addresses the reader
        - Attempts to teach or explain rather than summarize
        - Generates new content not in original conversation

        ### 2. Standard Criteria (60% of score)
        Each worth 10% of total score:

        a. Category Accuracy
        - Uses only specified categories (Information Seeking, Learning and Education, etc.)
        - Correctly categorizes content within appropriate categories
        - Skips categories not present in conversation

        b. Format Compliance
        - Uses H1 (#) only for main categories
        - Uses H2 (##) for instances within categories
        - Uses single-level bullet points correctly

        c. Bullet Point Quality
        - Starts with action verbs in past tense
        - Presents specific, concrete information
        - Maintains conciseness (max 2 lines per point)

        d. Technical Accuracy
        - Accurately reflects technical content from conversation
        - Includes relevant technical details
        - No information fabrication

        e. Completeness
        - Captures all major points from conversation
        - No critical information omitted
        - Appropriate level of detail

        f. Organization
        - Logical grouping of related information
        - Clear instance headers
        - Proper information hierarchy

        ## CRITICAL OUTPUT REQUIREMENT
        You MUST ALWAYS provide output in this exact format, no exceptions:
        ```
        Score: [number between 0 and 1, rounded to 2 decimal places]
        Feedback: [Detailed feedback explaining the score]
        ```

        ### Score Rules
        - A score MUST ALWAYS be provided
        - Score MUST be between 0 and 1
        - Score MUST be rounded to 2 decimal places
        - No score can be skipped or omitted
        - No score can be null or undefined
        - No other format is acceptable

        ### If Unable to Calculate Score
        If you encounter any issues calculating the score:
        - Default to 0.10 for severe issues
        - Default to 0.40 for critical role failures
        - Default to 0.50 for unclear cases
        - NEVER skip providing a score

        ### Example Valid Outputs:
        ```
        Score: 0.35
        Feedback: [explanation...]
        ```
        ```
        Score: 0.90
        Feedback: [explanation...]
        ```
        ```
        Score: 0.50
        Feedback: Unable to fully evaluate due to [reason], defaulting to median score.
        ```

        ### Example Invalid Outputs (NEVER DO THESE):
        ```
        Feedback: [explanation without score]
        ```
        ```
        Score: Pending
        Feedback: [explanation...]
        ```
        ```
        Score: N/A
        Feedback: [explanation...]
        ```

        ## Scoring Calculation
        1. First check Role and Format Adherence:
        - If ANY critical failures found, maximum score = 0.40
        - If no critical failures, this section = 0.40 points

        2. Then evaluate Standard Criteria:
        - Each of 6 criteria worth 0.10 points
        - Can be partially awarded (0.00, 0.05, or 0.10)
        - Sum all points for total score

        ## Example Evaluations

        ### Example 1 - Critical Failure:
        ```
        Score: 0.35
        Feedback: The summary critically fails by attempting to engage in conversation, starting with "Let's explore" and ending with "Feel free to ask questions." Despite good technical content and organization, this conversational approach violates the core role of the Summary Agent. Additionally, the summary attempts to teach concepts rather than simply summarizing what was discussed. To improve: remove all conversational language, eliminate teaching elements, and maintain strict focus on summarizing the actual conversation content using the required format.
        ```

        ### Example 2 - Strong Summary:
        ```
        Score: 0.95
        Feedback: The summary excellently maintains its analytical role with no conversational elements. Categories are correctly used, all points start with action verbs, and technical details are accurately captured. Minor improvement needed in bullet point conciseness - some points exceed two lines. Consider condensing: "Analyzed system architecture requirements and performance constraints, identifying key scalability challenges" into "Analyzed system architecture requirements for scalability and performance."
        ```

        ## Important Reminders
        - Always evaluate based on the original conversation content
        - Provide specific examples in feedback
        - Focus first on critical role adherence
        - Be precise about formatting issues
        - Include both problems and strengths in feedback
        - Suggest concrete improvements
        - ALWAYS include a score between 0 and 1

        Your evaluation must always end with a Score and Feedback using the exact format shown above.
        """
            
    elif is_jumpshare_link:
        return f"""
        ---

        **Evaluation Agent Prompt**

        **Task:**

        Evaluate the following summary of a meeting transcript by assessing its adherence to the extraction, topic organization, and formatting guidelines based on the instructions provided to the **Summary Agent**.

        **Inputs:**

        - **Original Transcript:**

        BEGINNING OF ORIGINAL TRANSCRIPT
        ```
        {original_transcript}
        ```
        END OF ORIGINAL TRANSCRIPT

        - **Summary to Evaluate:**

        BEGINNING OF SUMMARY TO EVALUATE
        ```
        {summary_to_evaluate}
        ```
        END OF SUMMARY TO EVALUATE

        **Instructions:**

        ### 1. Understand the Content:

        - **Thorough Review:**
        - Carefully read the entire **Original Transcript** to fully grasp the key information, topics, and context related to the meeting.

        ### 2. Evaluate the Summary:

        - **Alignment with Instructions:**
        - Assess how well the **Summary to Evaluate** aligns with the **Summary Agent's** instructions.
        - Focus on topic identification, organization, and inclusion of crucial information.
        - Do not use any external references or gold standard summaries for comparison. Base your evaluation solely on the **Original Transcript** and the **Summary to Evaluate**.

        ### 3. Scoring Criteria:

        Evaluate the summary based on the following **eleven** criteria. For each criterion, determine whether the summary meets the standard (**Yes**) or does not (**No**). Provide specific comments to justify your assessment.

        1. **Inclusion of Meeting Purpose and Participants:**
        - **Criteria:**
            - The introductory paragraph includes the meeting's purpose.
            - The main participants and their roles are clearly stated.
        - **Assessment:** Does the summary include the meeting's purpose and key participants?
        - **Comment:**

        2. **Listing of Main Topics in Introductory Paragraph:**
        - **Criteria:**
            - All main topics discussed in the meeting are listed in the introductory paragraph.
        - **Assessment:** Are all main topics listed?
        - **Comment:**

        3. **Topic Identification and Organization:**
        - **Criteria:**
            - Topics are correctly identified and organized into separate sections with appropriate headings.
        - **Assessment:** Are the topics correctly identified and organized?
        - **Comment:**

        4. **Format Adherence:**
        - **Criteria:**
            - The summary follows the specified formatting, including:
            - An H1 tag for the title.
            - Introductory paragraph placed immediately after the title.
            - H2 headings for each topic name.
            - Under each topic, H3 headings for each category name.
            - Bullet points with concise summaries under each category.
            - There is only one section per category under each topic without duplication.
        - **Assessment:** Does the summary strictly follow the specified formatting?
        - **Comment:**

        5. **Correct Categorization within Topics:**
        - **Criteria:**
            - Each instance is correctly categorized under **Action Items**, **Decisions Made**, **Key Topics and Themes**, **Issues and Problems Identified**, or **Questions Raised** based on the definitions provided.
        - **Assessment:** Are all instances accurately categorized?
        - **Comment:**

        6. **Handling of Quotes:**
        - **Criteria:**
            - Quotes are cleaned up for readability by removing filler words, repetitions, and correcting grammar, punctuation, and capitalization.
            - The original intent and meaning of the quotes are preserved.
        - **Assessment:** Are the quotes properly cleaned up without altering their meaning?
        - **Comment:**

        7. **Determination and Prioritization of Key Information:**
        - **Criteria:**
            - The summarizer has effectively identified and prioritized the most important information based on the meeting's purpose and topics.
            - The summary focuses on what the intended audience would find most valuable.
        - **Assessment:** Has the summarizer effectively identified and prioritized key information?
        - **Comment:**

        8. **Conciseness:**
        - **Criteria:**
            - Summaries are concise, focusing solely on essential information without unnecessary verbosity.
        - **Assessment:** Is the summary brief and to the point?
        - **Comment:**

        9. **Accuracy:**
        - **Criteria:**
            - No information is included that is not present in the transcript.
            - Summaries accurately reflect the content of the transcript without embellishment or interpretation beyond cleaning up quotes.
        - **Assessment:** Is the summary free from inaccuracies and extraneous information?
        - **Comment:**

        10. **Completeness:**
            - **Criteria:**
            - All relevant instances within each category present in the transcript are included in the summary.
            - No critical information from the transcript is omitted.
            - **Assessment:** Does the summary cover all necessary instances without omitting key information?
            - **Comment:**

        11. **Clarity:**
            - **Criteria:**
            - The summary is written in clear, precise language.
            - Technical terms are used appropriately without overuse of jargon.
            - **Assessment:** Is the summary clear and easy to understand?
            - **Comment:**

        ### 4. Scoring Framework:

        - **Score Calculation:**
        - Each criterion is worth up to **1 point**.
        - **Total Possible Score:** 11 points.
        - **Final Score:** Sum of points awarded divided by 11, resulting in a score between 0 and 1, rounded to two decimal places.

        - **An Example of How to Score:**
        - If a summary meets 9 out of the 11 criteria, the score would be **9/11 ≈ 0.82**.

        ### 5. Provide Your Evaluation in the Following Format:

        ```
        Score: [A single number between 0 and 1, rounded to two decimal places]
        Feedback:
        1. **Inclusion of Meeting Purpose and Participants:** [Yes/No] - [Comment]
        2. **Listing of Main Topics in Introductory Paragraph:** [Yes/No] - [Comment]
        3. **Topic Identification and Organization:** [Yes/No] - [Comment]
        4. **Format Adherence:** [Yes/No] - [Comment]
        5. **Correct Categorization within Topics:** [Yes/No] - [Comment]
        6. **Handling of Quotes:** [Yes/No] - [Comment]
        7. **Determination and Prioritization of Key Information:** [Yes/No] - [Comment]
        8. **Conciseness:** [Yes/No] - [Comment]
        9. **Accuracy:** [Yes/No] - [Comment]
        10. **Completeness:** [Yes/No] - [Comment]
        11. **Clarity:** [Yes/No] - [Comment]
        ```

        ---

        **Important Instructions:**

        - **Accuracy:**
        - **Do not include any information not present in the transcript.**
        - **Avoid paraphrasing or interpreting the content beyond assessing the cleaned-up quotes.**

        - **Handling of Quotes:**
        - **Permitted Edits:**
            - Acknowledge that quotes may be cleaned up for readability as per the guidelines.
        - **Prohibited Changes:**
            - The meaning or intent of the quotes must not be altered.

        - **Format Adherence:**
        - **Strictly follow the specified formatting with appropriate headings and bullet points.**
        - **Ensure the introductory paragraph is included immediately after the title.**
        - **Do not repeat sections; there should only ever be one section per category under each topic.**

        - **Determination and Prioritization of Key Information:**
        - **Evaluate whether the summarizer has effectively identified and focused on the most important information based on the meeting's purpose and topics.**

        - **Conciseness:**
        - **Keep feedback concise to ensure it is easily digestible and fits within any system limitations.**

        - **Completeness:**
        - **Ensure all relevant instances from the transcript are considered in the evaluation without omitting key information.**

        - **Clarity:**
        - **Ensure your feedback is written in clear, precise language suitable for an expert audience.**
        - **Use technical terms appropriately without overusing jargon.**

        ---
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
                        - Note: It's possible there isn't one of each cateogry if a category was omitted because there was no relevant info for that category.
                    - The summary uses H3 subheadings for each instance within a category.
                    - Bullet points contain concise, rich, and active summaries.
                - Assessment: Does the summary strictly follow the specified formatting? Is there no more than 1 Tools section, no more than 1 Technologies section, no more than 1 Concepts section, no more than 1 People section, and no more than 1 Events section. 
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