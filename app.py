import os
import json
import datetime
from datetime import timedelta
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests

# -------------------------------
# Flask Setup
# -------------------------------
app = Flask(__name__)
app.secret_key = os.urandom(24) # "42c49afbd77de45bb67d01c4278a9b24"  # not strictly used now
CORS(app, supports_credentials=True)

# -------------------------------
# Configuration / Secrets
# -------------------------------
def load_dict_from_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

secrets_file = "../secrets.json"
SECRETS = load_dict_from_json(secrets_file)

ENDPOINT = SECRETS["AZURE_DOC_ENDPOINT"]
KEY = SECRETS["AZURE_DOC_KEY"]
AZURE_OPENAI_URL = SECRETS["GPT_ENDPOINT"]
AZURE_OPENAI_KEY = SECRETS["GPT_API"]

# -------------------------------
# (Optional) Document Analysis
# -------------------------------
from azure.ai.formrecognizer import DocumentAnalysisClient 
from azure.core.credentials import AzureKeyCredential

document_analysis_client = DocumentAnalysisClient(ENDPOINT, credential=AzureKeyCredential(KEY))

def extract_text_from_pdf(uploaded_file):
    poller = document_analysis_client.begin_analyze_document(
        "prebuilt-read", 
        document=uploaded_file
    )
    result = poller.result()
    extracted_text = "\n".join(
        [line.content for page in result.pages for line in page.lines]
    )
    return extracted_text

with open("document.pdf", "rb") as f:
    company_info_text = extract_text_from_pdf(f)

# -------------------------------
# LLM Call Function
# -------------------------------
def call_llm_api(conversation_history):
    """Call your Azure OpenAI model with the conversation history."""
    url = AZURE_OPENAI_URL
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }
    # Build the system message with your PDF content
    system_message = f"""
    You are Nekko Website Chatbot. Below is the company information and product details:
    {company_info_text}
    Nekko is an Industry Leader in AI ML Solutions.

    Your job is to:
    0. Collect Customer Details Such as Name and Mobile Number Mandatorily and if possible other information such as Email, Organisation Name as well.
    1. Present the latest and exciting product offerings by Nekko.
    2. Be empathetic and address the customer's pain points.
    3. Respond normally if the query is unrelated.
    4. Provide 'prithvi@nekko.tech' if the user asks for the sales team contact.
    5. Engage in a normal conversation.

    Since this is for a chatbot, Please avoid using markdown formatting. Keep your answers short and suitable for a chat environment.
    """
    messages = [{"role": "system", "content": system_message}] + conversation_history
    payload = {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 512
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# -------------------------------
# Conversations Folder
# -------------------------------
CONVERSATIONS_FOLDER = "conversations"
if not os.path.exists(CONVERSATIONS_FOLDER):
    os.makedirs(CONVERSATIONS_FOLDER)

# ---------------------------------------------------------
# Helper: Find newest JSON file in last 1 minute
# ---------------------------------------------------------
def latest_file_in_last_minute(folder, cutoff):
    """
    Return the path of the single newest .json file if it’s
    within the last minute; else None.
    """
    newest_path = None
    newest_ctime = None
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            file_path = os.path.join(folder, filename)
            ctime = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
            # If file was created after cutoff, consider it
            if ctime >= cutoff:
                # Keep track of whichever is newest
                if newest_ctime is None or ctime > newest_ctime:
                    newest_ctime = ctime
                    newest_path = file_path
    return newest_path

# -------------------------------
# Routes
# -------------------------------
@app.route('/')
def index():
    # Just render index.html
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_query = data.get("user_query", "").strip()
    if not user_query:
        return jsonify({"error": "No user query provided"}), 400

    now = datetime.datetime.now()
    one_minute_ago = now - datetime.timedelta(seconds=60)

    # 1) Find the single newest conversation file in the last minute
    latest_path = latest_file_in_last_minute(CONVERSATIONS_FOLDER, one_minute_ago)
    if latest_path is not None:
        # Load existing conversation
        with open(latest_path, "r", encoding="utf-8") as f:
            combined_history = json.load(f)
    else:
        # No recent file => start a blank conversation
        combined_history = []

    # 2) Add the user's new message
    combined_history.append({"role": "user", "content": user_query})

    # 3) Call your LLM
    try:
        reply = call_llm_api(combined_history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # 4) Append the bot's response
    combined_history.append({"role": "assistant", "content": reply})

    # 5) Overwrite the same file if it exists, or create a brand-new file
    if not latest_path:
        latest_path = os.path.join(
            CONVERSATIONS_FOLDER,
            f"chat_{now.strftime('%Y%m%d_%H%M%S')}.json"
        )

    print("Conversation file will be saved at:", os.path.abspath(latest_path))
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(combined_history, f, indent=4)

    return jsonify({"reply": reply})

# -------------------------------
# Main
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)
