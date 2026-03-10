import os
import json
import sys
from datetime import datetime
import yfinance as yf
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

JSON_PATH = os.path.join(os.path.dirname(__file__), "ai_analysis.json")

def main():
    print(f"[{datetime.now()}] Starting AI Analysis Workflow...")

    # שלב א': קריאת מצב הכפתור (Read Status)
    if not os.path.exists(JSON_PATH):
        print(f"File not found: {JSON_PATH}")
        sys.exit(1)
        
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("Invalid JSON in ai_analysis.json.")
            sys.exit(1)

    # שלב ב': התנייה (Router/Condition)
    sync_enabled = data.get("sync_enabled", False)
    if str(sync_enabled).lower() != "true":
        print("sync_enabled is false. Stopping workflow to save tokens!")
        sys.exit(0)

    # שלב ג': ניתוח המידע (ה-API של ChatGPT)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")
        sys.exit(1)
        
    client = OpenAI(api_key=api_key)
    
    # List of stocks to analyze
    SYMBOLS = ["^GSPC", "NVDA", "AAPL", "MSFT"]

    for symbol in SYMBOLS:
        print(f"Fetching market data and news for {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # 1. Market Indicators (Price & Volume)
            price = info.get("currentPrice", info.get("regularMarketPrice", 0))
            prev_close = info.get("previousClose", 0)
            name = info.get("shortName", symbol)
            
            # 2. Fundamentals & Valuation
            pe_ratio = info.get("trailingPE", "N/A")
            fwd_pe_ratio = info.get("forwardPE", "N/A")
            eps = info.get("trailingEps", "N/A")
            beta = info.get("beta", "N/A")
            target_price = info.get("targetMeanPrice", "N/A")
            
            # 3. Technicals (Calculate 50-day and 200-day SMAs)
            hist = ticker.history(period="1y")
            sma_50 = "N/A"
            sma_200 = "N/A"
            if not hist.empty and len(hist) >= 50:
                sma_50 = round(hist["Close"].tail(50).mean(), 2)
            if not hist.empty and len(hist) >= 200:
                sma_200 = round(hist["Close"].tail(200).mean(), 2)
            
            market_data = (
                f"{name} ({symbol}) Current Price: ${price:.2f}, "
                f"Previous Close: ${prev_close:.2f}, "
                f"Day High: ${info.get('dayHigh', 0):.2f}, "
                f"Day Low: ${info.get('dayLow', 0):.2f}, "
                f"Volume: {info.get('volume', 0):,}\n"
                f"Fundamentals: Trailing P/E: {pe_ratio}, Forward P/E: {fwd_pe_ratio}, "
                f"EPS: {eps}, Beta: {beta}, Analyst Target: ${target_price}\n"
                f"Technicals: 50-Day SMA: ${sma_50}, 200-Day SMA: ${sma_200}"
            )

            # 4. Latest News Headlines (Up to 10)
            news = ticker.news
            headlines = []
            if news:
                for item in news[:10]:
                    headlines.append(f"- {item.get('title', '')}")
            news_data = "\n".join(headlines) if headlines else "No recent news available."
        except Exception as e:
            print(f"Failed to fetch market data for {symbol}: {e}")
            continue # Skip to next symbol on error
        
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Prompt Template matching the guidelines
        prompt = f"""Analyze {name} ({symbol}) performance for today {"and the broader market" if symbol == "^GSPC" else ""}.
Data provided:

Market Indicators: {market_data}

Latest News: 
{news_data}

Your goal is to provide a high-conviction forecast for the next 24-48 hours.
Output ONLY a valid JSON:
{{
"signal": "BUY/SELL/HOLD",
"confidence": "X/10",
"summary": "Short 10-word logic",
"expected_move": "+X%",
"sync_enabled": true,
"timestamp": "{current_date}"
}}
Be data-driven and avoid generic advice."""

        print(f"Sending request to OpenAI API for {symbol}...")
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a financial analyst AI. Return only the requested JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result_text = response.choices[0].message.content
            new_data = json.loads(result_text)
        except Exception as e:
            print(f"OpenAI API call failed for {symbol}: {e}")
            continue
            
        # Ensure sync is kept true and timestamp is added if missing
        new_data["sync_enabled"] = True 
        if "timestamp" not in new_data:
            new_data["timestamp"] = current_date

        # Save to specific file for this symbol
        file_path = os.path.join(os.path.dirname(__file__), f"ai_analysis_{symbol.replace('^', '')}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)

        print(f"[{datetime.now()}] Update successful for {symbol}! Signal: {new_data.get('signal')} - {new_data.get('expected_move')}")

if __name__ == "__main__":
    main()
