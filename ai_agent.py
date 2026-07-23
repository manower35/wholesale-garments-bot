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

AI_TIMEOUT_SECONDS = 15

class SQLiteChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str):
        self.session_id = session_id
        
    @property
    def messages(self) -> list[BaseMessage]:
        try:
            user_id = int(self.session_id)
            db_messages = db.get_chat_history(user_id, limit=6)
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
    return (
        f"You are the friendly wholesale AI Assistant for **{config.BUSINESS_NAME}** "
        f"({config.BUSINESS_SUBTITLE}), owned by **{config.OWNER_NAME}**.\n\n"
        f"Business contact info:\n"
        f"• Address: {config.BUSINESS_ADDRESS}\n"
        f"• Phone numbers: {', '.join(config.OWNER_PHONES)}\n\n"
        f"Relevant products catalog:\n"
        f"{{catalog_context}}\n\n"
        f"=== CRITICAL INSTRUCTIONS ===\n"
        f"1. Keep all replies VERY SHORT, simple, and polite (max 2-3 lines).\n"
        f"2. Never say 'Photo Inquiry Received' unless customer sent a photo. If customer asks about items or categories, tell them we have Kids Dresses, Nightwear, Sharara Suits, and Girls Denim Sets and ask them to type a category name to see photos.\n"
        f"3. For address/location queries, give: {config.BUSINESS_ADDRESS}\n"
        f"4. For owner contact: {config.OWNER_PHONES[0]}\n"
    )

_groq_chain = None
_gemini_chain = None

def get_groq_chain():
    global _groq_chain
    if _groq_chain is None and config.GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                api_key=config.GROQ_API_KEY,
                temperature=0.6,
                max_tokens=150,
                max_retries=1,
            )
            _groq_chain = _build_chain(llm)
            logger.info("Successfully initialized and cached Groq chain.")
        except Exception as e:
            logger.error(f"Failed to initialize Groq chain: {e}", exc_info=True)
    return _groq_chain

def get_gemini_chain():
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
    if is_greeting_or_general(user_message):
        catalog_context = get_catalog_context()
    else:
        matched_products = vector_db.search_catalog_semantic(user_message, k=2)
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
            catalog_context = get_catalog_context()

    groq_chain = get_groq_chain()
    if groq_chain:
        result = await _run_with_llm(groq_chain, "Groq", user_id, user_message, catalog_context)
        if result:
            return result

    gemini_chain = get_gemini_chain()
    if gemini_chain:
        result = await _run_with_llm(gemini_chain, "Gemini", user_id, user_message, catalog_context)
        if result:
            return result

    if not config.GROQ_API_KEY and (not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE"):
        return None

    return f"🙏 Shukriya! {config.BUSINESS_NAME} mein aapka swagat hai.\n📞 Call: {config.OWNER_PHONES[0]}"
