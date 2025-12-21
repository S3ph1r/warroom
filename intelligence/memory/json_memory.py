"""
Zero-Dependency Vector Memory (JSON + Pure Python Math).
Implements semantic/spatial search without heavy libraries (numpy/chromadb).
Perfect for datasets < 10,000 items.
"""
import json
import os
import math
import logging
import requests
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("data", "warroom_memory.json")

class JsonVectorMemory:
    def __init__(self, embedding_model="mistral-nemo:latest"):
        self.embedding_model = embedding_model
        self.ollama_url = "http://localhost:11434"
        self.file_path = DB_PATH
        self.data = self._load_data()
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def _load_data(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading memory: {e}")
                return []
        return []

    def _save_data(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _get_embedding(self, text):
        """Get embedding from Ollama API"""
        try:
            url = f"{self.ollama_url}/api/embeddings"
            payload = {
                "model": self.embedding_model,
                "prompt": text
            }
            resp = requests.post(url, json=payload)
            if resp.status_code == 200:
                vector = resp.json().get('embedding')
                return vector
            else:
                print(f"❌ Ollama Error ({resp.status_code}): {resp.text}")
                return None
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return None

    def _cosine_similarity(self, vec_a, vec_b):
        """
        Pure Python Cosine Similarity.
        Formula: (A . B) / (||A|| * ||B||)
        """
        if not vec_a or not vec_b: return 0.0
        if len(vec_a) != len(vec_b): return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        return dot_product / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0

    def add_news(self, news_items):
        """
        Add news items to memory.
        Items must have: title, summary, link, published_at, source.
        """
        added_count = 0
        print(f"🧠 Embedding {len(news_items)} items using {self.embedding_model}...")

        # Create a set of existing links to avoid duplicates
        existing_links = {item.get('link') for item in self.data}

        for news in news_items:
            if news['link'] in existing_links:
                continue

            # Rich text for embedding (Title + Summary)
            text_to_embed = f"{news['title']}. {news['summary']}"
            vector = self._get_embedding(text_to_embed)

            if vector:
                doc = {
                    "id": str(uuid.uuid4()),
                    "metadata": {
                        "title": news['title'],
                        "link": news['link'],
                        "published_at": news['published_at'],
                        "source": news.get('source', 'Unknown'),
                        "summary": news['summary']
                    },
                    "embedding": vector,  # Store 1024-dim vector
                    "created_at": datetime.now().isoformat()
                }
                self.data.append(doc)
                added_count += 1
                # print(f"   Embedded: {news['title'][:30]}...")
        
        if added_count > 0:
            self._save_data()
            print(f"✅ Saved {added_count} new vectors to {self.file_path}")
        else:
            print("Types: No new items to add (or duplicates).")
            
        return added_count

    def search(self, query, n_results=5):
        """
        Semantic Search using Cosine Similarity.
        Returns top N matches.
        """
        query_vector = self._get_embedding(query)
        if not query_vector:
            return []

        print(f"🔍 Scanning {len(self.data)} memories for space: '{query}'...")
        
        scored_results = []
        for doc in self.data:
            score = self._cosine_similarity(query_vector, doc['embedding'])
            scored_results.append((score, doc))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Format output
        results = []
        for score, doc in scored_results[:n_results]:
            results.append({
                "score": round(score, 4),
                "metadata": doc['metadata']
            })
            
        return results
