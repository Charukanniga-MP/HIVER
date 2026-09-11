"""
Historical Evidence Retrieval Module with Data Leakage Prevention.
Uses TF-IDF + Cosine Similarity over clean, independent SpotifyCares conversations.
"""

import os
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CONVERSATIONS_PATH = r'd:\Hiver\data\processed\spotify_conversations.json'
GOLDEN_SET_V2_PATH = r'd:\Hiver\data\golden_set_v2.json'
CLEAN_CORPUS_PATH = r'd:\Hiver\data\processed\clean_retrieval_corpus.json'
LEAKAGE_REPORT_PATH = r'd:\Hiver\data\retrieval_leakage_report.json'

def build_evaluation_retrieval_corpus(
    conversations_path: str = CONVERSATIONS_PATH,
    golden_set_path: str = GOLDEN_SET_V2_PATH,
    similarity_threshold: float = 0.95
) -> list[dict]:
    """
    Build a clean retrieval corpus that excludes every golden evaluation example.
    Filters by exact customer_tweet_id, exact customer_text, and near-duplicates (>0.95 similarity).
    Generates data/retrieval_leakage_report.json.
    """
    with open(conversations_path, 'r', encoding='utf-8') as f:
        orig_convs = json.load(f)

    with open(golden_set_path, 'r', encoding='utf-8') as f:
        golden_data = json.load(f)

    golden_examples = golden_data.get('examples', [])
    orig_size = len(orig_convs)

    golden_tweet_ids = set(str(ex['customer_tweet_id']) for ex in golden_examples)
    golden_source_ids = set(str(ex['source_conversation_id']) for ex in golden_examples)
    golden_texts = set(ex['customer_text'].strip().lower() for ex in golden_examples)

    # 1. Exact ID Filter
    after_id_filter = []
    removed_by_id = 0
    for item in orig_convs:
        if str(item['customer_tweet_id']) in golden_tweet_ids or str(item['id']) in golden_source_ids:
            removed_by_id += 1
        else:
            after_id_filter.append(item)

    # 2. Exact Text Filter
    after_text_filter = []
    removed_by_text = 0
    for item in after_id_filter:
        if item['clean_customer_text'].strip().lower() in golden_texts:
            removed_by_text += 1
        else:
            after_text_filter.append(item)

    # 3. Near-Duplicate Filter using TF-IDF similarity > threshold against golden texts
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10000, stop_words='english')
    golden_text_list = [ex['customer_text'] for ex in golden_examples]
    candidate_text_list = [item['clean_customer_text'] for item in after_text_filter]

    vectorizer.fit(golden_text_list + candidate_text_list)
    golden_matrix = vectorizer.transform(golden_text_list)
    candidate_matrix = vectorizer.transform(candidate_text_list)

    sim_matrix = cosine_similarity(candidate_matrix, golden_matrix)
    max_sims = sim_matrix.max(axis=1)

    final_corpus = []
    removed_by_near_dup = 0
    for idx, item in enumerate(after_text_filter):
        if max_sims[idx] > similarity_threshold:
            removed_by_near_dup += 1
        else:
            final_corpus.append(item)

    # Save clean retrieval corpus
    os.makedirs(os.path.dirname(CLEAN_CORPUS_PATH), exist_ok=True)
    with open(CLEAN_CORPUS_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_corpus, f, indent=2, ensure_ascii=False)

    # Save leakage report
    leakage_report = {
        "original_corpus_size": orig_size,
        "removed_by_exact_id": removed_by_id,
        "removed_by_exact_text": removed_by_text,
        "removed_by_near_duplicate": removed_by_near_dup,
        "similarity_threshold": similarity_threshold,
        "final_clean_retrieval_corpus_size": len(final_corpus)
    }

    with open(LEAKAGE_REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(leakage_report, f, indent=2, ensure_ascii=False)

    print(f"Clean retrieval corpus built: {len(final_corpus):,} items (Leakage report saved to {LEAKAGE_REPORT_PATH})")
    return final_corpus

class HistoricalRetriever:
    def __init__(self, conversations_path: str = CLEAN_CORPUS_PATH):
        # If clean corpus does not exist yet, build it
        if not os.path.exists(conversations_path):
            print("Clean retrieval corpus not found. Building clean evaluation corpus...")
            self.conversations = build_evaluation_retrieval_corpus()
        else:
            with open(conversations_path, 'r', encoding='utf-8') as f:
                self.conversations = json.load(f)
        
        self.corpus = [c['clean_customer_text'] for c in self.conversations]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10000, stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
        print(f"HistoricalRetriever indexed {len(self.conversations):,} clean historical support cases.")

    def retrieve(self, query_text: str, exclude_tweet_id: str = None, top_k: int = 3) -> list[dict]:
        """
        Retrieve top-k historically similar support cases from the clean corpus.
        Filters out matching tweet_ids or > 0.95 similarity matches.
        """
        query_vec = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        top_indices = similarities.argsort()[::-1]
        
        results = []
        for idx in top_indices:
            if len(results) >= top_k:
                break
            
            score = float(similarities[idx])
            case = self.conversations[idx]
            
            # DATA LEAKAGE PREVENTION:
            if exclude_tweet_id and str(case.get('customer_tweet_id')) == str(exclude_tweet_id):
                continue
            if score > 0.95 and exclude_tweet_id is not None:
                continue

            results.append({
                "evidence_id": case['id'],
                "customer_tweet_id": case['customer_tweet_id'],
                "similarity_score": round(score, 4),
                "historical_customer_message": case['clean_customer_text'],
                "historical_brand_response": case['clean_brand_text'],
                "clean_customer_text": case['clean_customer_text'],
                "clean_brand_text": case['clean_brand_text'],
                "created_at": case['brand_created_at']
            })

        return results

    def retrieve_with_quality(self, query_text: str, exclude_tweet_id: str = None, top_k: int = 3) -> dict:
        """
        Retrieve top-k historical evidence with minimum evidence quality classification.
        Returns:
        {
          "evidence": [...],
          "best_similarity": 0.0,
          "evidence_quality": "strong|medium|weak"
        }
        """
        evidence = self.retrieve(query_text, exclude_tweet_id=exclude_tweet_id, top_k=top_k)
        best_sim = evidence[0]['similarity_score'] if evidence else 0.0
        
        if best_sim >= 0.70:
            quality = "strong"
        elif best_sim >= 0.50:
            quality = "medium"
        else:
            quality = "weak"
            
        return {
            "evidence": evidence,
            "best_similarity": round(best_sim, 4),
            "evidence_quality": quality
        }

