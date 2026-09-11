import os
import re
import html
import json
import pandas as pd

RAW_CSV_PATH = r'C:\Users\bc\.cache\kagglehub\datasets\thoughtvector\customer-support-on-twitter\versions\10\twcs\twcs.csv'
PROCESSED_OUTPUT_PATH = r'd:\Hiver\data\processed\spotify_conversations.json'

def clean_tweet_text(text: str) -> str:
    """Sanitize and clean tweet text content."""
    if not isinstance(text, str):
        return ""
    # Decode HTML entities
    text = html.unescape(text)
    # Remove twitter handles (@115887, @SpotifyCares, etc)
    text = re.sub(r'@[A-Za-z0-9_]+', '', text)
    # Remove http/https URLs
    text = re.sub(r'https?://\S+', '', text)
    # Normalize multiple whitespace / newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def process_spotify_dataset(raw_csv_path: str = RAW_CSV_PATH, output_path: str = PROCESSED_OUTPUT_PATH):
    print("=" * 60)
    print("PHASE 2 & 3: Data Cleaning & Conversation Reconstruction")
    print("=" * 60)
    print(f"Reading raw dataset from: {raw_csv_path}")

    # Read relevant columns
    df = pd.read_csv(
        raw_csv_path,
        usecols=['tweet_id', 'author_id', 'inbound', 'created_at', 'text', 'response_tweet_id', 'in_response_to_tweet_id'],
        low_memory=False
    )
    print(f"Total raw tweets loaded: {len(df):,}")

    # Filter brand responses for SpotifyCares with valid parent tweet ID
    spotify_replies = df[(df['author_id'] == 'SpotifyCares') & (df['inbound'] == False) & (df['in_response_to_tweet_id'].notnull())].copy()
    spotify_replies['in_response_to_tweet_id'] = spotify_replies['in_response_to_tweet_id'].astype(int)

    # Filter inbound customer tweets
    cust_tweets = df[df['inbound'] == True][['tweet_id', 'author_id', 'created_at', 'text']].copy()

    # Merge on parent tweet ID to form Customer -> Brand pairs
    merged = pd.merge(
        spotify_replies,
        cust_tweets,
        left_on='in_response_to_tweet_id',
        right_on='tweet_id',
        suffixes=('_brand', '_cust')
    )

    print(f"Total reconstructed SpotifyCares conversation pairs: {len(merged):,}")

    conversations = []
    skipped_empty = 0

    for idx, row in merged.iterrows():
        clean_cust = clean_tweet_text(row['text_cust'])
        clean_brand = clean_tweet_text(row['text_brand'])

        # Skip extremely short / empty customer messages
        if len(clean_cust) < 5 or len(clean_brand) < 5:
            skipped_empty += 1
            continue

        conversations.append({
            "id": f"SPOT-{idx+1:05d}",
            "customer_tweet_id": int(row['tweet_id_cust']),
            "brand_tweet_id": int(row['tweet_id_brand']),
            "customer_author_id": str(row['author_id_cust']),
            "customer_created_at": str(row['created_at_cust']),
            "brand_created_at": str(row['created_at_brand']),
            "raw_customer_text": str(row['text_cust']),
            "raw_brand_text": str(row['text_brand']),
            "clean_customer_text": clean_cust,
            "clean_brand_text": clean_brand
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, indent=2, ensure_ascii=False)

    print(f"Skipped empty/ultra-short pairs: {skipped_empty:,}")
    print(f"Successfully saved {len(conversations):,} clean conversations to {output_path}")
    print("=" * 60)
    return conversations

if __name__ == "__main__":
    process_spotify_dataset()
