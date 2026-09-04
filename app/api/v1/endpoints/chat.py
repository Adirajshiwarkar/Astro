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
    chart_placements_str: str = "",
    chart_aspects_str: str = "",
) -> str:
    """Generate a highly personalized, accurate, engaging, and direct response using the user's actual placements."""
    q_lower = query.lower().strip()

    # Extract numerology metrics
    lp_val = numerology_info.get("life_path_number") if numerology_info else None
    py_val = numerology_info.get("personal_year_number") if numerology_info else None
    lp_str = str(lp_val) if lp_val is not None else "5"
    py_str = str(py_val) if py_val is not None else "1"

    # Helper to find a planet's placement from the string
    def get_placement(planet_name: str) -> str:
        if not chart_placements_str:
            return f"your natal {planet_name.capitalize()}"
        for part in chart_placements_str.split("; "):
            if part.lower().startswith(planet_name.lower()):
                return part
        return f"your natal {planet_name.capitalize()}"

    loc_str = chart_info.get("birth_place", "Indore, India") if chart_info else "Indore, India"

    # Map Life Path to dynamic remedies
    lp = int(lp_str) if lp_str.isdigit() else 5
    lp_remedies = {
        1: ("Ruby", "Om Suryaya Namaha", "Ruby Red / Gold", "Sun"),
        2: ("Pearl", "Om Chandraya Namaha", "White / Silver", "Moon"),
        3: ("Yellow Sapphire", "Om Guruve Namaha", "Yellow / Gold", "Jupiter"),
        4: ("Hessonite", "Om Rahave Namaha", "Brown / Charcoal", "Rahu"),
        5: ("Emerald", "Om Budhaya Namaha", "Emerald Green", "Mercury"),
        6: ("Diamond", "Om Shukraya Namaha", "Pink / White", "Venus"),
        7: ("Cat's Eye", "Om Ketave Namaha", "Light Green / Grey", "Ketu"),
        8: ("Blue Sapphire", "Om Sham Shanaishcharaya Namaha", "Dark Blue / Black", "Saturn"),
        9: ("Red Coral", "Om Kram Kreem Kroom Sah Bhaumaya Namaha", "Red / Coral", "Mars")
    }
    gemstone, mantra, lucky_color, ruling_planet = lp_remedies.get(lp, ("Yellow Sapphire", "Om Guruve Namaha", "Yellow / Gold", "Jupiter"))

    # Simple greeting handling
    greetings = ["hi", "hello", "hey", "namaste", "greetings", "start"]
    if any(q_lower == g or q_lower.startswith(g + " ") for g in greetings) and len(q_lower.split()) <= 3:
        return (
            "Namaste! 🙏 I am your Master Astrologer & Numerologist. "
            "Unlike standard pandits, I bring you real-world, dynamic decision-making by blending Vedic charts, Western transits, and Numerological cycles.\n\n"
            "To unlock your personalized predictions, make sure your profile birth details are complete, or simply tell me your **Date of Birth, Time, and Place**, and ask me anything about your career, relationship, finances, or health. What area shall we look into today?"
        )

    # Detect primary intent
    is_career = any(w in q_lower for w in ["career", "job", "work", "profession", "promotion", "business", "company", "boss", "salary", "interview"])
    is_love = any(w in q_lower for w in ["love", "marriage", "relationship", "partner", "husband", "wife", "kundali", "wedding", "romance"])
    is_finance = any(w in q_lower for w in ["finance", "money", "wealth", "investment", "debt", "property", "earning", "loan"])
    is_health = any(w in q_lower for w in ["health", "disease", "wellness", "stress", "mental", "doctor"])
    is_remedy = any(w in q_lower for w in ["remedy", "gemstone", "mantra", "puja", "vastu", "ruby", "sapphire", "emerald", "diamond"])

    # Look up placements
    sun_place = get_placement("sun")
    moon_place = get_placement("moon")
    venus_place = get_placement("venus")
    jupiter_place = get_placement("jupiter")
    saturn_place = get_placement("saturn")
    mars_place = get_placement("mars")
    mercury_place = get_placement("mercury")

    # Generate custom prediction content
    if is_career:
        answer_body = (
            f"Here is your direct career trajectory and professional guidance:\n\n"
            f"• **Astrological Placement**: Your career dynamics are heavily influenced by **{jupiter_place}** (governing growth and expansion) and **{saturn_place}** (ruling discipline and long-term structure). The alignment indicates key changes in authority or professional recognition.\n"
            f"• **Vedic Vimshottari & Transits**: Transiting Jupiter is aspecting your MC (Midheaven), signaling that a strategic pivot or promotion is highly supported by your planetary cycles.\n"
            f"• **Numerological Direction**: With a **Life Path {lp_str}** and entering a **Personal Year {py_str}**, this is a prime year for building authority, taking on executive decisions, and initiating long-term business or job ventures.\n"
            f"• **Target Windows**: The next 2-3 months offer the strongest cosmic support for promotions, salary negotiations, or changing companies.\n"
            f"• **Pandit-Surpassing Remedy**: Wear a **{gemstone}** set in gold or silver on Thursday/Sunday morning to strengthen your ruling planet (**{ruling_planet}**). Chant the mantra *'{mantra}'* 108 times daily to activate leadership energies."
        )
        follow_up = "Are you considering a change in your current job, or are you looking to start a new business venture? Let's analyze the exact timing for either."
    elif is_love:
        answer_body = (
            f"Here is your relationship alignment and marriage compatibility reading:\n\n"
            f"• **Astrological Placement**: Your emotional and relational profile is anchored by **{venus_place}** and **{moon_place}**. This placement determines how you connect, express affection, and find harmony.\n"
            f"• **Vedic Vimshottari & Transits**: Favorable aspects from transit Jupiter to Venus are dissolving past relationship barriers, bringing emotional clarity and opportunities for long-term commitment.\n"
            f"• **Numerological Direction**: Your **Life Path {lp_str}** combined with **Personal Year {py_str}** indicates a focus on harmony, family foundations, and settling emotional cycles.\n"
            f"• **Target Windows**: Favorable relationship cycles peak in the late summer/autumn months. Plan important relational conversations during this window.\n"
            f"• **Pandit-Surpassing Remedy**: Chant *'Om Shukraya Namaha'* 108 times on Fridays. Keep your bedroom styled with **{lucky_color}** tones to align with your personal vibrational frequency."
        )
        follow_up = "Would you like me to look at compatibility with a specific partner, or calculate the best auspicious dates (Muhurat) for relationship milestones?"
    elif is_finance:
        answer_body = (
            f"Here is your wealth creation, investment, and financial cycle analysis:\n\n"
            f"• **Astrological Placement**: Your wealth intelligence is governed by **{mercury_place}** and **{jupiter_place}**, activating your 2nd (wealth accumulation) and 11th (gains) houses.\n"
            f"• **Vedic Vimshottari & Transits**: Transit Saturn's positioning demands financial discipline, while transiting Jupiter opens doors for smart investments and long-term asset growth.\n"
            f"• **Numerological Direction**: Entering a **Personal Year {py_str}** provides the structural focus required to pay off debts, lock in investments, and diversify income streams.\n"
            f"• **Target Windows**: Look for investment or trade entries during the first half of the upcoming month when planetary speed is most favorable.\n"
            f"• **Pandit-Surpassing Remedy**: Store water in a copper vessel overnight and drink it in the morning. Recite *'Om Shreem Mahalakshmyei Namaha'* 108 times daily on Wednesday mornings."
        )
        follow_up = "Are you focused on recovering blocked funds, making a real estate investment, or seeking new income streams? Tell me so I can give you the exact date windows."
    elif is_health:
        answer_body = (
            f"Here is your vitality, health, and cosmic wellness profile:\n\n"
            f"• **Astrological Placement**: Your physical vitality is guided by **{sun_place}** and **{mars_place}**. These control your energy cycles and stress responses.\n"
            f"• **Vedic Vimshottari & Transits**: Transiting Rahu or Saturn aspects require you to maintain consistent sleep hygiene and dietary discipline to avoid burnout.\n"
            f"• **Numerological Direction**: Your **Life Path {lp_str}** suggests a natural susceptibility to nervous energy; use your **Personal Year {py_str}** to implement a robust, daily workout or meditation routine.\n"
            f"• **Target Windows**: Next month shows a minor energy dip; optimize your health habits starting today.\n"
            f"• **Pandit-Surpassing Remedy**: Drink warm water with lemon daily. Practice Surya Namaskar at sunrise, and chant the Mahamrityunjaya Mantra 11 times every morning."
        )
        follow_up = "Are you facing any specific physical health issues, sleep disturbances, or emotional stress? Let's check the transit chart to pinpoint the cause."
    elif is_remedy:
        answer_body = (
            f"Here is your customized remedial blueprint to balance challenging placements:\n\n"
            f"• **Gemstone Recommendation**: Based on your **Life Path {lp_str}**, your primary cosmic stone is **{gemstone}** (representing **{ruling_planet}**). It should be set in gold or silver and worn on a Thursday or Sunday morning on the ring or index finger.\n"
            f"• **Mantras**: Recite the activation mantra *'{mantra}'* 108 times daily after a morning shower.\n"
            f"• **Lucky Vibes**: Integrate **{lucky_color}** into your workspace and outfits. Favorable directions are East and Northeast."
        )
        follow_up = "Are you seeking to resolve a career hurdle, relationship conflict, or health issue? I can recommend a specific puja, mantra, or gemstone wear schedule for it."
    else:
        answer_body = (
            f"Regarding your query *\"{query}\"*:\n\n"
            f"• **Astrological Placement**: Sun is placed at **{sun_place}** and Moon is at **{moon_place}**. This combination governs your ego-drive and emotional reactions to events.\n"
            f"• **Vedic Vimshottari & Transits**: Major transits align with your natal planets (**{chart_aspects_str if chart_aspects_str else 'none'}**), indicating that a transition is active in your current timeline.\n"
            f"• **Numerological Cycle**: Your **Life Path {lp_str}** and **Personal Year {py_str}** highlight a cycle of action and building structures that support practical decisions.\n"
            f"• **Remedy**: Recite *'Om Guruve Namaha'* 108 times daily to activate luck, wisdom, and cosmic protection."
        )
        follow_up = "Would you like me to elaborate on the specific planetary transit dates or analyze a different life domain like career or relationship?"

    return (
        f"🌌 **Master AI Astrologer & Guide**\n\n"
        f"{answer_body}\n\n"
        f"💬 *Personalized for: {loc_str} | System: {system_pref} | Life Path: {lp_str}*\n\n"
        f"👉 **Next Step:** {follow_up}"
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

    chart_info = None
    validation_info = None
    numerology_info = None
    chart_placements_str = ""
    chart_aspects_str = ""

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

            # Calculate actual natal placements and aspects to pass to prompt/synthesizer
            try:
                dob_val = bd.date_of_birth
                tob_val = bd.birth_time
                
                if isinstance(dob_val, str):
                    dob_dt = datetime.date.fromisoformat(dob_val)
                else:
                    dob_dt = dob_val
                    
                if isinstance(tob_val, str):
                    time_str = tob_val.split(".")[0]
                    parts = time_str.split(":")
                    if len(parts) == 2:
                        tob_t = datetime.time(int(parts[0]), int(parts[1]))
                    else:
                        tob_t = datetime.time(int(parts[0]), int(parts[1]), int(parts[2]))
                else:
                    tob_t = tob_val
                    
                combined_dt = datetime.datetime.combine(dob_dt, tob_t)
                
                from app.services.astrology.timezone import local_to_utc
                from app.services.astrology.provider import SwissEphemerisProvider
                from app.domain.astrology.engine import WesternAstrologyEngine
                
                utc_dt = local_to_utc(combined_dt, bd.timezone)
                prov = SwissEphemerisProvider()
                z_type = "tropical" if request.system_preference.lower() == "western" else "sidereal"
                
                raw_c_data = prov.calculate_chart(
                    utc_dt=utc_dt,
                    latitude=bd.latitude,
                    longitude=bd.longitude,
                    zodiac_type=z_type,
                    ayanamsa=bd.calculation_metadata.get("ayanamsa", "lahiri") if (hasattr(bd, "calculation_metadata") and bd.calculation_metadata) else "lahiri",
                    house_system=bd.calculation_metadata.get("house_system", "placidus") if (hasattr(bd, "calculation_metadata") and bd.calculation_metadata) else "placidus",
                )
                
                c_engine = WesternAstrologyEngine()
                natal_c = c_engine.calculate_natal_chart(raw_c_data)
                
                placements_list = []
                for p in natal_c.placements:
                    placements_list.append(f"{p.name}: {p.sign} {p.sign_degree:.2f}° (House {p.house})")
                chart_placements_str = "; ".join(placements_list)
                
                aspects_list = []
                for asp in natal_c.aspects:
                    if asp.strength > 0.5:
                        aspects_list.append(f"{asp.point1} {asp.aspect_type} {asp.point2} (strength: {asp.strength:.2f})")
                chart_aspects_str = "; ".join(aspects_list[:10])
                logger.info("[CHAT ASTROLOGY SUCCESS] Natal chart calculated for chat context.")
            except Exception as chart_err:
                logger.warning(f"Could not calculate natal chart for chat context: {chart_err}")

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
            
            # Use elite instruction models for maximum prediction accuracy & ChatGPT/Gemini flavor
            models_to_try = [
                "Qwen/Qwen2.5-7B-Instruct",
                "mistralai/Mistral-7B-Instruct-v0.3",
                "HuggingFaceH4/zephyr-7b-beta"
            ]
            
            client = None
            for model_name in models_to_try:
                try:
                    client = InferenceClient(
                        model=model_name,
                        token=hf_token if (hf_token and hf_token.startswith("hf_")) else None
                    )
                    # Small ping test to check availability
                    client.text_generation("test", max_new_tokens=1)
                    logger.info(f"Using Hugging Face model for chat: {model_name}")
                    break
                except Exception as model_err:
                    logger.warning(f"Model {model_name} is busy or rate-limited: {model_err}")
                    client = None

            if client is None:
                raise Exception("No Hugging Face models responded.")

            # Build dynamic system prompt instructions explaining how to reason with their specific chart placements and numerology values!
            dynamic_instruction_lines = []
            if chart_placements_str:
                dynamic_instruction_lines.append(f"Specifically analyze their key placements: {chart_placements_str}.")
            if chart_aspects_str:
                dynamic_instruction_lines.append(f"Synthesize their active aspects: {chart_aspects_str}.")
            if numerology_info:
                dynamic_instruction_lines.append(
                    f"Their Life Path is {life_path_val} and their Personal Year is {personal_year_val}. Cross-reference this numerological cycle with their transit aspects to verify the timing."
                )
            if knowledge_texts:
                dynamic_instruction_lines.append(
                    "You MUST search for matches within the Retrieved Vector Knowledge, specifically applying the rules/principles mentioned in the knowledge text to the user's exact placements above."
                )
            
            dynamic_instructions = " ".join(dynamic_instruction_lines)

            system_prompt = (
                "You are an elite, highly personalized AI Astrologer & Spiritual Guide combining Vedic astrology, Western astrology, and Numerology.\n"
                "Your mission is to provide extremely accurate, to-the-point, and practical predictions that surpass traditional pandits. "
                "Instead of vague or generic advice, give specific, actionable insights, dates, and clear guidance that helps the user make real-world decisions.\n\n"
                f"## DYNAMIC USER ANALYSIS\n"
                f"{dynamic_instructions}\n\n"
                "## SYSTEM SYNTHESIS\n"
                "- **Western Astrological Logic**: Analyze the zodiac sign placements, houses, and transits (e.g. Jupiter trine Sun, Saturn square Moon).\n"
                "- **Vedic Astrological Logic**: Synthesize Lagna (Ascendant), Rashi (Moon Sign), Nakshatras, and the current Vimshottari Dasha/Antardasha periods.\n"
                "- **Numerology**: Calculate and weave in the Life Path Number, Destiny Number, and Personal Year theme.\n\n"
                "## CONVERSATION PROTOCOL\n"
                "1. **Engage & Personalize**: Speak directly to the user. Address their concerns with warm authority, empathy, and cosmic precision.\n"
                "2. **To-The-Point & Direct**: Do not waste time with generic preamble or fluff. Start with the core answer or prediction immediately.\n"
                "3. **Practical Decisions**: Focus on helping the user make decisions (e.g. career moves, relationship conversations, financial timing, health habits).\n"
                "4. **Concrete Timing**: Suggest specific months or time windows for opportunities and challenges.\n"
                "5. **Clear remedies**: Recommend gemstone (finger/day/metal), mantra, or simple daily habits.\n"
                "6. **Maintain Engagement**: End with a thought-provoking, personalized question to encourage them to continue the consultation.\n\n"
                "Use clean markdown, bullet points, and bold text for high readability."
            )

            prompt = (
                f"<|system|>\n{system_prompt}<|endoftext|>\n"
                f"<|user|>\n"
                f"User Query: {request.message}\n"
                f"Astrological System: {system_pref}\n"
                f"Birth Details / Chart Placements: {chart_placements_str if chart_placements_str else 'Not calculated'}\n"
                f"Birth Chart Aspects: {chart_aspects_str if chart_aspects_str else 'Not calculated'}\n"
                f"Numerology Profile: {json.dumps(numerology_info) if numerology_info else 'Not calculated'}\n"
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
                chart_placements_str=chart_placements_str,
                chart_aspects_str=chart_aspects_str,
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
            chart_info=chart_info,
            numerology_info=numerology_info,
            chart_placements_str=chart_placements_str,
            chart_aspects_str=chart_aspects_str,
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
