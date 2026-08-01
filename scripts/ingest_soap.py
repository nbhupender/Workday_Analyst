import os
import sys
import json
from pathlib import Path

# Path injection to handle execution from various directories
project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rag.embedder import IntentEmbedder
from src.rag.pinecone_store import PineconeStore

def ingest_soap_data(input_file="swagger/soap_specs.json", namespace="workday_soap_specs"):
    print("[Ingest SOAP] Initializing SOAP Ingestion Pipeline...")
    
    embedder = IntentEmbedder()
    store = PineconeStore()
    
    input_path = Path(project_root) / input_file
    if not input_path.exists():
        print(f"[Error] {input_file} not found. Please create it first.")
        return
        
    with open(input_path, "r", encoding="utf-8") as f:
        soap_specs = json.load(f)
        
    print(f"[Ingest SOAP] Loaded {len(soap_specs)} SOAP operations/definitions. Generating vectors...")
    
    vectors_to_upsert = []
    
    for item in soap_specs:
        item_id = item.get("id")
        api_name = item.get("api_name")
        
        # Convert fields dictionary to compatible parameter structures
        params = []
        for field_name, field_info in item.get("fields", {}).items():
            params.append({
                "name": field_name,
                "in": "body",
                "required": "required" in str(field_info.get("use_when", "")).lower(),
                "type": "string"
            })
        params_str = json.dumps(params)
        
        # 1. Ingest service intents
        intents = item.get("intent_triggers", [])
        for idx, intent in enumerate(intents):
            vector_values = embedder.encode_intents(intent)[0]
            vector_id = f"{item_id}-service-intent-{idx}"
            metadata = {
                "api_name": api_name,
                "method": "SOAP",
                "api_type": "soap",
                "type": "service",
                "field": "",
                "parameters": params_str,
                "trigger_text": intent
            }
            vectors_to_upsert.append((vector_id, vector_values, metadata))
            
        # 2. Ingest response group examples
        for field_name, group_data in item.get("response_groups", {}).items():
            examples = group_data.get("examples", [])
            for idx, example in enumerate(examples):
                vector_values = embedder.encode_intents(example)[0]
                vector_id = f"{item_id}-rg-{field_name}-{idx}"
                metadata = {
                    "api_name": api_name,
                    "method": "SOAP",
                    "api_type": "soap",
                    "type": "response_group",
                    "field": field_name,
                    "parameters": params_str,
                    "trigger_text": example
                }
                vectors_to_upsert.append((vector_id, vector_values, metadata))
            
    print(f"[Ingest SOAP] Generated {len(vectors_to_upsert)} total intent vectors. Pushing to Pinecone (namespace='{namespace}')...")
    
    batch_size = 50
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        store.upsert_vectors(batch, namespace=namespace)
        
    print(f"[Ingest SOAP] Success! Ingested {len(vectors_to_upsert)} vectors into '{namespace}' namespace.")

if __name__ == "__main__":
    ingest_soap_data()
