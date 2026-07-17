import logging
import asyncio
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

import db
import config
import vector_db

logger = logging.getLogger(__name__)

# Timeout (seconds) for the entire AI call — prevents the bot from hanging
AI_TIMEOUT_SECONDS = 15


class SQLiteChatMessageHistory(BaseChatMessageHistory):
    """Custom LangChain chat message history backed by our SQLite database."""
    
    def __init__(self, session_id: str):
        # session_id represents the user_id (as a string)
        self.session_id = session_id
        
    @property
    def messages(self) -> list[BaseMessage]:
        try:
            user_id = int(self.session_id)
            # Retrieve recent messages (DB returns DESC, we reverse it to ASC order for LangChain)
            db_messages = db.get_chat_history(user_id, limit=20)
            langchain_messages = []
            
            for msg in reversed(db_messages):
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["message"]))
                else:
                    langchain_messages.append(AIMessage(content=msg["message"]))
            return langchain_messages
        except ValueError:
            return []
            
    def add_message(self, message: BaseMessage) -> None:
        try:
            user_id = int(self.session_id)
            role = "user" if isinstance(message, HumanMessage) else "model"
            db.save_chat_message(user_id, role, message.content)
        except ValueError:
            pass
            
    def clear(self) -> None:
        try:
            user_id = int(self.session_id)
            db.clear_chat_history(user_id)
        except ValueError:
            pass


def get_catalog_context() -> str:
    """Fetches categories and products from the database and formats them as a text context block."""
    categories = db.get_categories()
    if not categories:
        return "Our shop catalog is currently empty."
        
    context = "=== AT SELECTION STORE CATALOG ===\n"
    for cat in categories:
        context += f"\n📁 Category: {cat}\n"
        products = db.get_products_by_category(cat)
        if not products:
            context += "  (No products in this category yet)\n"
        else:
            for p in products:
                context += (
                    f"  • ID #{p['id']} - Name: {p['name']}\n"
                    f"    Available Sizes: {p['sizes'] if p['sizes'] else 'Standard'}\n"
                    f"    Description: {p['description'] if p['description'] else 'No description available'}\n"
                )
    return context


def _get_system_prompt() -> str:
    """Build the system prompt with business info and dynamic catalog placeholder."""
    return (
        f"You are the friendly and professional AI Catalog Assistant for **{config.BUSINESS_NAME}** "
        f"({config.BUSINESS_SUBTITLE}), owned by **{config.OWNER_NAME}**.\n\n"
        f"Here is our business contact card info:\n"
        f"• Address: {config.BUSINESS_ADDRESS}\n"
        f"• Phone numbers: {', '.join(config.OWNER_PHONES)}\n"
        f"• Email: {', '.join(config.OWNER_EMAILS)}\n\n"
        f"Here is the list of products from our catalog that are most relevant to the customer's request:\n"
        f"{{catalog_context}}\n\n"
        f"=== CRITICAL FORMATTING RULE ===\n"
        f"ALL replies must be extremely short, simple, and formatted with a bold heading and an italicized subheading. Do not write long conversational paragraphs.\n\n"
        f"Follow these templates exactly:\n\n"
        f"For Matching Products:\n"
        f"**💎 [Product Name] (ID #[Product ID])**\n"
        f"*Category: [Category Name] | Sizes: [Sizes]*\n"
        f"Description: [A short 1-2 sentence description detailing fabric, colors, and style]\n\n"
        f"For Unrelated / Out-of-Stock Queries (e.g., 'potato'):\n"
        f"**⚠️ Unrelated Request / Not in Stock**\n"
        f"*Product category requested: [Item requested]*\n"
        f"We only deal in wholesale readymade garments. Please click '🛍️ Browse Catalog' to explore our active collection (Kids Dresses, Sharara Sets, Denim Sets, etc.).\n\n"
        f"=== ADDITIONAL INSTRUCTIONS ===\n"
        f"1. Wholesale prices are hidden. Do NOT quote specific prices. Ask them to submit an inquiry through the cart so you can review their order quantities and reply with customized pricing, or direct them to Syed Ahmer.\n"
        f"2. Keep your replies under 100 words. Be short, direct, and helpful.\n"
        f"3. LOCAL HYDERABADI DIALECT & WHOLESALE BUSINESS CONTEXT: Since our business is in Hyderabad (Dewan Dewdi/Madina market vibe), sprinkle a friendly, local Hyderabadi/Deccani Urdu vibe (Hinglish) and trade terms into your replies when customers ask about stock or orders:\n"
        f"   - Use 'Hau' (Yes), 'Nakko' (No / Don't / Not).\n"
        f"   - Use local trade terms: 'Maal' (stock/merchandise), 'Giraak' (customer), 'Joda'/'Jode' (suit sets), 'Bhao'/'Rate' (wholesale price).\n"
        f"   - Emphasize wholesale rules: 'Hum chillar me (loose retail pieces) nakko bechte, sirf set-to-set wholesale maal milta. Har design me puri gaddi (complete size set) lena padta.'\n"
        f"   - Use terms like 'Kirrak', 'Zabardast', or 'Ek number' to describe the quality and work ('Karigari' / 'Zari work').\n"
        f"   - Explain pricing: 'Bhao abhi chat me nakko pucho, pehle items cart me add karo, uske baad Syed Ahmer bhai ku confirm karo WhatsApp pe.'"
    )


# Global caches for LLM chains
_groq_chain = None
_gemini_chain = None

def get_groq_chain():
    """Lazily load and cache the Groq LangChain chain."""
    global _groq_chain
    if _groq_chain is None and config.GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                api_key=config.GROQ_API_KEY,
                temperature=0.7,
                max_retries=1,
            )
            _groq_chain = _build_chain(llm)
            logger.info("Successfully initialized and cached Groq chain.")
        except Exception as e:
            logger.error(f"Failed to initialize Groq chain: {e}", exc_info=True)
    return _groq_chain

def get_gemini_chain():
    """Lazily load and cache the Gemini LangChain chain."""
    global _gemini_chain
    if _gemini_chain is None and config.GEMINI_API_KEY and config.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=config.GEMINI_API_KEY,
                temperature=0.7,
                timeout=15,
                max_retries=1,
            )
            _gemini_chain = _build_chain(llm)
            logger.info("Successfully initialized and cached Gemini chain.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini chain: {e}", exc_info=True)
    return _gemini_chain

def is_greeting_or_general(message: str) -> bool:
    """Detects if the message is a simple greeting or general command to skip vector DB lookup latency."""
    msg = message.strip().lower()
    if len(msg) < 3:
        return True
    greetings = {"hi", "hello", "hey", "hola", "yo", "greetings", "good morning", "good afternoon", "good evening", "help", "menu", "status", "who are you", "what is this"}
    if msg in greetings:
        return True
    for word in ["hi ", "hello ", "hey "]:
        if msg.startswith(word):
            remaining = msg[len(word):].strip()
            if not remaining or len(remaining) < 3:
                return True
    return False

def _build_chain(llm):
    """Build the LangChain prompt + LLM chain with chat history."""
    system_prompt = _get_system_prompt()

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])

    chain = prompt | llm

    runnable_chain = RunnableWithMessageHistory(
        chain,
        lambda session_id: SQLiteChatMessageHistory(session_id),
        input_messages_key="input",
        history_messages_key="history"
    )

    return runnable_chain


async def _run_with_llm(runnable_chain, llm_name: str, user_id: int, user_message: str, catalog_context: str) -> str | None:
    """Run a LangChain chain with the given runnable chain, timeout, and context."""
    try:
        session_id = str(user_id)

        def _invoke():
            return runnable_chain.invoke(
                {"input": user_message, "catalog_context": catalog_context},
                config={"configurable": {"session_id": session_id}}
            )

        response = await asyncio.wait_for(
            asyncio.to_thread(_invoke),
            timeout=AI_TIMEOUT_SECONDS
        )

        logger.info(f"[{llm_name}] Response generated successfully for user {user_id}")
        return response.content

    except asyncio.TimeoutError:
        logger.warning(f"[{llm_name}] Timed out after {AI_TIMEOUT_SECONDS}s for user {user_id}")
        return None
    except Exception as e:
        logger.error(f"[{llm_name}] Error: {e}", exc_info=True)
        return None


async def ask_ai_agent(user_id: int, user_message: str) -> str | None:
    """Orchestrates the AI agent flow for a user message.
    Uses Groq (fast, free) as primary, Gemini as fallback.
    Returns the AI response, or a fallback message if all fail.
    """
    # 1. Skip vector database search for simple greetings/general queries to reduce latency
    if is_greeting_or_general(user_message):
        logger.info(f"Skipping vector search for greeting/general message: '{user_message[:30]}'")
        catalog_context = get_catalog_context()
    else:
        # Fetch relevant products semantically matching the user message
        logger.info(f"Searching vector DB for user message: {user_message[:50]}...")
        matched_products = vector_db.search_catalog_semantic(user_message, k=4)
        
        if matched_products:
            catalog_context = "=== RELEVANT PRODUCTS ===\n"
            for p in matched_products:
                catalog_context += (
                    f"  • ID #{p['id']} - Name: {p['name']}\n"
                    f"    Category: {p['category']}\n"
                    f"    Available Sizes: {p['sizes'] if p['sizes'] else 'Standard'}\n"
                    f"    Description: {p['description'] if p['description'] else 'No description available'}\n"
                )
        else:
            # Fallback to general catalog summary context
            catalog_context = get_catalog_context()

    # ===== PRIMARY: Groq (Llama 3.3 70B — fast & free) =====
    groq_chain = get_groq_chain()
    if groq_chain:
        logger.info(f"[Groq] Processing message from user {user_id}...")
        result = await _run_with_llm(groq_chain, "Groq", user_id, user_message, catalog_context)
        if result:
            return result
        logger.warning("[Groq] Failed, falling back to Gemini...")

    # ===== FALLBACK: Google Gemini =====
    gemini_chain = get_gemini_chain()
    if gemini_chain:
        logger.info(f"[Gemini] Fallback: Processing message from user {user_id}...")
        result = await _run_with_llm(gemini_chain, "Gemini", user_id, user_message, catalog_context)
        if result:
            return result

    # ===== ALL FAILED =====
    if not config.GROQ_API_KEY and (not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE"):
        logger.warning("No AI API keys configured.")
        return None

    return (
        "🙏 I'm sorry, I couldn't process your message right now.\n\n"
        "Please use the menu buttons below to browse our catalog, "
        "or try again in a moment!"
    )
