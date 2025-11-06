import os
import argparse
from pathlib import Path
import time

from dotenv import load_dotenv
import feedparser
from google import genai
from google.genai import types
import requests

load_dotenv()


def setup_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file")
    return genai.Client(api_key=api_key)

def get_episodes(rss_url, limit=None):
    feed = feedparser.parse(rss_url)
    print(f"Found podcast: {feed.feed.title}")
    episodes = feed.entries
    if limit:
        episodes = episodes[:limit]
    return feed.feed, episodes

def download_audio(url, filename):
    print(f"Downloading {filename}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded {filename}")
    return filename

def transcribe_audio(client, audio_path):
    print(f"Uploading {audio_path} for transcription...")
    audio_file = client.files.upload(file=audio_path)
    
    print("Waiting for file processing...")
    while audio_file.state.name == "PROCESSING":
        time.sleep(1)
        audio_file = client.files.get(name=audio_file.name)
    
    if audio_file.state.name == "FAILED":
        raise Exception("Audio file processing failed")

    print("Transcribing...")
    response = client.models.generate_content(
        model='gemini-2.5-flash-lite',
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=audio_file.uri,
                        mime_type=audio_file.mime_type
                    ),
                    types.Part.from_text(text="Transcribe this audio. Output only the transcription. Do not include any obvious ad-reads or promotional segments in the transcription (if unsure, leave them in). Label the speakers.")
                ]
            )
        ]
    )
    return response.text

def create_or_get_store(client, store_name):
    for store in client.file_search_stores.list():
        if store.display_name == store_name:
            return store
    return client.file_search_stores.create(config={'display_name': store_name})

def get_existing_episodes(client, store_name):
    existing_episodes = set()
    for doc in client.file_search_stores.documents.list(parent=store_name):
        if doc.display_name:
            existing_episodes.add(doc.display_name)
    return existing_episodes

def main():
    parser = argparse.ArgumentParser(description="Ingest podcast into Gemini File Search Store")
    parser.add_argument("rss_url", help="URL of the podcast RSS feed")
    parser.add_argument("--limit", type=int, default=0, help="Number of episodes to process (0 for all)")
    parser.add_argument("--store", default="PodcastStore", help="Name of the File Search Store")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary audio and transcript files")
    args = parser.parse_args()

    client = setup_client()
    store = create_or_get_store(client, args.store)
    print(f"Using File Search Store: {store.name} ({store.display_name})")

    existing_episodes = get_existing_episodes(client, store.name)
    print(f"Found {len(existing_episodes)} existing episodes in store.")

    feed_info, episodes = get_episodes(args.rss_url, args.limit)

    for i, ep in enumerate(episodes):
        print(f"Processing episode {i+1}/{len(episodes)}: {ep.title}")
        
        if ep.title in existing_episodes:
            print(f"Episode '{ep.title}' already exists in store. Skipping.")
            continue

        # Find audio URL
        audio_url = None
        for link in ep.links:
            if link.get('type', '').startswith('audio/'):
                audio_url = link.href
                break
        
        if not audio_url:
            print(f"No audio link found for {ep.title}, skipping.")
            continue

        audio_filename = f"episode_{i}.mp3"
        try:
            download_audio(audio_url, audio_filename)
            transcript = transcribe_audio(client, audio_filename)
            
            transcript_filename = f"transcript_{i}.txt"
            with open(transcript_filename, 'w') as f:
                f.write(f"Title: {ep.title}\n")
                f.write(f"Podcast: {feed_info.title}\n")
                f.write(f"Date: {ep.get('published', '')}\n")
                f.write("\nTranscript:\n")
                f.write(transcript)
            
            print(f"Uploading transcript to store...")
            
            # Prepare metadata
            metadata = [
                {'key': 'title', 'string_value': ep.title},
                {'key': 'podcast', 'string_value': feed_info.title},
            ]
            
            if 'link' in ep:
                metadata.append({'key': 'url', 'string_value': ep.link})
                
            # Thumbnail
            thumbnail_url = None
            if 'image' in ep and 'href' in ep.image:
                thumbnail_url = ep.image.href
            elif 'media_thumbnail' in ep and len(ep.media_thumbnail) > 0:
                thumbnail_url = ep.media_thumbnail[0]['url']
            
            if thumbnail_url:
                metadata.append({'key': 'thumbnail_url', 'string_value': thumbnail_url})

            # Date
            if 'published_parsed' in ep and ep.published_parsed:
                pub_date = ep.published_parsed
                metadata.append({'key': 'year', 'numeric_value': pub_date.tm_year})
                metadata.append({'key': 'month', 'numeric_value': pub_date.tm_mon})
                metadata.append({'key': 'day', 'numeric_value': pub_date.tm_mday})

            if 'tags' in ep:
                for tag in ep.tags:
                     metadata.append({'key': 'tag', 'string_value': tag.term})

            op = client.file_search_stores.upload_to_file_search_store(
                file_search_store_name=store.name,
                file=transcript_filename,
                config={
                    'custom_metadata': metadata,
                    'display_name': ep.title
                }
            )
            
            while not op.done:
                time.sleep(2)
                op = client.operations.get(op)
            print(f"Uploaded {ep.title} to store.")
            existing_episodes.add(ep.title) # Add to set to avoid reprocessing if duplicate in feed

        except Exception as e:
            print(f"Error processing {ep.title}: {e}")
        finally:
            # Cleanup
            if not args.keep_temp:
                if os.path.exists(audio_filename):
                    os.remove(audio_filename)
                if os.path.exists(transcript_filename):
                    os.remove(transcript_filename)
            else:
                print(f"Keeping temporary files: {audio_filename}, {transcript_filename}")

if __name__ == "__main__":
    main()
