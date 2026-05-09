import os
import json
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from groq import Groq
from sentence_transformers import SentenceTransformer
import faiss

# ─── Config ───────────────────────────────────────────────────────────────────
# Read the API key from the environment variable set in Render dashboard.
# Never hardcode secrets in source code.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable is not set!")

# Paths
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR    = os.path.join(BASE_DIR, "telecom_docs")
BUILD_DIR   = os.path.join(BASE_DIR, "..", "frontend", "build")

# ─── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=BUILD_DIR, static_url_path="")

# ─── Load Telecom Knowledge Base ──────────────────────────────────────────────
def load_docs(docs_dir):
    """Load all .txt files from the telecom_docs folder."""
    chunks = []
    if os.path.isdir(docs_dir):
        for filename in os.listdir(docs_dir):
            if filename.endswith(".txt"):
                filepath = os.path.join(docs_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
                    # Split into ~500-char chunks with overlap
                    for i in range(0, len(text), 400):
                        chunk = text[i:i + 500].strip()
                        if chunk:
                            chunks.append(chunk)
    return chunks

print("Loading documents...")
DOCS = load_docs(DOCS_DIR)

print("Loading embedding model...")
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

print("Building FAISS index...")
if DOCS:
    embeddings = EMBED_MODEL.encode(DOCS, show_progress_bar=False).astype("float32")
    INDEX = faiss.IndexFlatL2(embeddings.shape[1])
    INDEX.add(embeddings)
else:
    INDEX = None

groq_client = Groq(api_key=GROQ_API_KEY)

# ─── RAG Helper ───────────────────────────────────────────────────────────────
def retrieve_context(query, top_k=3):
    """Return the top-k most relevant document chunks for the query."""
    if INDEX is None or not DOCS:
        return ""
    q_emb = EMBED_MODEL.encode([query]).astype("float32")
    _, indices = INDEX.search(q_emb, top_k)
    context_chunks = [DOCS[i] for i in indices[0] if i < len(DOCS)]
    return "\n\n".join(context_chunks)

# ─── API Routes ───────────────────────────────────────────────────────────────
@app.route("/api/ask", methods=["POST"])
def ask():
    data    = request.get_json(force=True)
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "No question provided"}), 400

    context = retrieve_context(question)

    system_prompt = (
        "You are RANAssist, an expert AI assistant specialized in Telecom RAN "
        "(Radio Access Networks), 4G LTE, 5G NR, network slicing, beamforming, "
        "and related telecom topics. Answer clearly and concisely based on the "
        "context provided. If the context does not contain the answer, use your "
        "general telecom knowledge.\n\n"
        f"Context:\n{context}"
    )

    response = groq_client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question},
        ],
        max_tokens=512,
        temperature=0.3,
    )

    answer = response.choices[0].message.content
    return jsonify({"answer": answer})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "docs_loaded": len(DOCS)})

# ─── Serve React Frontend ─────────────────────────────────────────────────────
# This is REQUIRED for single-container deployment on Render.
# Flask serves the built React app for every non-API route.

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    full_path = os.path.join(BUILD_DIR, path)
    if path and os.path.exists(full_path):
        return send_from_directory(BUILD_DIR, path)
    # For any unknown route, return index.html so React Router works
    return send_from_directory(BUILD_DIR, "index.html")

# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
