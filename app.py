from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import requests, json
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

def load_dict_from_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

secrets_file = "../secrets.json"
SECRETS = load_dict_from_json(secrets_file)

# ========== CONFIGURATION ==========
ENDPOINT = SECRETS["AZURE_DOC_ENDPOINT"]
KEY = SECRETS["AZURE_DOC_KEY"]
AZURE_OPENAI_URL = SECRETS["GPT_ENDPOINT"]
AZURE_OPENAI_KEY = SECRETS["GPT_API"]

document_analysis_client = DocumentAnalysisClient(ENDPOINT, credential=AzureKeyCredential(KEY))

def extract_text_from_pdf(uploaded_file):
    poller = document_analysis_client.begin_analyze_document("prebuilt-read", document=uploaded_file)
    result = poller.result()
    extracted_text = "\n".join([line.content for page in result.pages for line in page.lines])
    return extracted_text

with open("document.pdf", "rb") as f:
    company_info_text = extract_text_from_pdf(f)

@app.route('/')
def index():
    # Optionally, clear conversation history when loading the page
    session.pop('chat_history', None)
    return render_template('index.html')

def call_llm_api(conversation_history):
    url = AZURE_OPENAI_URL
    headers = {  
        "Content-Type": "application/json",  
        "api-key": AZURE_OPENAI_KEY  
    }  

    # Define your system prompt with the company info context.
    system_message = f"""
    You are Nekko BhAI (`Buddy for Helpful AI`) Nekko's AI Company Chatbot. Below is the company information and product details:
    {company_info_text}
    Nekko is an Industry Leader in AI ML Solutions.
    
    Your job is to do the following: 
    1. Always present the latest and exciting product offerings by Nekko. 
    2. Be empathetic and address the customer's pain points.
    3. If the query is unrelated, respond normally.
    4. If a user asks for the sales team contact, provide 'prithvi@nekko.tech'.
    5. Ask the user for their contact details such as Name, Mobile Number, Email over a few messages (Name and Mobile Number is Mandatory if they would prefer a call back)
    """
    
    # Build the complete messages list with the system prompt and conversation history.
    messages = [{"role": "system", "content": system_message}] + conversation_history

    payload = {  
        "messages": messages,  
        "temperature": 0.7,  
        "max_tokens": 512   
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()  
    return response.json()["choices"][0]["message"]["content"]

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_query = data.get("user_query")
    
    if not user_query:
        return jsonify({"error": "No user query provided"}), 400

    # Retrieve chat history from session or initialize as empty list
    chat_history = session.get('chat_history', [])
    
    # Append current user message to chat history
    chat_history.append({"role": "user", "content": user_query})
    
    # Send only the last 5 messages to preserve context and avoid exceeding token limits
    trimmed_history = chat_history[-10:]
    
    try:
        reply = call_llm_api(trimmed_history)
        # Append the assistant's reply to the history
        chat_history.append({"role": "assistant", "content": reply})
        # Update session with the new chat history
        session['chat_history'] = chat_history
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
