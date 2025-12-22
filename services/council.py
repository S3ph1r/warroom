
import os
import asyncio
import logging
import json
from datetime import datetime
from sqlalchemy import func
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
        
        # 1. Google (Gemini Flash Latest)
        try:
            self.models['google'] = LLMWrapper(
                provider="google", 
                api_key=self.google_key,
                model="gemini-flash-latest"
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
                # Clean markdown blocks if present
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
                data['role'] = role_id
                data['model'] = model_name
                data['persona'] = persona
                return data
            except json.JSONDecodeError:
                logger.error(f"[{role_id}] JSON Parse Error. Text: {response_text}")
                return {"role": role_id, "verdict": "Error", "reasoning": "Failed to parse JSON", "raw": response_text[:100]}
        except Exception as e:
            logger.error(f"[{role_id}] Critical Error: {e}")
            return {"role": role_id, "error": str(e)}

    def get_todays_session(self):
        """Checks if a session already exists for today."""
        try:
            db = SessionLocal()
            today = datetime.now().date()
            # Query for sessions created today
            session = db.query(CouncilSession).filter(
                func.date(CouncilSession.timestamp) == today
            ).order_by(CouncilSession.timestamp.desc()).first()
            db.close()
            return session
        except Exception as e:
            logger.error(f"DB Cache Check Failed: {e}")
            return None

    def generate_consensus(self, results_dict):
        """
        Uses Local Mistral to generate a unified consensus and score the models.
        """
        logger.info("Generating Council Consensus via Mistral...")
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
            
            # Use Ollama Helper
            mistral = LLMWrapper(provider="ollama", model="mistral-nemo:latest")
            response = mistral.chat([{"role": "user", "content": prompt}], json_mode=True)
            return response
            
        except Exception as e:
            logger.error(f"Consensus Generation Failed: {e}")
            return None

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

    async def convene_council(self, user_query: str = None, force_refresh: bool = False):
        """
        Consults all advisors. Checks cache first unless force_refresh is True.
        """
        # 0. Check Cache (Daily)
        if not force_refresh:
            cached = self.get_todays_session()
            if cached:
                logger.info("Returning CACHED Council Session.")
                # Return immediately, do NOT block for self-healing. 
                # Frontend will handle missing pieces via discrete refresh calls.
                return {
                    "from_cache": True,
                    "timestamp": cached.timestamp.isoformat(),
                    "responses": cached.responses,
                    "consensus": cached.consensus, 
                    "context": cached.context_snapshot
                }

        # 1. Gather Data (The Dossier)
        logger.info("Gathering Council Dossier...")
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
        consensus_json = await asyncio.to_thread(self.generate_consensus, results_dict)
        
        # 4. Persist Session
        try:
            db = SessionLocal()
            session_record = CouncilSession(
                context_snapshot=dossier,
                responses=results_dict,
                consensus=consensus_json 
            )
            db.add(session_record)
            db.commit()
            db.close()
            logger.info(f"Council Session saved to DB with {len(results_dict)} opinions.")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            
        # Return full structure
        return {
            "from_cache": False,
            "timestamp": dossier['timestamp'],
            "responses": results_dict,
            "consensus": consensus_json,
            "context": dossier
        }

# Singleton instance
council = TheCouncil()
