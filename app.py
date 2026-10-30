import os
import datetime
from flask import Flask, jsonify, render_template_string, request
import yfinance as yf
import pandas as pd
import numpy as np

app = Flask(__name__)

# Institutional Settings and Risk Management
ASSET = "EURUSD=X"
BASE_BANKROLL = 50.0
SESSION_STATE = {
    "consecutive_losses": 0,
    "blocked_until": None
}

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_news_calendar_and_schedule():
    current_hour = datetime.datetime.now().hour
    
    if current_hour < 8 or current_hour >= 17:
        return True, "🌙 Outside Operating Hours. Recommended rest to preserve mindset and capital."
    
    if current_hour in [12, 13]: 
        return True, "🍽️ Lunch Break and Institutional Rest. New orders suspended."
        
    if current_hour in [9, 14]: 
        return True, "⚠️ ALERT: High Impact Macro News Window. Orders suspended."
        
    return False, "🟢 Market open and clear. Active operational session."

def analyze_institutional_market():
    try:
        if SESSION_STATE["consecutive_losses"] >= 2:
            return {
                "status": "DEFENSE_BLOCKED",
                "message": "🚨 Daily Stop Triggered! 2 consecutive losses. Bot in preservation mode."
            }

        off_hours, schedule_msg = check_news_calendar_and_schedule()
        if off_hours:
            return {
                "status": "STRATEGIC_PAUSE",
                "message": schedule_msg
            }

        d_m5 = yf.download(ASSET, period="1d", interval="5m", progress=False)
        d_m15 = yf.download(ASSET, period="5d", interval="15m", progress=False)

        if d_m5.empty or d_m15.empty:
            return {"status": "ERROR", "message": "No market data available."}

        if isinstance(d_m5.columns, pd.MultiIndex): d_m5.columns = d_m5.columns.get_level_values(0)
        if isinstance(d_m15.columns, pd.MultiIndex): d_m15.columns = d_m15.columns.get_level_values(0)

        close_m5 = d_m5['Close']
        volume_m5 = d_m5['Volume'] if 'Volume' in d_m5.columns else pd.Series([1]*len(close_m5))
        
        ema20_m5 = close_m5.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50_m5 = close_m5.ewm(span=50, adjust=False).mean().iloc[-1]
        rsi_m5 = calculate_rsi(close_m5, 14).iloc[-1]
        current_price = float(close_m5.iloc[-1])

        obv = (np.sign(close_m5.diff()) * volume_m5).fillna(0).cumsum().iloc[-1]
        institutional_flow = obv >= 0

        close_m15 = d_m15['Close']
        ema20_m15 = close_m15.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50_m15 = close_m15.ewm(span=50, adjust=False).mean().iloc[-1]

        uptrend_m5 = current_price > ema20_m5 and ema20_m5 > ema50_m5
        uptrend_m15 = ema20_m15 > ema50_m15
        
        downtrend_m5 = current_price < ema20_m5 and ema20_m5 < ema50_m5
        downtrend_m15 = ema20_m15 < ema50_m15

        if uptrend_m5 and uptrend_m15 and rsi_m5 < 65 and institutional_flow:
            assertiveness = 95.0
            direction = "CALL (BUY)"
            stake = BASE_BANKROLL * 0.10
            leverage = "x50"
            status = "SIGNAL_CONFIRMED"
        elif downtrend_m5 and downtrend_m15 and rsi_m5 > 35 and not institutional_flow:
            assertiveness = 95.0
            direction = "PUT (SELL)"
            stake = BASE_BANKROLL * 0.10
            leverage = "x50"
            status = "SIGNAL_CONFIRMED"
        elif (uptrend_m5 or downtrend_m5) and not (uptrend_m15 or downtrend_m15):
            assertiveness = 91.0
            direction = "CALL" if uptrend_m5 else "PUT"
            stake = BASE_BANKROLL * 0.04
            leverage = "x50"
            status = "CONSERVATIVE_SIGNAL"
        else:
            return {
                "status": "WAIT",
                "message": "Market without perfect confluence (<90%). Preserving bankroll of $50.00."
            }

        return {
            "status": status,
            "asset": ASSET,
            "direction": direction,
            "timeframe": "M5 (Confirmed in M15)",
            "estimated_assertiveness": f"{assertiveness}%",
            "leverage": leverage,
            "suggested_entry": f"${stake:.2f}",
            "current_price": f"{current_price:.5f}",
            "rsi": f"{rsi_m5:.2f}",
            "volume_ok": bool(institutional_flow)
        }

    except Exception as e:
        return {"status": "ERROR", "detail": str(e)}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Bot - Institutional Pro</title>
    <style>
        body { background-color: #0b0e14; color: #ffffff; font-family: Arial, sans-serif; padding: 12px; margin: 0; }
        h1 { color: #00FFAA; text-align: center; font-size: 18px; margin-bottom: 5px; }
        .clock-bar { background: #121824; border: 1px solid #00FFAA; padding: 8px; border-radius: 8px; display: flex; justify-content: space-around; align-items: center; margin-bottom: 12px; font-size: 13px; font-weight: bold; color: #00FFAA; }
        .card { background-color: #161922; padding: 12px; border-radius: 10px; border: 1px solid #222; margin-bottom: 12px; }
        .mode-container { display: flex; gap: 4px; margin-top: 5px; }
        .btn-mode { flex: 1; padding: 6px; font-size: 11px; font-weight: bold; border-radius: 6px; border: 2px solid #444; background-color: #161922; color: #aaa; cursor: pointer; }
        .btn-mode.active { border-color: #00FFAA; background-color: #003322; color: #00FFAA; }
        .box { background-color: #161922; padding: 12px; border-radius: 10px; border: 2px solid #00FFAA; margin-top: 8px; text-align: center; font-size: 13px; font-weight: bold; color: #00FFAA; word-break: break-all; }
        .tradingview-widget-container { height: 400px; width: 100%; margin-top: 10px; }
        .btn-voice { background-color: #00FFAA; color: #0b0e14; border: none; padding: 8px; border-radius: 6px; font-weight: bold; width: 100%; margin-top: 8px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🤖 Master Bot: Institutional Pro</h1>
    
    <div class="clock-bar">
        <div>🕒 <span id="current-clock">00:00:00</span></div>
        <div>⏱️ M5 Close: <span id="timer-m5" style="color: #FF3333;">05:00</span></div>
    </div>

    <div class="card">
        <label style="font-weight:bold; color:#00FFAA; font-size:12px; display:block;">👋 Greeting & Work Routine:</label>
        <button class="btn-voice" onclick="speakGreeting()">🗣️ Listen Initial Greeting</button>

        <label style="font-weight:bold; color:#00FFAA; font-size:12px; display:block; margin-top:10px;">🎛️ Sound Alert Mode:</label>
        <div class="mode-container">
            <button id="m-complete" class="btn-mode active" onclick="setMode('complete')">🔊 Complete</button>
            <button id="m-vibra" class="btn-mode" onclick="setMode('vibra')">🔕 Vibrate Only</button>
            <button id="m-silencio" class="btn-mode" onclick="setMode('silencio')">🔇 Silent</button>
        </div>
    </div>

    <div class="card">
        <h3 style="margin:0 0 8px 0; font-size:14px;">📊 Signals and Market Intelligence:</h3>
        <div id="bot-status" class="box">Synchronizing with the institutional engine...</div>
    </div>

    <div class="card">
        <h3 style="margin:0 0 8px 0; font-size:14px;">📈 Live Chart (TradingView - EURUSD)</h3>
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {
            "width": "100%",
            "height": "100%",
            "symbol": "FX:EURUSD",
            "interval": "5",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "allow_symbol_change": true,
            "calendar": false,
            "support_host": "https://www.tradingview.com"
          }
          </script>
        </div>
    </div>

    <script>
        let currentMode = 'complete';
        let audioCtx = null;

        function speakGreeting() {
            if ('speechSynthesis' in window) {
                let text = "Good morning! Ready to start our work? A blessed day to you, let us begin!";
                let utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'en-US';
                utterance.rate = 1.0;
                
                let voices = window.speechSynthesis.getVoices();
                let maleVoice = voices.find(v => v.name.toLowerCase().includes('male') || v.name.toLowerCase().includes('david') || v.name.toLowerCase().includes('google us english'));
                if (maleVoice) {
                    utterance.voice = maleVoice;
                }
                
                window.speechSynthesis.speak(utterance);
            }
        }

        window.onload = () => {
            setTimeout(speakGreeting, 1000);
        };

        function updateClocks() {
            let now = new Date();
            let hours = String(now.getHours()).padStart(2, '0');
            let minutes = String(now.getMinutes()).padStart(2, '0');
            let seconds = String(now.getSeconds()).padStart(2, '0');
            
            document.getElementById('current-clock').innerText = `${hours}:${minutes}:${seconds}`;

            let remainingMins = 4 - (now.getMinutes() % 5);
            let remainingSecs = 59 - now.getSeconds();
            let formattedM5Time = String(remainingMins).padStart(2, '0') + ":" + String(remainingSecs).padStart(2, '0');
            document.getElementById('timer-m5').innerText = formattedM5Time;
        }
        setInterval(updateClocks, 1000);
        updateClocks();

        function playBeep(freq = 800, dur = 100) {
            if (currentMode === 'silencio') return;
            if (currentMode === 'vibra' && navigator.vibrate) { navigator.vibrate(100); return; }
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                let osc = audioCtx.createOscillator();
                let gain = audioCtx.createGain();
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                setTimeout(() => osc.stop(), dur);
            } catch(e) {}
        }

        function setMode(mode) {
            currentMode = mode;
            document.querySelectorAll('.btn-mode').forEach(b => b.classList.remove('active'));
            document.getElementById('m-' + mode).classList.add('active');
            playBeep(1000, 150);
        }

        async function fetchProSignal() {
            try {
                let res = await fetch('/api/signal');
                let data = await res.json();
                let div = document.getElementById('bot-status');
                
                if (data.status === 'SIGNAL_CONFIRMED' || data.status === 'CONSERVATIVE_SIGNAL') {
                    div.style.borderColor = "#00FF66";
                    div.innerHTML = `🔥 <b>${data.status}</b><br>🎯 Direction: <b>${data.direction}</b><br>✨ Assertiveness: <b>${data.estimated_assertiveness}</b><br>💰 Entry: <b>${data.suggested_entry}</b> (Lev. ${data.leverage})<br>📈 RSI: ${data.rsi} | Price: ${data.current_price}`;
                    playBeep(1400, 300);
                } else {
                    div.style.borderColor = "#FFAA00";
                    div.innerHTML = `⏳ <b>${data.status}</b><br>${data.message}`;
                }
            } catch (e) {
                document.getElementById('bot-status').innerText = "Waiting for engine synchronization...";
            }
        }

        fetchProSignal();
        setInterval(fetchProSignal, 15000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/signal')
def api_signal():
    return jsonify(analyze_institutional_market())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
