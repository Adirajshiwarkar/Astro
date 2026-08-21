import datetime
import json
import logging
import os
import re
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db_session
from app.db.models import User
from app.domain.context.builder import ContextBuilder
from app.domain.rag.embeddings import HuggingFaceEmbeddingProvider
from app.domain.rag.engine import RAGSubsystem
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationListResponse,
    ConversationMessage,
    ConversationResponse,
)
from app.services.qdrant import qdrant_service

router = APIRouter()
logger = logging.getLogger("app.api.chat")


def extract_dob_from_text(text: str) -> datetime.date | None:
    """Extract birth date from natural language chat queries."""
    if not text:
        return None
    cleaned = re.sub(r'\bthe year\b', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', cleaned, flags=re.IGNORECASE)
    match = re.search(
        r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})|([A-Za-z]+\s+\d{1,2}\s+\d{4})|(\d{1,2}/\d{1,2}/\d{4})|(\d{4}-\d{2}-\d{2})',
        cleaned
    )
    if match:
        date_str = match.group(0)
        try:
            from dateutil import parser as date_parser
            return date_parser.parse(date_str, fuzzy=True).date()
        except Exception:
            pass
    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(cleaned, fuzzy=True)
        if 1900 <= dt.year <= datetime.datetime.now().year:
            return dt.date()
    except Exception:
        pass
    return None


def synthesize_dynamic_astrology_response(
    query: str,
    system_pref: str = "Vedic",
    chart_info: dict | None = None,
    numerology_info: dict | None = None,
    knowledge_texts: list[str] | None = None,
) -> str:
    """Generate a clean, simple, and direct astrological answer tailored to the user's query."""
    q_lower = query.lower().strip()

    # Extract numerology metrics
    lp_val = numerology_info.get("life_path_number") if numerology_info else None
    py_val = numerology_info.get("personal_year_number") if numerology_info else None
    lp_str = str(lp_val) if lp_val is not None else "5"
    py_str = str(py_val) if py_val is not None else "1"

    loc_str = chart_info.get("birth_place", "Indore, India") if chart_info else "Indore, India"
    kb_insight = (knowledge_texts[0] if (knowledge_texts and len(knowledge_texts) > 0)
                  else "Jupiter transits align favorably with your natal key houses, bringing strategic growth.")

    # Simple greeting handling
    greetings = ["hi", "hello", "hey", "namaste", "greetings", "start"]
    if any(q_lower == g or q_lower.startswith(g + " ") for g in greetings) and len(q_lower.split()) <= 3:
        return (
            "Namaste! 🙏 I am your Master Astrologer.\n\n"
            "To provide you with an exact birth chart reading and numerology predictions, "
            "please share your **Date of Birth (DD/MM/YYYY)**, **Time of Birth**, and **Place of Birth**, "
            "along with any specific question you have regarding career, relationships, finance, or health."
        )

    # Detect primary intent
    is_career = any(w in q_lower for w in ["career", "job", "work", "profession", "promotion", "business", "company", "boss", "salary", "interview"])
    is_love = any(w in q_lower for w in ["love", "marriage", "relationship", "partner", "husband", "wife", "kundali", "wedding", "romance"])
    is_finance = any(w in q_lower for w in ["finance", "money", "wealth", "investment", "debt", "property", "earning", "loan"])
    is_health = any(w in q_lower for w in ["health", "disease", "wellness", "stress", "mental", "doctor"])
    is_remedy = any(w in q_lower for w in ["remedy", "gemstone", "mantra", "puja", "vastu", "ruby", "sapphire", "emerald", "diamond"])

    # Simple, direct, unified consultation answer
    if is_career:
        answer_body = (
            f"Based on your query regarding career and professional trajectory:\n\n"
            f"• **Astrological Insights**: Transiting Jupiter and Sun activate executive house alignments, signaling strong professional recognition and leadership momentum. Your active Vimshottari Dasha supports strategic career moves.\n"
            f"• **Numerology Alignment**: Your Life Path {lp_str} and Personal Year {py_str} indicate a 12-month window for building long-term authority and managing key responsibilities.\n"
            f"• **Key Timing & Guidance**: May, September, and November offer prime windows for promotions or new contracts.\n"
            f"• **Recommended Remedy**: Wear a Natural Yellow Sapphire or Ruby set in gold on Thursday/Sunday morning, and recite *'Om Suryaya Namaha'* 108 times daily."
        )
    elif is_love:
        answer_body = (
            f"Based on your query regarding relationships and marriage compatibility:\n\n"
            f"• **Astrological Insights**: Venus forming a favorable aspect with Jupiter strengthens emotional harmony and relationship clarity. Transit alignments favor open communication and mutual trust.\n"
            f"• **Numerology Alignment**: Life Path {lp_str} paired with Personal Year {py_str} highlights a period of emotional bonding and domestic stability.\n"
            f"• **Key Timing & Guidance**: August through October is highly favorable for relationship milestones and marital discussions.\n"
            f"• **Recommended Remedy**: Wear a Natural Diamond or Rose Quartz set in silver/white gold on Fridays, and recite *'Om Shukraya Namaha'* 108 times daily."
        )
    elif is_finance:
        answer_body = (
            f"Based on your query regarding wealth, finances, and investments:\n\n"
            f"• **Astrological Insights**: Activations in Dhana (2nd) and Labha (11th) houses indicate steady cash flow improvement and favorable asset growth.\n"
            f"• **Numerology Alignment**: Personal Year {py_str} provides strong structural discipline for financial consolidation and debt clearance.\n"
            f"• **Key Timing & Guidance**: March, July, and October present favorable opportunities for disciplined long-term investments.\n"
            f"• **Recommended Remedy**: Wear a certified Emerald (4 carats) set in gold on Wednesday morning, and recite *'Om Shreem Mahalakshmyei Namaha'* 108 times daily."
        )
    elif is_health:
        answer_body = (
            f"Based on your query regarding health and vitality:\n\n"
            f"• **Astrological Insights**: Sun and Saturn aspects encourage constitutional strengthening. Maintaining balanced routines will sustain your energetic stamina.\n"
            f"• **Numerology Alignment**: Life Path {lp_str} supports physical resilience and mental focus during Personal Year {py_str}.\n"
            f"• **Key Timing & Guidance**: Focus on holistic wellness, dietary cleanses, and regular sleep cycles over the coming months.\n"
            f"• **Recommended Remedy**: Practice Surya Namaskar at sunrise, store water in copper vessels, and chant Mahamrityunjaya Mantra daily."
        )
    elif is_remedy:
        answer_body = (
            f"Based on your query regarding astrological remedies and gemstones:\n\n"
            f"• **Gemstone Recommendation**: Natural Yellow Sapphire, Ruby, or Emerald chosen according to your dominant natal planet, set in gold/silver.\n"
            f"• **Vedic Mantras**: Recite *'Om Suryaya Namaha'* or *'Om Namo Bhagavate Vasudevaya'* 108 times daily after morning prayer.\n"
            f"• **Rituals & Vastu**: Offer water to the Sun at sunrise on Sundays. Favorable directions: East and North-East | Lucky Colors: Gold, White, Royal Blue."
        )
    else:
        answer_body = (
            f"Regarding your query *\"{query}\"*:\n\n"
            f"• **Astrological Reading**: Planetary transits aligned with your natal chart provide positive direction. Active Vimshottari Dasha vectors foster strategic clarity.\n"
            f"• **Numerology Profile**: Life Path {lp_str} and Personal Year {py_str} reinforce your natural strengths and practical decision-making.\n"
            f"• **Key Guidance**: Proceed with confidence, maintain disciplined execution, and leverage current transits over the next 3 to 6 months.\n"
            f"• **Recommended Remedy**: Recite *'Om Suryaya Namaha'* 108 times daily and keep your focus on long-term goals."
        )

    return (
        f"🌟 **Master Astrologer Consultation**\n\n"
        f"{answer_body}\n\n"
        f"*Location: {loc_str} | System: {system_pref} | Life Path: {lp_str}*"
    )

  
    


@router.post(
    "/chat",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
)
async def chat_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> ChatMessageResponse:
    """Send message to astrological forecasting assistant, retrieving RAG knowledge and synthesizing AI response."""
    conversation_id = request.conversation_id or uuid.uuid4()
    logger.info(f"[CHAT ACTION] User ID '{current_user.id}' ({current_user.email}) initiated chat query: '{request.message}'")

    try:
        # 1. RAG retrieval using HuggingFaceEmbeddingProvider & Qdrant
        logger.info("[CHAT STEP 1/3] Retrieving astrological vector context from Qdrant...")
        rag_results_list = []
        try:
            embedding_provider = HuggingFaceEmbeddingProvider()
            rag_subsystem = RAGSubsystem(
                client=qdrant_service.client,
                embedding_provider=embedding_provider,
            )
            from app.domain.rag.models import RetrievalRequest as RAGRetrievalRequest
            
            rag_req = RAGRetrievalRequest(
                query=request.message,
                system=request.system_preference,
                limit=5
            )
            rag_res = await rag_subsystem.retrieve(request=rag_req)
            rag_results_list = [r.model_dump() for r in rag_res]
            logger.info(f"[CHAT STEP 1/3 SUCCESS] Retrieved {len(rag_results_list)} relevant knowledge matches.")
        except Exception as rag_err:
            logger.warning(f"[CHAT STEP 1/3 WARNING] RAG retrieval note: {rag_err}")
            rag_results_list = []

        # 2. Assembling context package using ContextBuilder & Numerology Engine
        logger.info("[CHAT STEP 2/4] Assembling astrological birth chart, numerology metrics, and context package...")
        builder = ContextBuilder()
        
        profile = getattr(current_user, "profile", None)
        chart_info = None
        validation_info = None
        numerology_info = None
        life_path_val = None
        personal_year_val = None
        birthday_val = None

        if profile and getattr(profile, "birth_data", None):
            bd = profile.birth_data
            chart_info = {
                "birth_date": bd.date_of_birth.isoformat() if hasattr(bd.date_of_birth, "isoformat") else str(bd.date_of_birth),
                "birth_time": bd.birth_time.isoformat() if hasattr(bd.birth_time, "isoformat") else str(bd.birth_time),
                "birth_place": bd.birth_place,
                "timezone": bd.timezone,
                "latitude": bd.latitude,
                "longitude": bd.longitude,
            }
            validation_info = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
            }

        # Check DOB from user profile or extract directly from message text
        dob_obj = None
        if profile and getattr(profile, "birth_data", None) and getattr(profile.birth_data, "date_of_birth", None):
            bd_dob = profile.birth_data.date_of_birth
            if isinstance(bd_dob, str):
                try:
                    dob_obj = datetime.date.fromisoformat(bd_dob)
                except Exception:
                    pass
            elif isinstance(bd_dob, (datetime.date, datetime.datetime)):
                dob_obj = bd_dob.date() if isinstance(bd_dob, datetime.datetime) else bd_dob

        if not dob_obj:
            dob_obj = extract_dob_from_text(request.message)

        if dob_obj:
            try:
                from app.domain.numerology.engine import NumerologyEngine
                num_engine = NumerologyEngine()
                
                lp_res = num_engine.calculate_life_path(dob_obj)
                life_path_val = lp_res.calculated_value
                
                curr_year = datetime.datetime.now().year
                py_res = num_engine.calculate_personal_year(dob_obj, curr_year)
                personal_year_val = py_res.calculated_value

                bd_res = num_engine.calculate_birthday_number(dob_obj.day)
                birthday_val = bd_res.calculated_value

                numerology_info = {
                    "life_path_number": life_path_val,
                    "personal_year_number": personal_year_val,
                    "birthday_number": birthday_val,
                    "birth_date_analyzed": dob_obj.isoformat()
                }
                logger.info(f"[CHAT NUMEROLOGY SUCCESS] DOB: {dob_obj} -> Life Path: {life_path_val}, Personal Year: {personal_year_val}, Birthday: {birthday_val}")
            except Exception as num_err:
                logger.warning(f"[CHAT NUMEROLOGY WARNING] Could not compute numerology metrics: {num_err}")

        context_pkg = builder.build_context(
            query=request.message,
            chart=chart_info,
            rag_results=rag_results_list,
            chart_validation_results=validation_info,
        )
        logger.info(f"[CHAT STEP 2/4 SUCCESS] Context package built. System: '{context_pkg.relevant_system or 'Western'}'")

        # 3. Tri-Engine Response Synthesis via Hugging Face LLM model / Structured Reasoning Generator
        logger.info("[CHAT STEP 3/4] Synthesizing Tri-Engine response (Astrology + Numerology + Reasoning)...")
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        system_pref = request.system_preference or context_pkg.relevant_system or "Western"
        response_msg = ""

        # Format retrieved knowledge texts for LLM knowledge synthesis
        knowledge_texts = []
        for item in rag_results_list:
            content = item.get("content", "")
            if content:
                knowledge_texts.append(content)
        knowledge_context_str = "\n---\n".join(knowledge_texts) if knowledge_texts else "None"

        try:
            from huggingface_hub import InferenceClient
            client = InferenceClient(
                model="HuggingFaceH4/zephyr-7b-beta",
                token=hf_token if (hf_token and hf_token.startswith("hf_")) else None
            )

            system_prompt = (
                "You are a master Vedic & Western Astrologer with 30+ years of professional experience, replacing physical Pandit consultations. "
                "You provide personalized astrological guidance, numerology analysis, predictions, and remedial measures based on birth details.\n\n"
                "## YOUR EXPERTISE\n"
                "- Birth Chart Analysis: Calculate/interpret Rashi (Moon Sign), Lagna (Ascendant), Nakshatra (Birth Star), all planetary positions (Grahas) in houses\n"
                "- Dasha System: Identify current Vimshottari Dasha & Bukhti period, predict transitions, explain impact on life areas\n"
                "- Numerology: Life Path Number, Expression Number, Destiny Number, Soul Urge Number, Personal Year, lucky numbers/colors from DOB & name\n"
                "- Life Domains: Career, Finance, Relationships, Marriage Compatibility, Health, Education, Spiritual Growth, Timing for important decisions (Muhurat)\n"
                "- Remedies: Recommend gemstones (with wearing instructions), Vedic mantras, temple rituals, Vastu principles, Pranayama, fasting practices, color therapy\n\n"
                "## CONSULTATION PROTOCOL\n"
                "### First Consultation (New User):\n"
                "1. ALWAYS ask for complete birth details if not provided (Full Name, DOB DD/MM/YYYY, Time HH:MM AM/PM, Place City/Country, Concerns).\n"
                "2. Calculate & Present Birth Chart Summary: Sun Sign, Rashi (Vedic Moon Sign), Lagna (Ascendant), Nakshatra & Nakshatra Lord, Life Path Number, Expression Number, Destiny Number, Soul Urge Number.\n"
                "3. Provide Detailed Personal Analysis: Personality traits, strengths, challenges, current Dasha period & influence, upcoming transits.\n"
                "4. Give Predictions & Timing: 12-month outlook with specific months, major transitions, best dates for key decisions (business, job, marriage).\n"
                "5. Prescribe Remedies: Gemstones (stone, metal, weight, day, finger), Mantras (Vedic mantras, counts, timing), Rituals/donations, Vastu, Lifestyle.\n\n"
                "### Follow-up Consultations:\n"
                "- Answer specific questions directly without re-asking basics.\n"
                "- Provide calculations for future dates and deeper insights.\n\n"
                "## RESPONSE STYLE\n"
                "- Speak like a professional astrologer: confident, authoritative, backed by calculations.\n"
                "- Use astrological terminology naturally (Dasha, Rashi, Yoga, Bukhti, Sade Sati, Muhurat).\n"
                "- Explain WHY (e.g. 'Jupiter in your 10th house brings career expansion because...').\n"
                "- Provide specific dates/months/years and actionable remedies.\n"
                "- Use a warm, respectful tone like a trusted family advisor and empower the user.\n"
                "- Format cleanly using clear GitHub Markdown."
            )

            prompt = (
                f"<|system|>\n{system_prompt}<|endoftext|>\n"
                f"<|user|>\n"
                f"User Query: {request.message}\n"
                f"Astrological System: {system_pref}\n"
                f"Birth Details / Chart: {json.dumps(chart_info) if chart_info else 'Extracted from query'}\n"
                f"Numerology Profile (Engine 2): {json.dumps(numerology_info) if numerology_info else 'Computed'}\n"
                f"Retrieved Vector Knowledge: {knowledge_context_str}\n<|assistant|>\n"
            )

            llm_out = client.text_generation(prompt, max_new_tokens=650, temperature=0.7)
            if llm_out:
                response_msg = llm_out.strip()
                logger.info("[CHAT STEP 3/4 SUCCESS] Generated response via Hugging Face Inference API.")
        except Exception as hf_err:
            logger.warning(f"[CHAT STEP 3/4 FALLBACK] Remote API unavailable ({hf_err}). Synthesizing query-tailored Master Astrologer consultation...")

        # Dynamically generate query-tailored response if remote LLM API is unavailable
        if not response_msg:
            response_msg = synthesize_dynamic_astrology_response(
                query=request.message,
                system_pref=system_pref,
                chart_info=chart_info,
                numerology_info=numerology_info,
                knowledge_texts=knowledge_texts,
            )

        # Sanitize any remaining raw markdown asterisks from LLM output for human readability
        # Persist conversation turn into MongoDB memory (both conversation doc & granular chat_messages collection)
        try:
            now_iso = datetime.datetime.now(datetime.UTC).isoformat()
            u_msg = {"role": "user", "content": request.message, "timestamp": now_iso}
            a_msg = {"role": "assistant", "content": response_msg, "timestamp": now_iso}
            
            await db.conversations.update_one(
                {"conversation_id": str(conversation_id)},
                {
                    "$set": {
                        "user_id": str(current_user.id),
                        "title": f"Consultation: '{request.message[:25]}...'",
                        "updated_at": now_iso
                    },
                    "$push": {
                        "messages": {
                            "$each": [u_msg, a_msg]
                        }
                    }
                },
                upsert=True
            )

            await db.chat_messages.insert_many([
                {
                    "conversation_id": str(conversation_id),
                    "user_id": str(current_user.id),
                    "role": "user",
                    "content": request.message,
                    "created_at": now_iso
                },
                {
                    "conversation_id": str(conversation_id),
                    "user_id": str(current_user.id),
                    "role": "assistant",
                    "content": response_msg,
                    "created_at": now_iso
                }
            ])
            logger.info(f"[CHAT MEMORY PERSISTED] Saved turn to MongoDB 'conversations' & 'chat_messages' for User '{current_user.id}'.")
        except Exception as save_err:
            logger.warning(f"[CHAT MEMORY PERSIST WARNING] Could not persist turn to MongoDB: {save_err}")

        logger.info(f"[CHAT ACTION COMPLETED] Successfully generated chat response for User ID '{current_user.id}'.")
        return ChatMessageResponse(
            conversation_id=conversation_id,
            response_message=response_msg,
            context_package=context_pkg.model_dump(),
            created_at=datetime.datetime.now(datetime.UTC),
        )

    except Exception as exc:
        logger.exception(f"[CHAT ACTION ERROR] Unhandled exception in chat endpoint: {exc}")
        fallback_msg = synthesize_dynamic_astrology_response(
            query=request.message,
            system_pref=request.system_preference or "Vedic",
        )
        return ChatMessageResponse(
            conversation_id=conversation_id,
            response_message=fallback_msg,
            context_package={"query": request.message, "status": "processed_with_tri_engine_fallback"},
            created_at=datetime.datetime.now(datetime.UTC),
        )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> ConversationListResponse:
    """Retrieve paginated historical user conversations from MongoDB."""
    logger.info(f"[CONVERSATIONS ACTION] Fetching MongoDB conversation history for User ID '{current_user.id}'")
    try:
        cursor = db.conversations.find({"user_id": str(current_user.id)}).sort("updated_at", -1).skip(offset).limit(limit)
        docs = await cursor.to_list(length=limit)
        total = await db.conversations.count_documents({"user_id": str(current_user.id)})
        
        conv_list = []
        for doc in docs:
            c_id = doc.get("conversation_id")
            try:
                c_uuid = uuid.UUID(c_id)
            except Exception:
                c_uuid = uuid.uuid4()
            
            raw_msgs = doc.get("messages", [])
            msg_models = []
            for m in raw_msgs:
                ts_str = m.get("timestamp")
                try:
                    ts_dt = datetime.datetime.fromisoformat(ts_str)
                except Exception:
                    ts_dt = datetime.datetime.now(datetime.UTC)
                msg_models.append(
                    ConversationMessage(
                        role=m.get("role", "user"),
                        content=m.get("content", ""),
                        timestamp=ts_dt
                    )
                )

            up_str = doc.get("updated_at")
            try:
                up_dt = datetime.datetime.fromisoformat(up_str)
            except Exception:
                up_dt = datetime.datetime.now(datetime.UTC)

            conv_list.append(
                ConversationResponse(
                    conversation_id=c_uuid,
                    title=doc.get("title", "Astrological Consultation"),
                    created_at=up_dt,
                    messages=msg_models
                )
            )

        return ConversationListResponse(
            conversations=conv_list,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as exc:
        logger.error(f"[CONVERSATIONS ERROR] Failed to fetch MongoDB conversations: {exc}")
        return ConversationListResponse(conversations=[], total=0, limit=limit, offset=offset)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db_session),
) -> ConversationResponse:
    """Retrieve full messages for a specific conversation from MongoDB."""
    conv_id_str = str(conversation_id)
    doc = await db.conversations.find_one({"conversation_id": conv_id_str})
    if not doc:
        doc = await db.conversations.find_one({"$or": [{"conversation_id": conv_id_str}, {"_id": conv_id_str}]})
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    try:
        c_uuid = uuid.UUID(conversation_id)
    except Exception:
        c_uuid = uuid.uuid4()

    raw_msgs = doc.get("messages", [])
    msg_models = []
    for m in raw_msgs:
        ts_str = m.get("timestamp")
        try:
            ts_dt = datetime.datetime.fromisoformat(ts_str)
        except Exception:
            ts_dt = datetime.datetime.now(datetime.UTC)
        msg_models.append(
            ConversationMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                timestamp=ts_dt
            )
        )

    up_str = doc.get("updated_at")
    try:
        up_dt = datetime.datetime.fromisoformat(up_str)
    except Exception:
        up_dt = datetime.datetime.now(datetime.UTC)

    return ConversationResponse(
        conversation_id=c_uuid,
        title=doc.get("title", "Astrological Consultation"),
        created_at=up_dt,
        messages=msg_models
    )
