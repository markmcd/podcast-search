import argparse
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def setup_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file")
    return genai.Client(api_key=api_key)

def get_store(client, store_name):
    for store in client.file_search_stores.list():
        if store.display_name == store_name:
            return store
    raise ValueError(f"Store '{store_name}' not found")

def main():
    parser = argparse.ArgumentParser(description="Ask questions about podcasts in the store")
    parser.add_argument("question", help="The question to ask")
    parser.add_argument("--podcast", help="Filter by specific podcast name")
    parser.add_argument("--store", default="Podcasts", help="Name of the File Search Store")
    args = parser.parse_args()

    client = setup_client()
    try:
        store = get_store(client, args.store)
    except ValueError as e:
        print(e)
        return

    metadata_filter = None
    if args.podcast:
        # Assuming the key in custom_metadata is 'podcast'
        metadata_filter = f"podcast = {args.podcast}"

    print(f"Querying store '{store.display_name}' with question: '{args.question}'")
    if metadata_filter:
        print(f"Applying filter: {metadata_filter}")

    file_search = types.FileSearch(
        file_search_store_names=[store.name],
        metadata_filter=metadata_filter
    )
    tool = types.Tool(file_search=file_search)

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=args.question,
            config=types.GenerateContentConfig(
                tools=[tool]
            )
        )
        print("\nAnswer:")
        print(response.text)

        if response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
            print("\nCitations:")
            for i, chunk in enumerate(response.candidates[0].grounding_metadata.grounding_chunks):
                if chunk.retrieved_context:
                    title = chunk.retrieved_context.title or "Unknown Episode"
                    
                    print(f"\nCitation {i+1}:")
                    print(f"Episode: {title}")
                    print(f"Text: {chunk.retrieved_context.text}")
    except Exception as e:
        print(f"Error querying store: {e}")

if __name__ == "__main__":
    main()
