def main():
    print("Initializing Autonomous Financial AI Agent...")
    
    # 1. Update Legal Pages
    auto_update_legal()
    print("Legal pages synchronized.")
    
    # 2. Fetch and Post Market Data
    metrics = fetch_market_intelligence()
    title, content = generate_ai_insights(metrics)
    
    blog_payload = {
        "title": title,
        "content": content,
        "author": "Autonomous AI Sub-Agent (Agent 5)"
    }
    
    try:
        # Upsert use karein taaki purane logs update hote rahein, na ki naye bante rahein
        res = supabase.table("blogs").upsert(blog_payload).execute()
        print(f"Success! Data synchronized: {title}")
    except Exception as e:
        print(f"Database deployment error: {str(e)}")

if __name__ == "__main__":
    main()
    
