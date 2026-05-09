
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from groq import Groq
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os
from PyPDF2 import PdfReader

frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
app = Flask(__name__, static_folder=frontend_build_path, static_url_path="")
CORS(app)

# ======================
# Configure Groq API Key
# ======================

groq_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=groq_api_key) if groq_api_key else None

# ======================
# Load Telecom Documents
# ======================

documents = []

docs_path = "telecom_docs"

for file in os.listdir(docs_path):
    file_path = os.path.join(docs_path, file)
    
    if file.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            documents.append(f.read())
    
    elif file.endswith(".pdf"):
        try:
            with open(file_path, "rb") as f:
                pdf_reader = PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                if text.strip():
                    documents.append(text)
        except Exception as e:
            print(f"Error reading {file}: {e}")

# Handle empty documents
if not documents:
    documents = ["No documents available. Default response."]

# ======================
# Embeddings
# ======================

model = SentenceTransformer("all-MiniLM-L6-v2")

embeddings = model.encode(documents, convert_to_numpy=True)

# Ensure embeddings is 2D
if embeddings.ndim == 1:
    embeddings = embeddings.reshape(1, -1)

dimension = embeddings.shape[1]

# Normalize embeddings so inner product approximates cosine similarity
embeddings = embeddings / np.clip(np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-12, None)

index = faiss.IndexFlatIP(dimension)

index.add(np.array(embeddings).astype('float32'))

TOP_K = 3
MIN_SIMILARITY = 0.25
OUT_OF_SCOPE_MESSAGE = "Out of scope."

# ======================
# Ask Endpoint
# ======================

@app.route('/ask', methods=['POST'])
def ask():
    if client is None:
        return jsonify({"answer": "Server is missing GROQ_API_KEY."}), 500

    data = request.json
    question = data['question']

    query_embedding = model.encode([question], convert_to_numpy=True)
    query_embedding = query_embedding / np.clip(
        np.linalg.norm(query_embedding, axis=1, keepdims=True), 1e-12, None
    )

    D, I = index.search(np.array(query_embedding).astype('float32'), k=min(TOP_K, len(documents)))

    if len(D) == 0 or len(D[0]) == 0 or D[0][0] < MIN_SIMILARITY:
        return jsonify({
            "answer": OUT_OF_SCOPE_MESSAGE
        })

    context = ""

    for idx in I[0]:
        if idx < len(documents):
            # Truncate each document to 1000 chars to avoid token limit
            context += documents[idx][:1000] + "\n"

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert telecom RAN assistant. "
                    "Only answer questions that are strictly about telecom RAN and supported by the provided context. "
                    "If the question is out of scope or not covered by the context, reply with: "
                    f"{OUT_OF_SCOPE_MESSAGE}"
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
    )

    answer = completion.choices[0].message.content

    return jsonify({
        "answer": answer
    })

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
