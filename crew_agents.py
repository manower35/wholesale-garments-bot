"""
CrewAI Multi-Agent System for AT SELECTION Wholesale Garments Bot.

This module defines 4 specialized AI agents that collaborate as a team:
  1. Sales Agent     → Customer interaction, recommendations, inquiry handling
  2. Catalog Agent   → Product search, matching by size/style/category
  3. Report Agent    → Daily inquiry summaries for admin
  4. Follow-up Agent → Customer follow-up reminders

All agents are powered by Google Gemini (free tier).
"""

import os
import json
import logging
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import Field
import config
import db

logger = logging.getLogger(__name__)

# ===========================
# LLM SETUP (Google Gemini)
# ===========================

def get_gemini_llm():
    """Initialize the Gemini LLM for CrewAI agents."""
    return LLM(
        model="gemini/gemini-2.0-flash",
        api_key=config.GEMINI_API_KEY,
        temperature=0.7
    )

# ===========================
# CUSTOM TOOLS
# ===========================

class SearchCatalogTool(BaseTool):
    """Tool to search the product catalog database."""
    name: str = "search_catalog"
    description: str = (
        "Search the AT SELECTION product catalog. "
        "Input should be a search keyword like 'frock', 'sharara', 'kids dress', 'size 36', etc. "
        "Returns matching products with their details."
    )

    def _run(self, query: str) -> str:
        """Execute the catalog search."""
        results = db.search_products(query)
        if not results:
            # If direct search fails, try getting all products and filtering
            categories = db.get_categories()
            all_products = []
            for cat in categories:
                products = db.get_products_by_category(cat)
                all_products.extend(products)
            
            # Simple keyword matching
            query_lower = query.lower()
            results = [
                p for p in all_products
                if query_lower in p['name'].lower()
                or query_lower in (p['description'] or '').lower()
                or query_lower in (p['sizes'] or '').lower()
                or query_lower in p['category'].lower()
            ]

        if not results:
            return "No products found matching the search query."

        output = f"Found {len(results)} product(s):\n\n"
        for p in results:
            output += (
                f"• Product: {p['name']}\n"
                f"  Category: {p['category']}\n"
                f"  Sizes: {p['sizes'] or 'Standard'}\n"
                f"  Description: {p['description'] or 'No description'}\n\n"
            )
        return output


class GetAllCatalogTool(BaseTool):
    """Tool to get the full product catalog."""
    name: str = "get_full_catalog"
    description: str = (
        "Get the complete AT SELECTION product catalog with all categories and products. "
        "Use this when you need an overview of everything available in the store."
    )

    def _run(self, query: str = "") -> str:
        """Fetch the entire catalog."""
        categories = db.get_categories()
        if not categories:
            return "The catalog is currently empty."

        output = "=== AT SELECTION FULL CATALOG ===\n\n"
        for cat in categories:
            output += f"📁 Category: {cat}\n"
            products = db.get_products_by_category(cat)
            if not products:
                output += "  (No products in this category)\n\n"
            else:
                for p in products:
                    output += (
                        f"  • {p['name']}\n"
                        f"    Sizes: {p['sizes'] or 'Standard'}\n"
                        f"    Description: {p['description'] or 'N/A'}\n\n"
                    )
        return output


class GetPendingInquiriesTool(BaseTool):
    """Tool to fetch pending customer inquiries."""
    name: str = "get_pending_inquiries"
    description: str = (
        "Get all pending customer inquiries from the database. "
        "Returns inquiry details including customer name, phone, items, and date."
    )

    def _run(self, query: str = "") -> str:
        """Fetch pending inquiries."""
        try:
            with db.db_session() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, customer_name, customer_phone, items_json, status, created_at "
                    "FROM inquiries ORDER BY created_at DESC LIMIT 20"
                )
                rows = cursor.fetchall()

            if not rows:
                return "No inquiries found in the system."

            output = f"Found {len(rows)} inquiry(ies):\n\n"
            for row in rows:
                items = json.loads(row['items_json'])
                items_text = ", ".join(
                    f"{item['name']} (Sizes: {item.get('sizes', 'N/A')}) x {item.get('quantity', 1)}"
                    for item in items
                )
                output += (
                    f"• Inquiry #{row['id']} — Status: {row['status'].upper()}\n"
                    f"  Customer: {row['customer_name']} | Phone: {row['customer_phone']}\n"
                    f"  Items: {items_text}\n"
                    f"  Date: {row['created_at']}\n\n"
                )
            return output
        except Exception as e:
            return f"Error fetching inquiries: {str(e)}"


# ===========================
# AGENT DEFINITIONS
# ===========================

def create_sales_agent(llm):
    """Create the Sales Agent — handles customer conversations."""
    return Agent(
        role="Senior Sales Executive",
        goal=(
            "Help wholesale garment buyers find the right products from AT SELECTION catalog. "
            "Provide helpful product recommendations based on what the customer is looking for. "
            "Guide them to use the Browse Catalog button or Search Products feature. "
            "NEVER mention or quote any prices — direct customers to submit an inquiry for pricing."
        ),
        backstory=(
            f"You are the friendly and professional AI Sales Executive for {config.BUSINESS_NAME} "
            f"({config.BUSINESS_SUBTITLE}), owned by {config.OWNER_NAME}. "
            f"Located at: {config.BUSINESS_ADDRESS}. "
            f"Business Hours: {config.BUSINESS_HOURS}. "
            f"Contact: {', '.join(config.OWNER_PHONES)}. "
            "You have years of experience in the wholesale garment trade in Hyderabad. "
            "You know fabrics, sizing, and trends for kids and women's ethnic wear. "
            "You are talking to customers on Telegram. Keep replies concise (under 3 paragraphs). "
            "Use bold formatting and lists for clarity. "
            "IMPORTANT: Never share or discuss prices. For pricing, ask customers to submit an inquiry."
        ),
        llm=llm,
        tools=[SearchCatalogTool(), GetAllCatalogTool()],
        verbose=False,
        allow_delegation=True,
        max_iter=3
    )


def create_catalog_agent(llm):
    """Create the Catalog Agent — specializes in product search and matching."""
    return Agent(
        role="Catalog Specialist",
        goal=(
            "Search the AT SELECTION product catalog database to find the best matching products "
            "for a customer query. Match by garment type, size, style, or category. "
            "Return detailed product information without prices."
        ),
        backstory=(
            "You are an expert catalog specialist for AT SELECTION wholesale garment store. "
            "You know every product in the inventory — kids dresses, frocks, gowns, sharara sets, "
            "and ethnic wear. When the Sales Agent asks you to find products, you search "
            "the database efficiently and return accurate results. "
            "You understand Indian garment sizing (22-40), age groups, and styles."
        ),
        llm=llm,
        tools=[SearchCatalogTool(), GetAllCatalogTool()],
        verbose=False,
        max_iter=3
    )


def create_report_agent(llm):
    """Create the Report Agent — generates business summaries."""
    return Agent(
        role="Business Report Analyst",
        goal=(
            "Generate clear, concise business reports summarizing customer inquiries, "
            "popular products, and daily activity for the AT SELECTION store owner."
        ),
        backstory=(
            "You are the Business Report Analyst for AT SELECTION. "
            "You compile inquiry data into easy-to-read summaries that help "
            "the store owner understand their business performance at a glance. "
            "Your reports are formatted with emojis, bold text, and clear sections."
        ),
        llm=llm,
        tools=[GetPendingInquiriesTool(), GetAllCatalogTool()],
        verbose=False,
        max_iter=3
    )


def create_followup_agent(llm):
    """Create the Follow-up Agent — tracks pending inquiries for reminders."""
    return Agent(
        role="Customer Follow-up Coordinator",
        goal=(
            "Review pending customer inquiries and generate follow-up messages "
            "to remind customers about their inquiries or suggest similar products."
        ),
        backstory=(
            "You are the Follow-up Coordinator for AT SELECTION. "
            "You monitor pending inquiries and compose polite, friendly follow-up messages "
            "that encourage customers to complete their orders or visit the shop. "
            "Your tone is warm and helpful, never pushy."
        ),
        llm=llm,
        tools=[GetPendingInquiriesTool()],
        verbose=False,
        max_iter=3
    )


# ===========================
# CREW EXECUTION FUNCTIONS
# ===========================

async def run_sales_crew(user_message: str, user_id: int) -> str:
    """
    Run the Sales + Catalog crew to handle a customer message.
    Returns the AI response string.
    """
    try:
        llm = get_gemini_llm()
        sales_agent = create_sales_agent(llm)
        catalog_agent = create_catalog_agent(llm)

        # Load recent chat history for context
        chat_history = db.get_chat_history(user_id, limit=6)
        history_text = ""
        if chat_history:
            history_text = "Recent conversation history:\n"
            for msg in chat_history:
                role_label = "Customer" if msg['role'] == 'user' else "You (AI)"
                history_text += f"  {role_label}: {msg['message']}\n"
            history_text += "\n"

        # Define the catalog search task
        catalog_task = Task(
            description=(
                f"Search the AT SELECTION product catalog for products related to this "
                f"customer message: \"{user_message}\"\n"
                f"Find all relevant matching products by name, category, size, or description. "
                f"If the message is a general greeting or question, get the full catalog overview instead."
            ),
            expected_output="A list of matching products with their names, categories, sizes, and descriptions. No prices.",
            agent=catalog_agent
        )

        # Define the sales response task
        sales_task = Task(
            description=(
                f"You are chatting with a wholesale garment buyer (Telegram user #{user_id}) on Telegram.\n\n"
                f"{history_text}"
                f"The customer's latest message is: \"{user_message}\"\n\n"
                f"Using the catalog search results from your colleague, compose a helpful, "
                f"friendly response. Keep it concise (max 3 short paragraphs). "
                f"Use bold (**text**) and bullet points for product details. "
                f"NEVER mention or quote any prices — tell them to submit an inquiry for custom pricing. "
                f"If they want to browse or buy, tell them to click the '🛍️ Browse Catalog' or '🛒 View Cart/Inquiry' buttons below."
            ),
            expected_output=(
                "A friendly, concise Telegram message (max 3 paragraphs) with product recommendations. "
                "Formatted with bold text and bullet points. No prices mentioned."
            ),
            agent=sales_agent,
            context=[catalog_task]
        )

        # Assemble and run the crew
        crew = Crew(
            agents=[catalog_agent, sales_agent],
            tasks=[catalog_task, sales_task],
            process=Process.sequential,
            verbose=False
        )

        # Run synchronously (CrewAI kickoff is sync)
        import asyncio
        result = await asyncio.to_thread(crew.kickoff)

        response_text = str(result)

        # Save to chat history
        db.save_chat_message(user_id, "user", user_message)
        db.save_chat_message(user_id, "model", response_text)

        return response_text

    except Exception as e:
        logger.error(f"CrewAI Sales Crew error: {e}", exc_info=True)
        return None


async def run_report_crew() -> str:
    """
    Run the Report Agent crew to generate a daily business summary.
    Returns the formatted report string.
    """
    try:
        llm = get_gemini_llm()
        report_agent = create_report_agent(llm)

        report_task = Task(
            description=(
                "Generate a daily business summary report for AT SELECTION wholesale garment store. "
                "Include:\n"
                "1. Total number of inquiries (pending vs completed)\n"
                "2. List of recent inquiries with customer names and items\n"
                "3. Most popular product categories\n"
                "4. A brief recommendation for the store owner\n\n"
                "Format the report with emojis, bold text, and clear sections for Telegram display."
            ),
            expected_output=(
                "A well-formatted daily business report with sections for inquiry summary, "
                "popular products, and recommendations. Uses Telegram-compatible Markdown formatting."
            ),
            agent=report_agent
        )

        crew = Crew(
            agents=[report_agent],
            tasks=[report_task],
            process=Process.sequential,
            verbose=False
        )

        import asyncio
        result = await asyncio.to_thread(crew.kickoff)
        return str(result)

    except Exception as e:
        logger.error(f"CrewAI Report Crew error: {e}", exc_info=True)
        return "❌ Failed to generate report. Please try again later."


async def run_followup_crew() -> str:
    """
    Run the Follow-up Agent crew to generate follow-up messages for pending inquiries.
    Returns the follow-up suggestions.
    """
    try:
        llm = get_gemini_llm()
        followup_agent = create_followup_agent(llm)

        followup_task = Task(
            description=(
                "Review all pending customer inquiries for AT SELECTION store. "
                "For each pending inquiry, compose a short, friendly follow-up message "
                "that can be sent to the customer via Telegram. "
                "The message should remind them about their inquiry and offer assistance. "
                "Keep each message under 3 sentences."
            ),
            expected_output=(
                "A list of follow-up messages, one per pending inquiry, "
                "with the customer name and suggested message."
            ),
            agent=followup_agent
        )

        crew = Crew(
            agents=[followup_agent],
            tasks=[followup_task],
            process=Process.sequential,
            verbose=False
        )

        import asyncio
        result = await asyncio.to_thread(crew.kickoff)
        return str(result)

    except Exception as e:
        logger.error(f"CrewAI Follow-up Crew error: {e}", exc_info=True)
        return "❌ Failed to generate follow-up messages."
