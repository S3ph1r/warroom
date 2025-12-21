"""
Lightweight ChromaDB + Ollama Client
Removes generic dependencies (chromadb, ollama) to avoid Python compatibility issues.
Uses raw HTTP requests to Docker containers.
"""
import requests
import json
import uuid
import logging

logger = logging.getLogger(__name__)

class VectorMemory:
    def __init__(self, collection_name="warroom_news", embedding_model="mistral-nemo:latest"):
        self.chroma_url = "http://localhost:8000"
        self.ollama_url = "http://localhost:11434"
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.collection_id = None
        
        # Initialize
        if self._check_connection():
            self._get_or_create_collection()
            
    def _check_connection(self):
        try:
            # Check Chroma
            r = requests.get(f"{self.chroma_url}/api/v1/heartbeat", timeout=2)
            if r.status_code != 200:
                print("⚠️ ChromaDB not reachable at localhost:8000")
                return False
                
            # Check Ollama
            r = requests.get(f"{self.ollama_url}/", timeout=2)
            if r.status_code != 200:
                print("⚠️ Ollama not reachable at localhost:11434")
                return False
                
            return True
        except Exception as e:
            print(f"⚠️ Connection error: {e}")
            return False

    def _get_embedding(self, text):
        """Get embedding from Ollama"""
        try:
            url = f"{self.ollama_url}/api/embeddings"
            payload = {
                "model": self.embedding_model,
                "prompt": text
            }
            resp = requests.post(url, json=payload)
            if resp.status_code == 200:
                return resp.json()['embedding']
            else:
                print(f"Ollama Error: {resp.text}")
                return None
        except Exception as e:
            print(f"Embedding Error: {e}")
            return None

    def _get_or_create_collection(self):
        """Get collection ID"""
        try:
            # 1. Try to get collection
            # Note: Chroma API is a bit fluid. simpler to just "get or create"
            # Using standard API v1
            
            # Create/Get
            url = f"{self.chroma_url}/api/v1/collections"
            payload = {"name": self.collection_name, "get_or_create": True}
            resp = requests.post(url, json=payload)
            
            if resp.status_code == 200:
                self.collection_id = resp.json()['id']
                # print(f"Connected to Collection: {self.collection_name} ({self.collection_id})")
            else:
                print(f"Stats Code: {resp.status_code}, Response: {resp.text}")
                
        except Exception as e:
            print(f"Collection Init Error: {e}")

    def add_news(self, news_items):
        """
        Add news items to Vector DB.
        news_items: list of dicts with 'title', 'summary', 'published_at', 'link'
        """
        if not self.collection_id:
            print("No collection ID, cannot add.")
            return

        embeddings = []
        documents = []
        metadatas = []
        ids = []

        print(f"Embedding {len(news_items)} items with {self.embedding_model}...")
        
        for item in news_items:
            # Create rich text for embedding
            text = f"{item['title']}. {item['summary']}"
            vector = self._get_embedding(text)
            
            if vector:
                embeddings.append(vector)
                documents.append(text)
                metadatas.append({
                    "title": item['title'],
                    "link": item['link'],
                    "published_at": item['published_at'],
                    "source": item.get('source', 'Unknown')
                })
                ids.append(str(uuid.uuid4()))
        
        if not ids:
            return 0
            
        # Add to Chroma
        url = f"{self.chroma_url}/api/v1/collections/{self.collection_id}/add"
        payload = {
            "ids": ids,
            "embeddings": embeddings,
            "metadatas": metadatas,
            "documents": documents
        }
        
        try:
            resp = requests.post(url, json=payload)
            if resp.status_code in [200, 201]:
                print(f"✅ Indexed {len(ids)} items in ChromaDB.")
                return len(ids)
            else:
                print(f"Error adding to Chroma: {resp.text}")
                return 0
        except Exception as e:
            print(f"Error posting to Chroma: {e}")
            return 0

    def query_similar(self, query_text, n_results=5):
        """Query similar news"""
        if not self.collection_id: return []
        
        vector = self._get_embedding(query_text)
        if not vector: return []
        
        url = f"{self.chroma_url}/api/v1/collections/{self.collection_id}/query"
        payload = {
            "query_embeddings": [vector],
            "n_results": n_results
        }
        
        try:
            resp = requests.post(url, json=payload)
            if resp.status_code == 200:
                return resp.json()
            return []
        except:
            return []
