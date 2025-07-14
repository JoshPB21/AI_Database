import PyPDF2
import sqlite3
from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv
import json
import re

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def clean_json_string(json_string):
    """Remove trailing commas from JSON string to make it valid."""
    # Remove trailing commas in arrays
    json_string = re.sub(r',\s*]', ']', json_string)
    # Remove trailing commas in objects
    json_string = re.sub(r',\s*}', '}', json_string)
    return json_string

def analyze_pdf_content(text):
    """Use OpenAI to extract title, source, categories, subtopic, author, tags, and summary."""
    try:
        prompt = (
            "Analyze the following document text and return a valid JSON object with the following fields:\n"
            "1. title: Title of the article.\n"
            "2. source: Publisher (e.g., McKinsey, Bloomberg, or 'Unknown' if not clear).\n"
            "3. category: Main category (e.g., Crypto, Finance).\n"
            "4. subtopic: Subtopic (e.g., Tokenization for Crypto).\n"
            "5. author: Author(s) of the article (return 'Unknown' if not found).\n"
            "6. tags: Array of up to 5 relevant tags (e.g., ['bitcoin', 'meme coin', 'Ethereum']).\n"
            "7. summary: Summary of the document (100 words or less).\n"
            "Ensure the JSON is valid, with no trailing commas in arrays or objects.\n"
            "Return only the JSON object, enclosed in ```json\n...\n```.\n\n"
            f"Document text (first 4000 characters):\n{text[:4000]}"
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes documents and returns valid JSON output."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        # Extract JSON from response (remove ```json and ``` markers)
        json_content = response.choices[0].message.content
        json_content = json_content.strip()
        if json_content.startswith("```json"):
            json_content = json_content[7:].strip()
        if json_content.endswith("```"):
            json_content = json_content[:-3].strip()
        
        # Clean the JSON string to fix trailing commas
        json_content = clean_json_string(json_content)
        
        # Parse the JSON
        return json.loads(json_content)
    except Exception as e:
        print(f"Error analyzing content: {e}")
        # Fallback values
        return {
            "title": "Unknown",
            "source": "Unknown",
            "category": "Unknown",
            "subtopic": "Unknown",
            "author": "Unknown",
            "tags": [],
            "summary": "No summary available"
        }

def create_database():
    """Create SQLite database and table if they don't exist."""
    conn = sqlite3.connect("pdf_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT,
            category TEXT,
            subtopic TEXT,
            author TEXT,
            tags TEXT,
            summary TEXT,
            filename TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn, cursor

def insert_into_database(cursor, conn, analysis, filename):
    """Insert PDF analysis data into SQLite database."""
    try:
        cursor.execute(
            "INSERT INTO articles (title, source, category, subtopic, author, tags, summary, filename) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                analysis.get("title", "Unknown"),
                analysis.get("source", "Unknown"),
                analysis.get("category", "Unknown"),
                analysis.get("subtopic", "Unknown"),
                analysis.get("author", "Unknown"),
                ",".join(analysis.get("tags", [])),
                analysis.get("summary", "No summary available"),
                filename
            )
        )
        conn.commit()
        print(f"Successfully inserted {filename} into database.")
    except Exception as e:
        print(f"Error inserting into database: {e}")

def process_pdf(pdf_path):
    """Process a PDF file and store its data in the database."""
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print("Failed to extract text from PDF.")
        return

    # Analyze content using OpenAI
    analysis = analyze_pdf_content(text)
    if not analysis:
        print("Failed to analyze PDF content.")
        return

    # Get filename from path
    filename = Path(pdf_path).name

    # Store in database
    conn, cursor = create_database()
    insert_into_database(cursor, conn, analysis, filename)
    conn.close()

def main():
    """Main function to process a PDF file."""
    pdf_path = input("Enter the path to the PDF file: ")
    if not os.path.exists(pdf_path):
        print("File does not exist.")
        return
    process_pdf(pdf_path)

if __name__ == "__main__":
    main()