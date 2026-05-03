import numpy as np
import faiss
from groq import Groq

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are CodeSage AI, a code analysis assistant for a specific GitHub repository.
Answer questions strictly based on the provided code snippets.
- Reference exact file paths when explaining.
- Use markdown and code blocks.
- If the snippets don't have enough info, say so honestly.
"""


def classify_intent(query: str, groq_client: Groq) -> str:
    """
    Returns 'greeting', 'repo', or 'offtopic'.
    """
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify the user message into exactly one of these categories:\n"
                        "- greeting: casual chat, greetings, small talk, thanks\n"
                        "- repo: questions about a SPECIFIC codebase — asking about how code works, where something is implemented, how to add a feature, explaining architecture, debugging code in a project\n"
                        "- offtopic: general knowledge questions (what is python, what is jwt, who is someone, explain a concept in general), celebrities, sports, anything not about a specific codebase\n"
                        "Key rule: 'what is X' or 'explain X' for general concepts = offtopic. Only questions about THIS project's code = repo.\n"
                        "Reply with only one word: greeting, repo, or offtopic."
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=5,
        )
        intent = response.choices[0].message.content.strip().lower()
        if intent not in {"greeting", "repo", "offtopic"}:
            return "repo"
        return intent
    except Exception:
        return "repo"


def search(query, index, chunks, model, top_k=6):
    query_vec = model.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(query_vec)
    scores, indices = index.search(query_vec, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        chunk = dict(chunks[idx])
        chunk["score"] = float(score)
        results.append(chunk)
    return results


def generate_answer(query: str, results: list, groq_client: Groq) -> str:
    intent = classify_intent(query, groq_client)

    if intent == "greeting":
        return "Hey! Ask me anything about the indexed repository — features, code, architecture, or how to implement something."

    if intent == "offtopic":
        return "I can only answer questions about the indexed repository. Try asking about the code, features, or architecture."

    if not results:
        return "No relevant code found in the repository for your query."

    top_results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]
    context = "\n\n".join(
        f"### File: `{c['path']}` | Line ~{c['start_line']}\n```\n{c['content']}\n```"
        for c in top_results
    )

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Relevant code:\n\n{context}\n\nQuestion: {query}"},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[!] Groq error: {e}"
