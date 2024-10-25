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
        ```markdown
        BEGINNING OF PROMPT TO EVAL AGENT FOR NEW SUMMARY AGENT

        # Evaluation Agent Prompt for ChatGPT Conversation Summaries

        **Task:**  
        Evaluate the following summary of a ChatGPT conversation, ensuring it accurately and effectively summarizes the interaction based on the specified categories relevant to Rainsound.ai.

        **Inputs:**
        - **Original Conversation Transcript:**

        BEGINNING OF ORIGINAL CONVERSATION WITH LLM 
        ```
        {original_transcript}
        ```
        END OF ORIGINAL CONVERSATION WITH LLM 

        - **Summary to Evaluate:**

        ```
        {summary_to_evaluate}
        ```

        **Instructions:**

        1. **Understand the Content:**
        - Carefully read the entire Original Conversation Transcript to fully grasp the key information, topics, and context related to Rainsound.ai's focus areas: Information Seeking, Learning and Education, Coding Assistance, Content Creation, Brainstorming Ideas, and Task Automation.

        2. **Evaluate the Summary:**
        - Assess how well the Summary to Evaluate aligns with the Summarization Agent's instructions based on the criteria outlined below.
        - Do not use any external references or gold standard summaries for comparison. Base your evaluation solely on the Original Conversation Transcript and the Summary to Evaluate.

        3. **Scoring Criteria:**

        Evaluate the summary based on the following nine criteria. For each criterion, determine whether the summary meets the standard (Yes) or does not (No). Provide specific comments to justify your assessment.

        1. **Format Adherence:**
            - **Criteria:** 
                - The summary uses **H1** headings for each relevant category (Information Seeking, Learning and Education, Coding Assistance, Content Creation, Brainstorming Ideas, Task Automation).
                - The summary uses **H2** headings for each identified instance within a category.
                - Bullet points contain concise, rich, and active summaries.
            - **Assessment:** Does the summary strictly follow the specified Markdown formatting? Are the correct headings (H1 for categories, H2 for instances) used appropriately?
            - **Comment:**

        2. **Correct Categorization:**
            - **Criteria:** 
                - Each instance is correctly categorized into one of the six categories: Information Seeking, Learning and Education, Coding Assistance, Content Creation, Brainstorming Ideas, or Task Automation.
            - **Assessment:** Are all instances accurately categorized based on the definitions provided in the summarization agent's prompt?
            - **Comment:**

        3. **Active Voice & Rich Detail:**
            - **Criteria:** 
                - Summaries are written in active voice.
                - Each bullet point includes specific details, reasons, or explanations that provide a deeper understanding of the instance.
            - **Assessment:** Are the summaries in active voice and sufficiently detailed to convey the essence of the conversation?
            - **Comment:**

        4. **Prioritization:**
            - **Criteria:** 
                - Relevant categories and instances are prioritized based on their relevance to Rainsound.ai’s needs.
                - More critical or frequent interactions are highlighted appropriately within each category.
            - **Assessment:** Does the summary prioritize the most relevant and important instances effectively?
            - **Comment:**

        5. **Conciseness:**
            - **Criteria:** 
                - Summaries are concise, focusing on essential information without unnecessary verbosity.
            - **Assessment:** Are the summaries clear and to the point, avoiding extraneous information?
            - **Comment:**

        6. **Accuracy:**
            - **Criteria:** 
                - No information is included that is not present in the conversation.
                - Summaries accurately reflect the content of the conversation without embellishment.
            - **Assessment:** Is the summary free from inaccuracies and extraneous information?
            - **Comment:**

        7. **Completeness:**
            - **Criteria:** 
                - All relevant instances within each category present in the conversation are included in the summary.
                - No critical information from the conversation is omitted.
            - **Assessment:** Does the summary cover all necessary instances without omitting key information?
            - **Comment:**

        8. **Clarity:**
            - **Criteria:** 
                - The summary is written in clear, precise language suitable for an expert audience.
                - Technical terms are used appropriately without overuse of jargon.
            - **Assessment:** Is the summary clear and easy to understand for the intended audience?
            - **Comment:**

        9. **Educational Value:**
            - **Criteria:** 
                - The summary provides insights or knowledge that would be valuable to professionals in the AI and technology industry.
                - It highlights new developments or important aspects relevant to Rainsound.ai.
            - **Assessment:** Does the summary add educational value and promote further understanding or learning?
            - **Comment:**

        4. **Scoring Framework:**

        - **Score Calculation:**
            - Each criterion is worth up to 1 point.
            - **Total Possible Score:** 9 points.
            - **Final Score:** Sum of points awarded divided by 9, resulting in a score between 0 and 1.

        - **Example Of How To Score:**
            - If a summary meets 7 out of the 9 criteria, the score would be 7/9 ≈ 0.78.

        5. **Provide Your Evaluation in the Following Format:**

        ```
        Score: [A single number between 0 and 1, rounded to two decimal places]
        Feedback: [Your detailed feedback here, including strengths and areas for improvement]
        ```

        **Example Evaluation:**

        ```
        Score: 0.89
        Feedback: The summary adheres to the specified format with correct use of H1 and H2 headings. All instances are accurately categorized, and the summaries are written in active voice with rich details. Prioritization of relevant categories like Learning and Education is well-executed. The content is concise and free from inaccuracies, covering all critical information from the conversation. However, the Content Creation section could include more specific examples to enhance educational value. Additionally, the Task Automation section is slightly underdeveloped. Overall, the summary is clear, accurate, and highly informative.
        ```

        ---------------------

        **Usage Example**

        **Original Conversation Transcript:**
        ```
        User: Can you help me understand the basics of federated learning?
        ChatGPT: Certainly! Federated learning is a machine learning approach where multiple devices collaboratively train a model without sharing their raw data. This enhances data privacy and reduces the need for centralized data storage. It's particularly useful in scenarios where data is distributed across various locations, such as mobile devices or edge servers.
        User: How can we implement federated learning in our AI models?
        ChatGPT: To implement federated learning, you can start by selecting a suitable framework like TensorFlow Federated or PySyft. Next, design your model to allow training on decentralized data sources. Ensure secure communication protocols are in place to protect data during transmission. Finally, aggregate the trained models centrally to update the global model without ever accessing the raw data.
        ```

        **Summary to Evaluate:**
        ```
        # Learning and Education
        ## Fundamentals of Federated Learning
            - Explained federated learning as a machine learning approach enabling multiple devices to collaboratively train a model without sharing raw data, enhancing privacy and reducing centralized storage needs.

        # Coding Assistance
        ## Implementing Federated Learning
            - Provided steps to implement federated learning, including selecting frameworks like TensorFlow Federated or PySyft, designing decentralized models, ensuring secure communication, and aggregating trained models centrally.
        ```

        **Evaluation Output:**

        ```
        Score: 0.89
        Feedback: The summary adheres to the specified format with correct use of H1 and H2 headings. All instances are accurately categorized under Learning and Education and Coding Assistance. The summaries are written in active voice with rich details, effectively conveying the essence of federated learning and its implementation steps. The content is concise and free from inaccuracies, covering all critical information from the conversation. However, the summary could benefit from additional categories if applicable, and the prioritization of key points within each category could be more evident. Overall, the summary is clear, accurate, and highly informative.
        ```

        ---------------------

        **Important Instructions:**

        - **Adherence to Summarization Instructions:** Ensure that the evaluation strictly follows the criteria based on the summarization agent's instructions without introducing external standards or references.

        - **Constructive Feedback:** Provide balanced feedback that highlights both strengths and areas for improvement, offering clear guidance on how the summary can be enhanced.

        - **Objectivity:** Maintain an objective stance, focusing on factual accuracy, completeness, clarity, and adherence to formatting and prioritization guidelines.

        - **Consistency:** Apply the scoring criteria uniformly across all evaluations to maintain consistency in assessments.

        - **No External Comparisons:** Do not reference or compare the summary to any external documents, standards, or previous summaries.
        ```
        """
            
    elif is_jumpshare_link:
        return f"""

        # Guardrails Agent Prompt for Evaluating Meeting Summaries

        **Task:**  
        Evaluate the following summary of a meeting transcript by assessing its adherence to the extraction and formatting guidelines based on the **Top 5 Elements**.

        **Inputs:**
        - **Original Transcript:**

        ```
        {original_transcript}
        ```

        - **Summary to Evaluate:**

        ```
        {summary_to_evaluate}
        ```

        **Instructions:**

        ### 1. Understand the Content:
        - **Thorough Review:**
        - Carefully read the entire **Original Transcript** to fully grasp the key information, topics, and context related to the meeting.
        
        ### 2. Evaluate the Summary:
        - **Alignment with Instructions:**
        - Assess how well the **Summary to Evaluate** aligns with the **Summary Agent's** instructions based on the criteria outlined below.
        - Do not use any external references or gold standard summaries for comparison. Base your evaluation solely on the **Original Transcript** and the **Summary to Evaluate**.

        ### 3. Scoring Criteria:

        Evaluate the summary based on the following **seven** criteria. For each criterion, determine whether the summary meets the standard (**Yes**) or does not (**No**). Provide specific comments to justify your assessment.

        1. **Format Adherence:**
            - **Criteria:** 
                - The summary uses an H1 heading for the Title.
                - The summary uses H2 headings for each category (**Action Items**, **Decisions Made**, **Key Topics and Themes**, **Issues and Problems Identified**, **Questions Raised**).
                - The summary uses H3 subheadings for each instance within a category.
                - Bullet points contain concise summaries supported by direct, verbatim quotes from the transcript.
            - **Assessment:** Does the summary strictly follow the specified formatting? Is there only one section per category without duplication?
            - **Comment:**

        2. **Correct Categorization:**
            - **Criteria:** 
                - Each instance is correctly categorized as **Action Items**, **Decisions Made**, **Key Topics and Themes**, **Issues and Problems Identified**, or **Questions Raised** based on the definitions provided.
            - **Assessment:** Are all instances accurately categorized?
            - **Comment:**

        3. **Active Voice & Direct Quotes:**
            - **Criteria:** 
                - Summaries are written in active voice.
                - Each bullet point includes an exact, verbatim quote from the transcript supporting the extracted information.
            - **Assessment:** Are the summaries in active voice and supported by direct quotes without paraphrasing?
            - **Comment:**

        4. **Conciseness:**
            - **Criteria:** 
                - Summaries are concise, focusing solely on essential information without unnecessary verbosity.
            - **Assessment:** Are the summaries brief and to the point?
            - **Comment:**

        5. **Accuracy:**
            - **Criteria:** 
                - No information is included that is not present in the transcript.
                - Summaries accurately reflect the content of the transcript without embellishment or interpretation.
            - **Assessment:** Is the summary free from inaccuracies and extraneous information?
            - **Comment:**

        6. **Completeness:**
            - **Criteria:** 
                - All relevant instances within each category present in the transcript are included in the summary.
                - No critical information from the transcript is omitted.
            - **Assessment:** Does the summary cover all necessary instances without omitting key information?
            - **Comment:**

        7. **Clarity:**
            - **Criteria:** 
                - The summary is written in clear, precise language.
                - Technical terms are used appropriately without overuse of jargon.
            - **Assessment:** Is the summary clear and easy to understand?
            - **Comment:**

        ### 4. Scoring Framework:

        - **Score Calculation:**
            - Each criterion is worth up to **1 point**.
            - **Total Possible Score:** 7 points.
            - **Final Score:** Sum of points awarded divided by 7, resulting in a score between 0 and 1.

        - **An Example Of How To Score:**
            - If a summary meets 5 out of the 7 criteria, the score would be **5/7 ≈ 0.71**.

        ### 5. Provide Your Evaluation in the Following Format:

        ```
        Score: [A single number between 0 and 1, rounded to two decimal places]
        Feedback: [Your detailed feedback here, including strengths and areas for improvement]
        ```

        ---

        ### **EXAMPLE EVALUATION:**

        **EXAMPLE of an original Transcript:**
        ```
        Let's start with the financial report. Can you update us on the quarterly figures?
        Sure, we've seen a 10% increase in revenue compared to last quarter.
        That's great news. Based on these numbers, I decide to approve the increase in the marketing budget by 15%.
        With the increased budget, we can launch the new campaign next month.
        Speaking of campaigns, when is the new website expected to be live?
        We're targeting December 15, 2024, for the website launch.
        Excellent. Any issues with the current supply chain that we should address?
        Yes, there have been delays due to unforeseen weather conditions affecting our suppliers.
        Let's find alternative suppliers to mitigate these delays. Please handle this by next week.
        ```

        **EXAMPLE of a Summary to Evaluate:**
        # Project Kickoff Meeting Summary

        ## Action Items
        ### Prepare the Quarterly Financial Report
            - "The quarterly financial report will be prepared by the finance team to provide updated revenue and expense figures by October 31, 2024."
        
        ### Handle Supply Chain Delays
            - "Alternative suppliers will be identified to mitigate supply chain delays by next week."

        ## Decisions Made
        ### Approve the Increase in Marketing Budget
            - "A 15% increase in the marketing budget is approved based on a 10% quarterly revenue growth."

        ## Key Topics and Themes
        ### Financial Performance
            - "Discussed a 10% increase in quarterly revenue and its impact on budget allocations."
        
        ### Marketing Strategy
            - "Planned the launch of a new marketing campaign utilizing the increased budget."
        
        ### Supply Chain Management
            - "Addressed delays in product delivery caused by unforeseen weather conditions and the need for alternative suppliers."

        ## Issues and Problems Identified
        ### Supply Chain Delays
            - "Unforeseen weather conditions have disrupted suppliers, causing delays in product delivery and potentially impacting client satisfaction."

        ## Questions Raised
        ### Website Launch Timeline
            - "Inquired about the launch date for the new website, with a target set for December 15, 2024."


        **EXAMPLE Evaluation Output:**

        ```
        Score: 0.86
        Feedback: The summary adheres to the specified format with correct use of H1, H2, and H3 headings. All instances are accurately categorized under the appropriate sections. Each summary point is written in active voice and is supported by direct, verbatim quotes from the transcript, ensuring accuracy. The content is concise and focuses solely on essential information without unnecessary verbosity. However, the summary slightly lacks completeness as it could include additional details from the transcript regarding the impact of the marketing campaign launch. Additionally, while clarity is generally maintained, some bullet points could be more precise to enhance readability. Overall, the summary is clear, accurate, and mostly complete.
        ```

        ---

        ### **Important Instructions:**

        - **Accuracy:**
        - **Do not include any information not present in the transcript.**
        - **Use only direct, verbatim quotes from the transcript to support each extracted item.**
        - **Avoid paraphrasing or interpreting the content in any way.**

        - **Format Adherence:**
        - **Strictly follow the specified formatting with H1, H2, H3, and bullet points.**
        - **Do not repeat sections; there should only ever be one section per category.**

        - **Active Voice & Direct Quotes:**
        - **Use active voice in all summaries and ensure each summary is directly supported by a verbatim quote from the transcript.**

        - **Conciseness:**
        - **Keep summaries concise to ensure they are easily digestible and fit within any system limitations.**

        - **Completeness:**
        - **Ensure all relevant instances from the transcript are included without omitting key information.**

        - **Clarity:**
        - **Ensure the summary is written in clear, precise language suitable for an expert audience.**
        - **Use technical terms appropriately without overusing jargon.**

        ---

        ### **Usage Example:**

        **EXAMPLE Original Transcript:**
        ```
        Let's start with the financial report. Can you update us on the quarterly figures?
        Sure, we've seen a 10% increase in revenue compared to last quarter.
        That's great news. Based on these numbers, I decide to approve the increase in the marketing budget by 15%.
        With the increased budget, we can launch the new campaign next month.
        Speaking of campaigns, when is the new website expected to be live?
        We're targeting December 15, 2024, for the website launch.
        Excellent. Any issues with the current supply chain that we should address?
        Yes, there have been delays due to unforeseen weather conditions affecting our suppliers.
        Let's find alternative suppliers to mitigate these delays. Please handle this by next week.
        ```

        **EXAMPLE Summary to Evaluate:**
        ```markdown
        # Project Kickoff Meeting Summary

        ## Action Items
        ### Prepare the Quarterly Financial Report
            - "The quarterly financial report will be prepared by the finance team to provide updated revenue and expense figures by October 31, 2024."
        
        ### Handle Supply Chain Delays
            - "Alternative suppliers will be identified to mitigate supply chain delays by next week."

        ## Decisions Made
        ### Approve the Increase in Marketing Budget
            - "A 15% increase in the marketing budget is approved based on a 10% quarterly revenue growth."

        ## Key Topics and Themes
        ### Financial Performance
            - "Discussed a 10% increase in quarterly revenue and its impact on budget allocations."
        
        ### Marketing Strategy
            - "Planned the launch of a new marketing campaign utilizing the increased budget."
        
        ### Supply Chain Management
            - "Addressed delays in product delivery caused by unforeseen weather conditions and the need for alternative suppliers."

        ## Issues and Problems Identified
        ### Supply Chain Delays
            - "Unforeseen weather conditions have disrupted suppliers, causing delays in product delivery and potentially impacting client satisfaction."

        ## Questions Raised
        ### Website Launch Timeline
            - "Inquired about the launch date for the new website, with a target set for December 15, 2024."
        ```

        **EXAMPLE Processed Output:**
        ```
        Score: 0.86
        Feedback: The summary adheres to the specified format with correct use of H1, H2, and H3 headings. All instances are accurately categorized under the appropriate sections. Each summary point is written in active voice and is supported by direct, verbatim quotes from the transcript, ensuring accuracy. The content is concise and focuses solely on essential information without unnecessary verbosity. However, the summary slightly lacks completeness as it could include additional details from the transcript regarding the impact of the marketing campaign launch. Additionally, while clarity is generally maintained, some bullet points could be more precise to enhance readability. Overall, the summary is clear, accurate, and mostly complete.
        ```
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