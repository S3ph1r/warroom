
import os
import asyncio
import logging
import json
from datetime import datetime
import requests
from sqlalchemy import func, cast, Date
from dotenv import load_dotenv

from intelligence.llm_wrapper import LLMWrapper
from intelligence.engine import IntelligenceEngine
from services.portfolio_service import get_anonymous_portfolio_context
from db.database import SessionLocal
from db.models import CouncilSession


load_dotenv()
logger = logging.getLogger(__name__)

class TheCouncil:
    def __init__(self):
        # API Keys
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        if not self.google_key or not self.openrouter_key:
            logger.warning("The Council is missing API Keys. Some advisors may not work.")

        # Initialize Models (The Engines)
        self.models = {}
        
        # 1. Google (Gemini)
        try:
            # Switch back to direct Google Provider as requested by user
            self.models['google'] = LLMWrapper(
                provider="google", 
                api_key=self.google_key,
                model="gemini-2.5-flash"  # Tested and working
            )
        except Exception as e:
            logger.error(f"Failed to init Google Model: {e}")

        # 2. Anthropic (Claude 3.5 Sonnet)
        try:
            self.models['anthropic'] = LLMWrapper(
                provider="openrouter",
                api_key=self.openrouter_key,
                model="anthropic/claude-3.5-sonnet"
            )
        except Exception as e:
            logger.error(f"Failed to init Anthropic Model: {e}")

        # 3. DeepSeek (DeepSeek V3)
        try:
            self.models['deepseek'] = LLMWrapper(
                provider="openrouter",
                api_key=self.openrouter_key,
                model="deepseek/deepseek-chat"
            )
        except Exception as e:
            logger.error(f"Failed to init DeepSeek Model: {e}")

        # 4. Qwen (Qwen 2.5 72B)
        try:
            self.models['qwen'] = LLMWrapper(
                provider="openrouter",
                api_key=self.openrouter_key,
                model="qwen/qwen-2.5-72b-instruct"
            )
        except Exception as e:
            logger.error(f"Failed to init Qwen Model: {e}")

        # 5. Resilience Check
        self.verify_ollama_access()

    def verify_ollama_access(self):
        """
        Proactively checks if Ollama is reachable.
        If running in WSL, localhost might not work without OLLAMA_HOST=0.0.0.0.
        """
        host = os.getenv("OLLAMA_HOST", "localhost")
        port = "11434"
        
        # If host is 0.0.0.0, we check via localhost from here
        check_host = "localhost" if host == "0.0.0.0" else host
        
        # Determine base URL
        if check_host.startswith("http"):
            base_url = check_host
        else:
            base_url = f"http://{check_host}"
            
        # Add port if not present
        if ":" not in base_url.replace("http://", "").replace("https://", ""):
            base_url = f"{base_url}:{port}"

        url = f"{base_url}/api/tags"
        try:
            logger.info(f"🔍 Checking Ollama connectivity at {url}...")
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                logger.info("✅ Ollama is reachable and ready.")
                return True
        except Exception as e:
            logger.warning(f"⚠️  OLLAMA CONNECTION WARNING: Could not connect to {url}")
            logger.warning(f"   Error: {e}")
            logger.warning("   HINT: If Mistral is in WSL, run 'export OLLAMA_HOST=0.0.0.0' inside WSL.")
            return False
        return False

    def _get_system_prompt(self, persona):
        base = "Sei un membro de IL CONSIGLIO, un board strategico finanziario d'élite."
        instructions = "RISPONDI RIGOROSAMENTE IN ITALIANO. Usa terminologia finanziaria professionale."
        
        if persona == 'historian':
            return f"{base} Sei LO STORICO (The Historian). La tua forza è il contesto e i paralleli storici. Analizza la situazione comparandola con cicli di mercato passati. Sii accademico ma conciso. {instructions} Output in JSON."
        elif persona == 'strategist':
            return f"{base} Sei LO STRATEGA (The Strategist). La tua forza è la gestione del rischio e la teoria dei giochi. Sii cinico. Cerca cosa potrebbe andare storto (Black Swans). Identifica asimmetrie rischiose. {instructions} Output in JSON."
        
        return base

    async def consult_model_persona(self, model_name, persona, context):
        """
        Consults a specific Model with a specific Persona.
        """
        if model_name not in self.models:
            return {"role": f"{model_name}_{persona}", "error": "Model not initialized"}
        
        advisor = self.models[model_name]
        prompt = self._get_system_prompt(persona)
        role_id = f"{model_name}_{persona}"
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"CONTESTO DI MERCATO:\n{context}\n\nFornisci la tua analisi in formato JSON con i campi: 'verdict' (Bullish/Bearish/Neutral), 'confidence' (0-100), 'reasoning' (testo in italiano), 'actionable_advice' (bullet point)."}
        ]
        
        loop = asyncio.get_event_loop()
        try:
            response_text = await loop.run_in_executor(None, advisor.chat, messages, True)
            logger.info(f"[{role_id}] Raw Response: {response_text[:100]}...") # Log summary
            
            if not response_text:
                 return {"role": role_id, "error": "Empty response from LLM"}

            try:
                # Robustly extract JSON if embedded in markdown
                clean_text = response_text
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[-1].split("```")[0].strip()
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[-1].split("```")[0].strip()
                else:
                    clean_text = clean_text.strip()
                
                # Check for direct error strings
                if clean_text.startswith("Error:"):
                     raise ValueError(clean_text)

                data = json.loads(clean_text)
                
                # Add default fields if missing
                data.setdefault('verdict', 'Neutral')
                data.setdefault('confidence', 50)
                data.setdefault('reasoning', 'Analisi non disponibile.')
                data.setdefault('actionable_advice', [])

                data['role'] = role_id
                data['model'] = model_name
                data['persona'] = persona
                return data
            except (json.JSONDecodeError, ValueError, Exception) as je:
                logger.error(f"[{role_id}] Parse/Logic Error: {je}. Raw Text: {response_text}")
                return {
                    "role": role_id, 
                    "verdict": "Error", 
                    "reasoning": f"Errore nell'analisi del parere: {str(je)}", 
                    "raw_text": response_text[:200]
                }
        except Exception as e:
            logger.error(f"[{role_id}] Critical Error: {e}")
            return {"role": role_id, "error": str(e)}

    def get_todays_session(self, model: str = None):
        """Checks if a session already exists for today. Optionally filters by model."""
        return self.get_session_by_date(datetime.now().date(), model)

    def get_session_by_date(self, target_date, model: str = None):
        """Retrieves a Council Session for a specific date and optional model."""
        try:
            db = SessionLocal()
            query = db.query(CouncilSession).filter(
                cast(CouncilSession.timestamp, Date) == target_date
            )
            
            # If model is specified, filter by it.
            # If not specified (old behavior), just get the latest regardless.
            if model:
                query = query.filter(CouncilSession.consensus_model == model)
            
            session = query.order_by(CouncilSession.timestamp.desc()).first()
            db.close()
            return session
        except Exception as e:
            logger.error(f"DB Retrieval Failed for {target_date}: {e}")
            return None

    def get_session_history(self):
        """Returns a list of dates containing Council Sessions."""
        try:
            db = SessionLocal()
            # Select distinct dates
            dates = db.query(cast(CouncilSession.timestamp, Date)).distinct().order_by(
                cast(CouncilSession.timestamp, Date).desc()
            ).all()
            db.close()
            # Unpack tuples keys
            return [d[0].isoformat() for d in dates]
        except Exception as e:
            logger.error(f"History Retrieval Failed: {e}")
            return []

    def generate_consensus(self, results_dict, model: str = "mistral-nemo:latest"):
        """
        Uses Local Ollama to generate a unified consensus and score the models.
        Returns: tuple(consensus_json, model_name) or (None, model_name) on failure.
        """
        logger.info(f"Generating Council Consensus via Ollama ({model})...")
        try:
            # Prepare input for Mistral
            opinions_text = ""
            for role, data in results_dict.items():
                opinions_text += f"\n--- {role.upper()} ---\nVerdict: {data.get('verdict')}\nReasoning: {data.get('reasoning')}\nConfidence: {data.get('confidence')}\n"
            
            prompt = f"""
            You are the PRESIDENT of The Council.
            Review the following 8 opinions from your advisors (Historians and Strategists).
            
            ADVISOR OPINIONS:
            {opinions_text}
            
            YOUR TASK:
            1. Write an "Executive Summary" (in Italian) merging the insights. Identify the dominant sentiment.
            2. Assign a "Depth Score" (0-10) to each model (Google, Anthropic, DeepSeek, Qwen) based on their reasoning quality.
            3. Output strictly in JSON format.
            
            JSON STRUCTURE:
            {{
                "summary": "Full text summary here...",
                "scores": {{
                    "google": 0,
                    "anthropic": 0,
                    "deepseek": 0,
                    "qwen": 0
                }}
            }}
            """
            
            # Use Ollama Helper with configurable model
            ollama_model = LLMWrapper(provider="ollama", model=model)
            response = ollama_model.chat([{"role": "user", "content": prompt}], json_mode=True)
            return response, model
            
        except Exception as e:
            logger.error(f"Consensus Generation Failed: {e}")
            return None, model

    async def refresh_council_item(self, item_id: str):
        """
        Refreshes a specific item (Consensus or specific Model Persona) for the current daily session.
        """
        session = self.get_todays_session()
        if not session:
            raise ValueError("No active session found for today. Please convene the council first.")
        
        # 1. Handle Consensus Refresh
        if item_id == "consensus":
            logger.info("Refreshing Consensus...")
            new_consensus = await asyncio.to_thread(self.generate_consensus, session.responses)
            if new_consensus:
                try:
                    db = SessionLocal()
                    s = db.query(CouncilSession).filter(CouncilSession.id == session.id).first()
                    s.consensus = new_consensus
                    db.commit()
                    db.refresh(s)
                    db.close()
                    return {"type": "consensus", "data": new_consensus}
                except Exception as e:
                    logger.error(f"DB Update Failed: {e}")
                    raise
            else:
                raise ValueError("Consensus generation returned empty.")

        # 2. Handle Advisor Refresh (e.g. "anthropic_strategist")
        else:
            if "_" not in item_id:
                raise ValueError(f"Invalid item_id: {item_id}")
            
            model, persona = item_id.split("_")
            logger.info(f"Refreshing Advisor: {model} - {persona}")
            
            # We need the original context
            context_str = json.dumps(session.context_snapshot)
            
            # Call the single model
            new_response = await self.consult_model_persona(model, persona, context_str)
            
            # Update the responses dict
            try:
                db = SessionLocal()
                s = db.query(CouncilSession).filter(CouncilSession.id == session.id).first()
                
                # SQLAlchemy JSON mutation often requires re-assigning the whole dict or using flag_modified
                # simpler to copy, update, assign
                current_responses = dict(s.responses)
                current_responses[item_id] = new_response
                s.responses = current_responses
                
                # Flag modified just in case (for JSONB/JSON)
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(s, "responses")
                
                db.commit()
                db.close()
                return {"type": "advisor", "id": item_id, "data": new_response}
            except Exception as e:
                logger.error(f"DB Update Failed: {e}")
                raise

    async def convene_council(self, user_query: str = None, force_refresh: bool = False, model: str = "mistral-nemo:latest"):
        """
        Consults all advisors. Checks cache first.
        Smart Refresh: If data exists but has missing/errored items, repair them instead of re-running everything.
        """
        # 0. Check Cache (Daily)
        cached = self.get_todays_session(model)
        
        if cached and not force_refresh:
            logger.info(f"Found existing Council Session for model {model}. Checking for missing data...")
            
            responses = dict(cached.responses)
            target_models = ['google', 'anthropic', 'deepseek', 'qwen']
            target_personas = ['historian', 'strategist']
            
            missing_tasks = []
            context_str = json.dumps(cached.context_snapshot)
            
            for m in target_models:
                for p in target_personas:
                    role_id = f"{m}_{p}"
                    resp = responses.get(role_id)
                    # Check if missing or has error
                    if not resp or resp.get('error') or resp.get('verdict') == 'Error':
                        logger.info(f"Repairing missing/errored advisor: {role_id}")
                        missing_tasks.append(self.consult_model_persona(m, p, context_str))
            
            if missing_tasks:
                new_results = await asyncio.gather(*missing_tasks)
                for r in new_results:
                    responses[r['role']] = r
                
                # Update DB
                try:
                    db = SessionLocal()
                    s = db.query(CouncilSession).filter(CouncilSession.id == cached.id).first()
                    s.responses = responses
                    
                    # Re-generate consensus if opinions were repaired
                    logger.info("Regenerating consensus with repaired opinions...")
                    consensus_json, consensus_model = await asyncio.to_thread(self.generate_consensus, responses, model)
                    s.consensus = consensus_json
                    
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(s, "responses")
                    
                    db.commit()
                    db.refresh(s)
                    db.close()
                    
                    # Return the updated version
                    return {
                        "from_cache": True,
                        "repaired": True,
                        "timestamp": s.timestamp.isoformat(),
                        "responses": s.responses,
                        "consensus": s.consensus,
                        "consensus_model": s.consensus_model,
                        "context": s.context_snapshot
                    }
                except Exception as e:
                    logger.error(f"Failed to save repaired session: {e}")
            
            # If all were already present or repair failed, return what we have
            logger.info(f"Returning CACHED Council Session.")
            return {
                "from_cache": True,
                "timestamp": cached.timestamp.isoformat(),
                "responses": cached.responses,
                "consensus": cached.consensus,
                "consensus_model": cached.consensus_model,
                "context": cached.context_snapshot
            }

        # 1. Gather Data (The Dossier) - ONLY if no session or force_refresh
        logger.info("Gathering Council Dossier for a fresh session...")
        portfolio = get_anonymous_portfolio_context()
        
        # News Context (Mistral)
        intel_engine = IntelligenceEngine(portfolio_context=str(portfolio)) 
        market_brief = intel_engine.generate_daily_briefing()
        
        # Build Context String
        dossier = {
            "timestamp": datetime.now().isoformat(),
            "portfolio_summary": portfolio,
            "market_briefing": market_brief,
            "user_specific_query": user_query
        }
        
        context_str = json.dumps(dossier, indent=2)
        
        # 2. Consult Advisors (Matrix 4x2)
        tasks = []
        target_models = ['google', 'anthropic', 'deepseek', 'qwen']
        target_personas = ['historian', 'strategist']
        
        for m in target_models:
            for p in target_personas:
                tasks.append(self.consult_model_persona(m, p, context_str))
        
        results_list = await asyncio.gather(*tasks)
        results_dict = {r['role']: r for r in results_list}
        
        # 3. Generate Consensus
        consensus_json, consensus_model = await asyncio.to_thread(self.generate_consensus, results_dict, model)
        
        # 4. Persist Session
        try:
            db = SessionLocal()
            session_record = CouncilSession(
                context_snapshot=dossier,
                responses=results_dict,
                consensus=consensus_json,
                consensus_model=consensus_model
            )
            db.add(session_record)
            db.commit()
            db.close()
            logger.info(f"Council Session saved to DB with {len(results_dict)} opinions. Model: {consensus_model}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            
        # Return full structure
        return {
            "from_cache": False,
            "timestamp": dossier['timestamp'],
            "responses": results_dict,
            "consensus": consensus_json,
            "consensus_model": consensus_model,
            "context": dossier
        }

    def get_available_ollama_models(self):
        """
        Queries Ollama API to get list of available models.
        """
        try:
            # We assume Ollama is at the standard port or bridge port
            ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
            # Clean up host string if needed
            if not ollama_host.startswith("http"):
                ollama_host = f"http://{ollama_host}"
                
            res = requests.get(f"{ollama_host}/api/tags", timeout=2)
            if res.status_code == 200:
                data = res.json()
                # Extract model names
                models = [m['name'] for m in data.get('models', [])]
                return models
            return []
        except Exception as e:
            logger.error(f"Failed to fetch Ollama models: {e}")
            return []

# Singleton instance
council = TheCouncil()
