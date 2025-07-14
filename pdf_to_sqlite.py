import PyPDF2
import sqlite3
from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv

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

def generate_summary(text):
    """Generate a summary of the text using OpenAI API."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text."},
                {"role": "user", "content": f"Summarize the following text in 100 words or less:\n\n{text[:4000]}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating summary: {e}")
        return None

def create_database():
    """Create SQLite database and table if they don't exist."""
    conn = sqlite3.connect("pdf_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdfs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            content TEXT,
            summary TEXT
        )
    """)
    conn.commit()
    return conn, cursor

def insert_into_database(cursor, conn, filename, content, summary):
    """Insert PDF data into SQLite database."""
    try:
        cursor.execute(
            "INSERT INTO pdfs (filename, content, summary) VALUES (?, ?, ?)",
            (filename, content, summary)
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

    # Generate summary using OpenAI
    summary = generate_summary(text)
    if not summary:
        print("Failed to generate summary.")
        return

    # Get filename from path
    filename = Path(pdf_path).name

    # Store in database
    conn, cursor = create_database()
    insert_into_database(cursor, conn, filename, text, summary)
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