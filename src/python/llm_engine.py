import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

class DocumentBrain:
    def __init__(self):
        # 🔑 ENTER YOUR API KEY HERE
        self.api_key = "AIzaSyB24EcEbSo44dJaUMuHsZWPDwJWGMLV25Y"
        
        # We use temperature=0.0 for maximum precision (less creativity, more accuracy)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.api_key,
            temperature=0.0 
        )
    
    def analyze_document(self, text_content):
        
        # --- THE ENTERPRISE PROMPT ---
        # This prompt forces the AI to act as a Senior Data Analyst.
        template = """
        You are a Senior Document Intelligence Engine for Xentro AI.
        Your goal is to extract structured, actionable data from business documents with 100% precision.

        --- PHASE 1: CLASSIFICATION ---
        Determine the document type from these categories:
        [INVOICE, RECEIPT, CONTRACT, BANK_STATEMENT, RESUME, PURCHASE_ORDER, TECHNICAL_REPORT, OTHER]

        --- PHASE 2: EXTRACTION RULES ---
        Based on the classified type, extract the following specific fields:

        A. IF INVOICE / RECEIPT:
           - Vendor Name, Invoice Number, Invoice Date, Due Date
           - Subtotal, Tax Amount, Total Amount (with currency)
           - Line Items (Summarized list of what was bought)
        
        B. IF CONTRACT / LEGAL:
           - Contract Title, Effective Date, Expiration Date
           - Parties Involved (List of companies/people)
           - Contract Value (if mentioned)
           - Key Clauses (Liability, Termination, Payment Terms)

        C. IF BANK STATEMENT / FINANCIAL:
           - Bank Name, Account Holder, Period (Start-End)
           - Opening Balance, Closing Balance
           - Total Deposits, Total Withdrawals

        D. IF RESUME / CV:
           - Candidate Name, Email, Phone
           - Top 5 Skills, Years of Experience
           - Most Recent Job Title & Company

        E. IF OTHER:
           - Author/Sender, Subject/Title, Key Topics, Dates mentioned

        --- PHASE 3: METADATA ---
        - Language: Detect the document language (en, de, fr, etc.)
        - Confidence: Rate your extraction confidence (0-100%).
        - Summary: Write a professional executive summary (2 sentences).

        --- INPUT TEXT ---
        {text}

        --- REQUIRED OUTPUT FORMAT (Strict JSON) ---
        {{
            "type": "CATEGORY_NAME",
            "language": "ISO_CODE",
            "confidence_score": 95,
            "vendor": "String or null",
            "date": "YYYY-MM-DD or null",
            "total_amount": "String or null",
            "currency": "String or null",
            "parties": ["Name 1", "Name 2"],
            "specific_data": {{
                "invoice_number": "...",
                "tax": "...",
                "skills": "...",
                "clauses": "..."
            }},
            "summary": "Executive summary string..."
        }}
        """
        
        prompt = PromptTemplate.from_template(template)
        
        # Huge context window allows analyzing full 50-page contracts
        safe_text = text_content[:60000] 
        
        formatted_prompt = prompt.format(text=safe_text)
        
        try:
            response = self.llm.invoke(formatted_prompt)
            clean_content = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_content)
            
        except Exception as e:
            # Fallback for errors
            return {
                "type": "ERROR",
                "summary": f"Deep analysis failed: {str(e)}",
                "vendor": "Unknown",
                "total_amount": "0.00"
            }
    

    # ... inside class DocumentBrain ...
    def chat_with_documents(self, context_text, user_question):
            template = """
            You are the Xentro AI Knowledge Assistant.
            Answer the question based on the provided Context.
            
            RULES:
            1. Use facts from the Context strictly (Totals, Dates, Names).
            2. **ALLOW INFERENCE:** If the user asks for a Country/Region and only a City is found (e.g., Lahore, London), you MAY infer the Country.
            3. **DATE CHECK:** If a date seems to be in the future (e.g., 2029), check if it's likely an OCR error for a current year (e.g., 2025) and mention it.
            4. If the answer is completely missing, say "Information not found."

            --- CONTEXT ---
            {context}
            
            --- QUESTION ---
            {question}
            """
            prompt = PromptTemplate.from_template(template)
            formatted_prompt = prompt.format(context=context_text, question=user_question)
            
            try:
                response = self.llm.invoke(formatted_prompt)
                return response.content.strip()
            except Exception as e:
                return f"Error generating answer: {str(e)}"
    

    # ... inside DocumentBrain class ...

    def audit_document(self, current_doc_text, historical_context):
        """
        Compares the current document against history to find anomalies.
        """
        template = """
        You are a Forensic Accountant AI.
        Compare the CURRENT INVOICE against the HISTORICAL DATA for this vendor.

        --- CURRENT INVOICE CONTENT ---
        {current}

        --- VENDOR HISTORY ---
        {history}

        TASK:
        1. Check for Price Anomalies (Is this bill significantly higher than average?).
        2. Check for Risk (Does the layout or terms look suspicious compared to history?).
        3. If no history exists, mark as "New Vendor Risk".

        OUTPUT JSON ONLY:
        {{
            "risk_score": 85,
            "risk_level": "HIGH / MEDIUM / LOW",
            "flags": ["Flag 1", "Flag 2"],
            "recommendation": "Approve / Reject / Audit"
        }}
        """
        
        prompt = PromptTemplate.from_template(template)
        # Limit text to avoid token limits
        safe_current = current_doc_text[:10000]
        safe_history = str(historical_context)[:5000]
        
        formatted_prompt = prompt.format(current=safe_current, history=safe_history)
        
        try:
            response = self.llm.invoke(formatted_prompt)
            clean_content = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_content)
        except Exception as e:
            return {
                "risk_level": "ERROR",
                "flags": [f"Audit failed: {str(e)}"],
                "recommendation": "Manual Review"
            }
    def redact_sensitive_data(self, extracted_json):
        """
        Takes the extracted data and creates a GDPR-compliant 'Public Version'.
        Replaces PII (Names, Phones, IDs) with [REDACTED].
        """
        template = """
        You are a GDPR Compliance Officer.
        Analyze the JSON data below and REDACT all Personally Identifiable Information (PII).

        RULES:
        1. Replace specific Person Names with "[REDACTED_NAME]".
        2. Replace Phone Numbers/Emails with "[REDACTED_CONTACT]".
        3. Replace IBANs/Account Numbers with "[REDACTED_BANK]".
        4. KEEP the Vendor Name, Dates, and Totals visible (Business data is public).
        5. Return the modified JSON structure exactly.

        --- INPUT JSON ---
        {json_data}
        """
        
        prompt = PromptTemplate.from_template(template)
        formatted_prompt = prompt.format(json_data=json.dumps(extracted_json))
        
        try:
            response = self.llm.invoke(formatted_prompt)
            clean_content = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_content)
        except Exception as e:
            return {"error": f"Redaction failed: {str(e)}"}
    
    def verify_math(self, text_content):
            """
            Performs an arithmetic audit on the document.
            """
            # --- STEP 1: CLEAN THE TEXT ---
            # Replace massive whitespace gaps with a single space to help the AI
            # "Subtotal:          $100" -> "Subtotal: $100"
            import re
            clean_text = re.sub(r'\s+', ' ', text_content).strip()
            
            template = """
            You are a Forensic Math Auditor.
            Analyze the document text to find financial components and verify the arithmetic.

            CRITICAL RULES:
            1. The text is raw extraction. IGNORE formatting artifacts.
            2. Find values for: Subtotal, Discount, Tax, Shipping, Total.
            3. If a number has a comma (e.g. "4,941.60"), read it as 4941.60.
            4. Discount is a NEGATIVE value (subtract it).
            5. Shipping and Tax are POSITIVE values (add them).

            TASK:
            1. Extract the financial values (Use 0.00 if not found).
            2. Calculate: Expected = Subtotal - Discount + Tax + Shipping.
            3. Compare Expected vs Found Total.

            INPUT TEXT:
            {text}

            OUTPUT JSON ONLY:
            {{
                "found_subtotal": 0.00,
                "found_discount": 0.00,
                "found_tax": 0.00,
                "found_shipping": 0.00,
                "found_total": 0.00,
                "calculated_total": 0.00,
                "is_math_correct": true/false,
                "explanation": "Brief summary of the math check."
            }}
            """
            
            prompt = PromptTemplate.from_template(template)
            # Send the CLEANED text
            formatted_prompt = prompt.format(text=clean_text[:6000])
            
            try:
                response = self.llm.invoke(formatted_prompt)
                clean_content = response.content.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_content)
            except Exception as e:
                return {
                    "is_math_correct": False, 
                    "explanation": f"Audit failed: {str(e)}",
                    "found_total": 0.00
                }