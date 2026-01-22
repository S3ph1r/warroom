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

    def exists(self, link):
        """Check if a link (URL) is already present in memory."""
        for item in self.data:
            if item['metadata'].get('link') == link:
                return True
        return False
    
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
                # Store all fields in metadata to preserve analysis (scores, reasons, tags)
                metadata = news.copy()
                # Ensure defaults for stability (though engine provides them)
                metadata.update({
                    "title": news['title'],
                    "link": news['link'],
                    "published_at": news.get('published_at'),
                    "source": news.get('source', 'Unknown'),
                    "summary": news.get('summary', '')
                })

                doc = {
                    "id": str(uuid.uuid4()),
                    "metadata": metadata,
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

    def get_recent(self, limit=50):
        """Return the most recent N items."""
        # Sort by created_at desc (or published_at if available and consistent)
        # Using created_at for now as it's reliable
        sorted_data = sorted(self.data, key=lambda x: x.get('created_at', ''), reverse=True)
        return [{"score": 1.0, "metadata": doc['metadata']} for doc in sorted_data[:limit]]

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

    def archive_old_items(self, days=30):
        """
        Moves items older than 'days' to warroom_archive.json.
        Keeps the active memory lean.
        """
        archive_path = os.path.join("data", "warroom_archive.json")
        cutoff_date = datetime.now().timestamp() - (days * 86400)
        
        active_items = []
        archive_items = []
        
        print(f"🧹 Checking for items older than {days} days...")
        
        for doc in self.data:
            try:
                # Support both created_at (ISO) and published_at (ISO)
                date_str = doc.get('created_at') or doc['metadata'].get('published_at')
                if not date_str:
                    active_items.append(doc)
                    continue
                    
                # Robust date parsing
                if 'Z' in date_str:
                    item_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).timestamp()
                elif '+' in date_str:
                     item_date = datetime.fromisoformat(date_str).timestamp()
                else:
                    item_date = datetime.fromisoformat(date_str).timestamp()
                
                if item_date < cutoff_date:
                    archive_items.append(doc)
                else:
                    active_items.append(doc)
            except Exception as e:
                # Keep item if date parsing fails to avoid data loss
                active_items.append(doc)
                
        if archive_items:
            print(f"📦 Archiving {len(archive_items)} old items to {archive_path}...")
            
            # Load existing archive to append
            existing_archive = []
            if os.path.exists(archive_path):
                try:
                    with open(archive_path, 'r', encoding='utf-8') as f:
                        existing_archive = json.load(f)
                except Exception:
                    existing_archive = []
            
            existing_archive.extend(archive_items)
            
            # Save Archive
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(existing_archive, f, ensure_ascii=False, indent=2)
                
            # Update Active Memory
            self.data = active_items
            self._save_data()
            print(f"✅ Active memory reduced to {len(self.data)} items.")
        else:
            print("✨ No items to archive.")
