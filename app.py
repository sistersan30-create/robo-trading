from datetime import datetime
import time
from flask import Flask, jsonify, render_template_string
import numpy as np
import pandas as pd
import yfinance as yf

app = Flask(__name__)

# Configurações do Robô Institucional
ASSET = "EURUSD=X"
SESSION_STATE = {
    "consecutive_losses": 0,
    "blocked_until": None,
    "last_signal": "Aguardando análise de mercado em tempo real...",
    "last_action": "AGUARDAR",
    "rsi_value": 50.0,
    "current_price": 1.1166,
}


def calculate_rsi(series, period=14):
  delta = series.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
  rs = gain / loss
  rsi = 100 - (100 / (1 + rs))
  return rsi


def analyze_market():
  try:
    data = yf.download(ASSET, period="1d", interval="5m", progress=False)
    if not data.empty:
      close_prices = data["Close"]
      if isinstance(close_prices, pd.DataFrame):
        close_prices = close_prices.iloc[:, 0]

      rsi_series = calculate_rsi(close_prices, period=14)
      current_rsi = float(rsi_series.iloc[-1])
      current_price = float(close_prices.iloc[-1])

      SESSION_STATE["rsi_value"] = round(current_rsi, 2)
      SESSION_STATE["current_price"] = round(current_price, 5)

      # Lógica de Gatilho de Entrada Real baseada em RSI
      if current_rsi <= 30:
        SESSION_STATE["last_action"] = "COMPRA (CALL)"
        SESSION_STATE["last_signal"] = (
            f"Oportunidade de COMPRA! RSI em {round(current_rsi, 2)}"
            " (Sobrevenda)"
        )
      elif current_rsi >= 70:
        SESSION_STATE["last_action"] = "VENDA (PUT)"
        SESSION_STATE["last_signal"] = (
            f"Oportunidade de VENDA! RSI em {round(current_rsi, 2)}"
            " (Sobrecompra)"
        )
      else:
        SESSION_STATE["last_action"] = "AGUARDAR"
        SESSION_STATE["last_signal"] = (
            f"Mercado em consolidação. RSI: {round(current_rsi, 2)}. À espera de"
            " zonas de pressão."
        )
  except Exception as e:
    SESSION_STATE["last_signal"] = f"A aguardar sincronização de dados..."


# Template HTML Definitivo (Visual Institucional + Motor de Sinais Ativo)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robô Mestre: Profissional Institucional</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('rsi-val').innerText = data.rsi_value;
                    document.getElementById('price-val').innerText = data.current_price;
                    document.getElementById('signal-text').innerText = data.last_signal;
                    document.getElementById('action-badge').innerText = data.last_action;
                    
                    // Atualiza cores do badge conforme a ação
                    const badge = document.getElementById('action-badge');
                    if(data.last_action.includes("COMPRA")) {
                        badge.className = "text-xs font-bold px-2 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-600";
                    } else if(data.last_action.includes("VENDA")) {
                        badge.className = "text-xs font-bold px-2 py-1 rounded bg-rose-950 text-rose-300 border border-rose-600";
                    } else {
                        badge.className = "text-xs font-bold px-2 py-1 rounded bg-amber-950 text-amber-300 border border-amber-600";
                    }
                });
        }
        setInterval(updateDashboard, 5000); // Atualiza a cada 5 segundos
    </script>
</head>
<body class="bg-slate-950 text-slate-100 font-sans p-4">
    <div class="max-w-md mx-auto space-y-4">
        <!-- Cabeçalho Institucional -->
        <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center justify-between shadow-lg">
            <h1 class="font-bold text-emerald-400 text-base">🤖 Robô Mestre: Pro</h1>
            <span class="text-xs bg-emerald-950 text-emerald-300 px-2 py-1 rounded border border-emerald-800">EUR/USD Live</span>
        </div>

        <!-- Métricas em Tempo Real -->
        <div class="grid grid-cols-2 gap-3">
            <div class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-center shadow">
                <p class="text-xs text-slate-400">Preço Atual</p>
                <p id="price-val" class="text-xl font-bold text-slate-200">--</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 p-3 rounded-xl text-center shadow">
                <p class="text-xs text-slate-400">RSI (14) M5</p>
                <p id="rsi-val" class="text-xl font-bold text-emerald-400">--</p>
            </div>
        </div>

        <!-- Sinais e Inteligência de Mercado -->
        <div class="bg-slate-900 border border-amber-500/50 p-4 rounded-xl space-y-2 shadow-lg">
            <div class="flex justify-between items-center">
                <span class="text-xs uppercase tracking-wider text-amber-400 font-bold">Gatilho de Entrada</span>
                <span id="action-badge" class="text-xs font-bold px-2 py-1 rounded bg-amber-950 text-amber-300">AGUARDAR</span>
            </div>
            <p id="signal-text" class="text-sm text-slate-300">A sincronizar motor de inteligência analítica...</p>
        </div>

        <!-- Gráfico TradingView -->
        <div class="bg-slate-900 border border-slate-800 p-3 rounded-xl shadow">
            <h2 class="text-xs text-slate-400 mb-2">Gráfico ao vivo (TradingView - EURUSD)</h2>
            <div class="tradingview-widget-container">
                <div class="tradingview-widget-container__widget"></div>
                <script type="text/javascript" src="https://s.tradingview.com/external-embedding/embed-widget-single-quote.js" async>
                {
                  "symbol": "FX:EURUSD",
                  "width": "100%",
                  "colorTheme": "dark",
                  "isTransparent": true,
                  "locale": "br"
                }
                </script>
            </div>
        </div>
    </div>
</body>
</html>
"""


@app.route("/")
def index():
  analyze_market()
  return render_template_string(HTML_TEMPLATE)


@app.route("/api/status")
def api_status():
  analyze_market()
  return jsonify(SESSION_STATE)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
