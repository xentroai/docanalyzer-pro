import chromadb
from models import SessionLocal, Document
import json
import os
import uuid

class DatabaseEngine:
    def __init__(self):
        # 1. SQL Client (For Metadata/History)
        self.sql_db = SessionLocal()
        
        # 2. Vector Client (For Semantic Search)
        # Using a persistent path so it remembers vectors too
        self.chroma_client = chromadb.PersistentClient(path="./data/xentro_vectors")
        self.vector_col = self.chroma_client.get_or_create_collection("docs")

    def save_document(self, filename, filepath, text_content, ai_data, cpp_data, file_hash=None):
        """
        Saves to BOTH SQL (Record keeping) and Chroma (Search).
        """
        try:
            # A. Save to SQL (The System of Record)
            new_doc = Document(
                id=str(uuid.uuid4()),
                filename=filename,
                file_path=filepath,
                file_type=os.path.splitext(filename)[1].lower(),
                file_size=os.path.getsize(filepath) if os.path.exists(filepath) else 0,
                text_content=text_content,
                ai_summary=ai_data.get('summary', 'No summary provided.'),
                metadata_json=ai_data,
                cpp_metrics=cpp_data,
                file_hash=file_hash
            )
            self.sql_db.add(new_doc)
            self.sql_db.commit()
            
            # B. Save to Vector DB (The Search Engine)
            # We strip metadata to simple strings for Chroma compatibility
            simple_meta = {
                "filename": filename,
                "doc_id": new_doc.id,
                "vendor": str(ai_data.get('vendor', 'Unknown')),
                "total": str(ai_data.get('total_amount', '0'))
            }
            
            self.vector_col.add(
                documents=[text_content],
                metadatas=[simple_meta],
                ids=[new_doc.id]
            )
            
            return new_doc.id
        except Exception as e:
            self.sql_db.rollback()
            raise e
        finally:
            self.sql_db.close()

    def get_recent_documents(self, limit=5):
        """Returns list of most recently processed files from SQL"""
        docs = self.sql_db.query(Document).order_by(Document.processed_at.desc()).limit(limit).all()
        self.sql_db.close()
        return docs
        
    def query_similar_docs(self, query_text, filename_filter=None, n_results=3):
        """Semantic search in ChromaDB"""
        where_filter = None
        if filename_filter:
            where_filter = {"filename": filename_filter}
            
        results = self.vector_col.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter
        )
        return results

    def check_file_hash(self, file_hash):
        """
        Checks if a file with this hash already exists.
        Returns the Document object if found, else None.
        """
        return self.sql_db.query(Document).filter(Document.file_hash == file_hash).first()

    def query_global_context(self, query_text, n_results=10):
        """
        Searches the ENTIRE Knowledge Base (All Vendors, All Dates).
        Used for 'Cross-Document' intelligence.
        """
        # No 'where' filter = Search everything in the vector store
        results = self.vector_col.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results


    def get_vendor_history(self, vendor_name, exclude_filename=None):
        """
        Fetches past invoices using NORMALIZED MATCHING (Ignores spaces/case/symbols).
        """
        import re
        
        # Helper: "Super Store Inc." -> "superstore"
        def normalize(text):
            if not text: return ""
            # Remove all non-alphanumeric chars and convert to lower
            return re.sub(r'[^a-z0-9]', '', str(text).lower())

        target_slug = normalize(vendor_name)
        # If the vendor name is too short (e.g. "A"), don't fuzzy match to avoid garbage results
        if len(target_slug) < 3: return []

        # Fetch recent docs
        all_docs = self.sql_db.query(Document).order_by(Document.processed_at.desc()).limit(100).all()
        
        history = []
        for doc in all_docs:
            if exclude_filename and doc.filename == exclude_filename:
                continue
                
            stored_vendor = doc.metadata_json.get('vendor', '')
            stored_slug = normalize(stored_vendor)
            
            # LOGIC: Check if one contains the other
            # e.g. target="superstore", stored="superstoreinc" -> Match!
            if target_slug in stored_slug or stored_slug in target_slug:
                history.append({
                    "date": doc.metadata_json.get('date', 'Unknown'),
                    "total": doc.metadata_json.get('total_amount', '0'),
                    "vendor_name": stored_vendor, # Return original name for context
                    "filename": doc.filename
                })
        
        return history[:10]
    
    def get_all_vendors(self):
        """
        Returns a frequency map of all vendors in the database.
        Used for the 'Database Inspector' UI.
        """
        # Query all documents
        all_docs = self.sql_db.query(Document).all()
        
        # Tally up the vendors
        vendor_counts = {}
        for d in all_docs:
            # Extract vendor from the JSON blob
            v = d.metadata_json.get('vendor', 'Unknown')
            vendor_counts[v] = vendor_counts.get(v, 0) + 1
            
        return vendor_counts