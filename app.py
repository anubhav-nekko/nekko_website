from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests, json
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from PyPDF2 import PdfReader

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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

# Function to extract text from PDF using Azure Document Intelligence
def extract_text_from_pdf(uploaded_file):
    poller = document_analysis_client.begin_analyze_document(
        "prebuilt-read", document=uploaded_file
    )
    result = poller.result()
    extracted_text = "\n".join([line.content for page in result.pages for line in page.lines])
    return extracted_text

# Load document once at startup
with open("document.pdf", "rb") as f:
    company_info_text = extract_text_from_pdf(f)

# Route to serve the index.html page.
@app.route('/')
def index():
    return render_template('index.html')  # Place index.html in the "templates" folder

# Your function to call the LLM API
def call_llm_api(system_message, user_query):
    url = AZURE_OPENAI_URL
    headers = {  
        "Content-Type": "application/json",  
        "api-key": AZURE_OPENAI_KEY  
    }  

    # Modify system message to include extracted document info
    system_message = f"""
    You are Nekko's AI assistant. Below is the company information and product details:
    {company_info_text}
    
    Your Job is to Always present the Users with the Latest and Exciting Product Offerings by Nekko. Your Response should be short but attention grabbing.
    Always try to be empathetic and try to understand the customer's pain Point.
    Use this information to answer user queries. If the query is unrelated to the company or its products, respond normally.
    If a user requests the company's sales team contact details, provide them with the email 'prithvi@nekko.tech'.
    """

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_query}
    ]
    payload = {  
        "messages": messages,  
        "temperature": 0.7,  
        "max_tokens": 512   
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()  
    return response.json()["choices"][0]["message"]["content"]

# Create an endpoint for the chatbot
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_query = data.get("user_query")
    
    if not user_query:
        return jsonify({"error": "No user query provided"}), 400

    try:
        reply = call_llm_api("You are a company assistant.", user_query)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Listen on all interfaces so external requests can reach your API.
    #app.run(debug=True, host='0.0.0.0')
    app.run(debug=True)