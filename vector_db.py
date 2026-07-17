import os
import shutil
import logging
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_core.documents import Document
import config
import db

logger = logging.getLogger(__name__)

FAISS_INDEX_DIR = os.path.join(os.getcwd(), "faiss_index")

_embeddings = None
_faiss_index = None

def get_embeddings():
    """Initialize the Embeddings client (Hugging Face if key is available, else Google Gemini)."""
    global _embeddings
    if _embeddings is None:
        if config.HUGGINGFACE_API_KEY:
            logger.info("Initializing Hugging Face serverless embeddings (sentence-transformers/all-MiniLM-L6-v2)...")
            _embeddings = HuggingFaceInferenceAPIEmbeddings(
                api_key=config.HUGGINGFACE_API_KEY,
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        else:
            logger.info("Initializing Google Gemini GenAI embeddings...")
            _embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=config.GEMINI_API_KEY
            )
    return _embeddings

def format_product_doc(product: dict) -> str:
    """Format product dict into a descriptive text block for indexing."""
    return (
        f"Product Name: {product['name']}\n"
        f"Category: {product['category']}\n"
        f"Sizes: {product['sizes'] if product['sizes'] else 'Standard'}\n"
        f"Description: {product['description'] if product['description'] else 'No description available'}\n"
        f"Price: Rs. {product['price']}"
    )

def load_or_create_index():
    """Loads existing FAISS index from disk, or builds one from scratch if none exists."""
    global _faiss_index
    if _faiss_index is not None:
        return _faiss_index
        
    embeddings = get_embeddings()
    
    # Check if index exists on disk
    if os.path.exists(FAISS_INDEX_DIR) and os.path.exists(os.path.join(FAISS_INDEX_DIR, "index.faiss")):
        try:
            logger.info("Loading existing FAISS vector database from disk...")
            _faiss_index = FAISS.load_local(FAISS_INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
            return _faiss_index
        except Exception as e:
            logger.error(f"Failed to load FAISS index from disk: {e}. Rebuilding...")
            
    # Build from scratch
    _faiss_index = rebuild_index()
    return _faiss_index

def rebuild_index():
    """Rebuilds the entire FAISS index from all products in SQLite."""
    global _faiss_index
    logger.info("Rebuilding FAISS index from SQLite...")
    
    # Retrieve all products from SQLite
    categories = db.get_categories()
    products = []
    for cat in categories:
        products.extend(db.get_products_by_category(cat))
        
    if not products:
        logger.info("No products found in SQLite to index.")
        _faiss_index = None
        return None

    docs = []
    for p in products:
        text = format_product_doc(p)
        # Store product dict in metadata for easy extraction during search
        docs.append(Document(page_content=text, metadata={"product_id": p["id"]}))

    try:
        embeddings = get_embeddings()
        db_index = FAISS.from_documents(docs, embeddings)
        
        # Save to disk
        if os.path.exists(FAISS_INDEX_DIR):
            shutil.rmtree(FAISS_INDEX_DIR)
        db_index.save_local(FAISS_INDEX_DIR)
        logger.info("Successfully rebuilt and saved FAISS index.")
        _faiss_index = db_index
        return db_index
    except Exception as e:
        logger.error(f"Failed to build FAISS index (probably 429 quota exhaustion): {e}")
        return None

def search_catalog_semantic(query: str, k: int = 3) -> list[dict]:
    """Performs semantic search on the product catalog.
    Returns a list of matching product dictionaries from SQLite.
    """
    db_index = load_or_create_index()
    if not db_index:
        logger.warning("Vector index is unavailable. Falling back to empty results.")
        return []

    try:
        results = db_index.similarity_search(query, k=k)
        products = []
        for doc in results:
            product_id = doc.metadata.get("product_id")
            if product_id:
                product = db.get_product(product_id)
                if product:
                    products.append(product)
        return products
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return []

def add_product_to_vector_db(product: dict):
    """Adds a single product to the local FAISS index dynamically."""
    try:
        db_index = load_or_create_index()
        text = format_product_doc(product)
        doc = Document(page_content=text, metadata={"product_id": product["id"]})
        
        if db_index:
            db_index.add_documents([doc])
            db_index.save_local(FAISS_INDEX_DIR)
            logger.info(f"Dynamically added product #{product['id']} to FAISS index.")
        else:
            # Index doesn't exist yet, try to build it
            rebuild_index()
    except Exception as e:
        logger.error(f"Failed to dynamically add product #{product['id']} to FAISS: {e}")

def delete_product_from_vector_db(product_id: int):
    """Removes a product from the FAISS index."""
    # Since FAISS doesn't support easy dynamic deletion in older community versions
    # without rebuilding or maintaining ID maps, the most robust way for a small catalog
    # is to simply rebuild the index from scratch.
    try:
        rebuild_index()
        logger.info(f"Rebuilt vector DB after deleting product #{product_id}.")
    except Exception as e:
        logger.error(f"Failed to update FAISS index after deletion of product #{product_id}: {e}")
