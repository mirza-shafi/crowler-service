#!/usr/bin/env python3
"""
Quick script to view all content in the database
"""

import requests
import json

# Assuming your server is running on port 8001
BASE_URL = "http://localhost:8001/api/v1"

def view_content():
    """Fetch and display all content"""
    
    print("=" * 80)
    print("CONTENT MANAGER - ALL INGESTED CONTENT")
    print("=" * 80)
    
    # Get statistics
    print("\n📊 STATISTICS:")
    try:
        response = requests.get(f"{BASE_URL}/ingestion/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   Total Content: {stats['total_content']}")
            print(f"   By Source Type:")
            for source, count in stats['by_source_type'].items():
                print(f"      - {source}: {count}")
            print(f"   Indexed: {stats['indexed_content']} ({stats['indexing_percentage']}%)")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # List all content
    print("\n" + "=" * 80)
    print("📄 ALL CONTENT:")
    print("=" * 80)
    
    for source_type in ['url', 'file', 'text']:
        print(f"\n{'='*80}")
        print(f"📁 {source_type.upper()} CONTENT:")
        print(f"{'='*80}")
        
        try:
            response = requests.get(
                f"{BASE_URL}/ingestion/content/list",
                params={"source_type": source_type, "limit": 100}
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data['items']
                
                if not items:
                    print(f"   (No {source_type} content found)")
                    continue
                
                for i, item in enumerate(items, 1):
                    print(f"\n{i}. {item['title']}")
                    print(f"   ID: {item['id']}")
                    print(f"   Source: {item['source_identifier'] or 'N/A'}")
                    print(f"   Words: {item['word_count']}")
                    print(f"   Indexed: {'✅' if item['is_indexed'] else '❌'}")
                    print(f"   Date: {item['crawl_timestamp']}")
            else:
                print(f"   ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    view_content()
