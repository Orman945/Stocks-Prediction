# AI Stock Analysis Dashboard 📈

This is a comprehensive, real-time AI-powered stock dashboard built in Python using **Streamlit**. It fetches live financial data and combines it with daily AI-generated insights from OpenAI to provide high-conviction market forecasts.

![AI Stock Dashboard UI](dashboard_screenshot.png) <!-- Update this image filename if needed -->

## Features
- **Real-Time Market Data**: Pulls live pricing, daily highs/lows, and fundamental data directly from Yahoo Finance.
- **Interactive Candlestick Charts**: Uses Plotly to render dynamic 6-month historical candlestick charts with 50-day and 200-day Simple Moving Averages.
- **AI-Powered Market Analysis**: A dedicated Python cron script (`ai_updater.py`) securely queries OpenAI's GPT-4o model. It feeds the model technical indicators, fundamentals, and breaking news to generate a daily trading signal ("BUY", "SELL", "HOLD"), confidence score, and short summary.
- **Seamless Local State**: Extracted AI insights are stored efficiently in local JSON files to reduce API overhead and latency when switching between assets.

## Tech Stack
- **Frontend/UI**: [Streamlit](https://streamlit.io/)
- **Data Engineering**: [yFinance](https://pypi.org/project/yfinance/), Pandas
- **Visualization**: Plotly
- **AI Integration**: OpenAI Python SDK (GPT-4o)

---

## How it Works

The project is split into two core files:

### 1. The Dashboard (`app.py`)
This is the user interface. It runs a Streamlit server to visualize the financial data. Whenever an asset is selected from the sidebar, the app instantly pulls the latest live data from Yahoo Finance and displays it. It also automatically reads the local JSON files to display today's latest AI analysis on the dashboard.

### 2. The AI updater (`ai_updater.py`)
This is the background script that acts as the data pipeline to OpenAI. When executed, it pulls the complete technical array and latest breaking news for the configured assets, formulates a prompt, and requests a market forecast from GPT-4. It then parses the AI output and saves the insights into lightweight JSON files for the dashboard to read.

## Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/ai-stock-dashboard.git
   cd ai-stock-dashboard
   ```

2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your OpenAI API key:
   ```env
   OPENAI_API_KEY="sk-your-openai-api-key"
   ```

4. **Generate the Initial AI analysis:**
   Run the background script to fetch today's AI insights.
   ```bash
   python ai_updater.py
   ```

5. **Launch the Dashboard:**
   ```bash
   streamlit run app.py
   ```

## Deploying to Streamlit Community Cloud
If you intend to host this on Streamlit Cloud:
1. Verify that your `.env` file is excluded in your `.gitignore`.
2. Push this repository to GitHub.
3. On Streamlit Community Cloud, deploy the app targeting `app.py`.
4. Go to **Advanced Settings -> Secrets** in your Streamlit dashboard and paste your OpenAI key:
   ```toml
   OPENAI_API_KEY = "sk-........."
   ```
*(Note: Because Streamlit Cloud natively only runs `app.py`, this public repository already includes pre-generated snapshot JSON files from `ai_updater.py` to demonstrate the AI capability without burning live API tokens.)*
