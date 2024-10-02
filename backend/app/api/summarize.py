from app.lib.Env import open_ai_api_key
from fastapi import APIRouter,  HTTPException
import os
import warnings
from openai import OpenAI
from app.lib.JsonSchemas import TranscriptionRequest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

client = OpenAI(api_key=open_ai_api_key)

# Ignore torch warning 
warnings.filterwarnings("ignore", category=FutureWarning)

api_router = APIRouter()

# Define the input model for transcription
@api_router.post("/summarize")

async def summarize_transcription(request: TranscriptionRequest):
    try:
        print("Received request for summarization.")
        transcription = request.transcription.strip()

        # If transcription is empty, load from transcription.txt
        if not transcription:
            print("No transcription provided. Attempting to read from transcription.txt.")
            transcription_file_path = os.path.join(BASE_DIR, 'transcription.txt')

            if os.path.exists(transcription_file_path):
                print(f"transcription.txt found at {transcription_file_path}.")
                with open(transcription_file_path, 'r') as file:
                    transcription = file.read()
                    print("Successfully read transcription from transcription.txt.")
            else:
                print("transcription.txt is missing. Cannot proceed.")
                raise HTTPException(status_code=500, detail="No transcription provided and transcription.txt is missing.")

        sample_summary_file_path = os.path.join(BASE_DIR, 'sample_summary.txt')
        
        if os.path.exists(sample_summary_file_path):
            print(f"sample_summary.txt found at {sample_summary_file_path}.")
            with open(sample_summary_file_path, 'r') as file:
                sample_summary = file.read()
            
        
        # Send the combined summary for final summarization
        print("Sending combined summary to GPT-4 for final summarization.")
        # final_prompt = f"""
        # You will be provided with a transcript of a meeting.

        # This meeting took place at Rainsound.ai, a company that builds AI Agents for clients such as Nvidia, Salesforce, and Microsoft.
        
        # Alex is the Data Lead, Aubrey is the IT Lead, Miles is Business Lead, Luca is AI Lead, and Ian is Product Lead, but they didn't necessarily all attend this meeting.

        # There are stategy meetings, business operation meetings, customer-facing sales meetings, and delivery work sessions - thie meeting is probably related to one of those.

        # When meetings begin with introductions, skip that part for the purpose of your summary.
        
        # Organize the the response into a one sentence intro and then 1-5 sections containing bullet points for key insights, and then an analysis at the end. 
        # Each bullet point should be 1-2 sentences long. 
        # The title of each section should be intuitive. 
        
        # If any next actions were discussed please include those in the final analysis. 
        
        # Throughout the entire response clearly mark who said what when relevant. 
        # Sometimes the meetings include external people like customers or partners - do your best to capture what they said and when as well.
        # If you can't figure out the names of the speakers from the transcription, don't worry about it. Avoid using Speaker 1 or Speaker A. 

        # Propose potential next actions in a section at the very end called "Potential Next Actions".

        # Use this sample summary as a guide - it represents the kind of summarization fidelity and strucutre we expect from you.  
        # Sample Summary: {sample_summary}

        # Here's the transcription you need to summarize:
        # Transcription: {transcription}
        # """
        final_prompt = f"""
    You will be provided with a transcript of a meeting.

    This meeting took place at Rainsound.ai, a company that builds AI Agents for clients such as Nvidia, Salesforce, and Microsoft.
    
    Alex is the Data Lead, Aubrey is the IT Lead, Miles is the Business Lead, Luca is the AI Lead, and Ian is the Product Lead, but they didn't necessarily all attend this meeting.

    There are strategy meetings, business operation meetings, customer-facing sales meetings, and delivery work sessions — this meeting is probably related to one of those.

    When meetings begin with introductions, skip that part for the purpose of your summary.

    ### Key Areas to Focus On:
    1. **Sales and Business Strategy**: Identify key points about the sales strategy, including any discussions on conferences, sales roles, and outreach efforts. Include direct quotes when significant ideas or opinions are expressed.
    2. **Technical and AI-Related Insights**: Capture any technical discussions, especially those led by Luca (AI Lead). Highlight specific concerns related to AI technology (e.g., AI hallucination, legal issues, privacy risks). Include direct quotes where technical challenges or solutions were discussed.
    3. **Key Quotes**: Make sure to capture any critical quotes from participants that represent important insights or decisions. These can include quotes on strategy, technical challenges, or specific opinions. Be selective and only include the most important statements.
    4. **Speaker-Specific Insights**: Attribute key points and quotes to specific speakers when possible. Focus on technical insights or concerns brought up by Luca (AI Lead) and others regarding AI risks, challenges, or sales strategies.

    ### Summary Structure:
    - Start with a one-sentence introduction summarizing the purpose of the meeting.
    - Create 1-5 sections, each containing bullet points of key insights.
    - **Include direct quotes** where participants expressed important insights, concerns, or decisions. Attribute these quotes to the speaker.
    - Ensure one section is dedicated to **Technical and AI Insights**, especially focusing on AI risks (hallucination, legal, privacy).
    - Include an analysis section summarizing challenges and opportunities discussed.
    - If next actions were discussed, include them under a **Potential Next Actions** section at the end.

    Propose potential next actions in a section at the very end called **"Potential Next Actions"**.

    Throughout the entire response, clearly mark who said what when relevant. Sometimes the meetings include external people like customers or partners — do your best to capture what they said and when as well. If you can't figure out the names of the speakers from the transcription, don't worry about it. Avoid using "Speaker 1" or "Speaker A."

    Use this sample summary as a guide — it represents the kind of summarization fidelity and structure we expect from you.

    Sample Summary: {sample_summary}

    Here's the transcription you need to summarize:
    Transcription: {transcription}
    """


        try:
            final_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an assistant that provides structured meeting summaries."},
                    {"role": "user", "content": final_prompt}
                ]
            )
            final_summary = final_response.choices[0].message.content
            print("Successfully received final summary.")

        except Exception as e:
            print(f"GPT-4 API failed for final summarization with error: {e}")
            raise HTTPException(status_code=500, detail="Error while generating final summary.")

        return {"transcription": transcription, "summary": final_summary}

    except Exception as e:
        print(f"An error occurred during the summarization process: {e}")
        raise HTTPException(status_code=500, detail=str(e))