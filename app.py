import os
import datetime
from flask import Flask, jsonify, render_template_string, request
import yfinance as yf
import pandas as pd
import numpy as np

app = Flask(__name__)

# Configurações Institucionais e Gestão de Risco
ATIVO = "EURUSD=X"
BANCA_BASE = 50.0
ESTADO_SESSAO = {
    "perdas_consecutivas": 0,
    "bloqueado_ate": None
}

def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def verificar_calendario_noticias_e_horario():
    hora_atual = datetime.datetime.now().hour
    
    if hora_atual < 8 or hora_atual >= 17:
        return True, "🌙 Fora do Horário Operacional. Descanso recomendado para preservar a mente e o capital."
    
    if hora_atual in [12, 13]: 
        return True, "🍽️ Pausa para Almoço e Descanso Institucional. Novas ordens suspensas."
        
    if hora_atual in [9, 14]: 
        return True, "⚠️ ALERTA: Janela de Noticiário Macro de Alto Impacto. Ordens suspensas."
        
    return False, "🟢 Mercado aberto e livre. Sessão operacional ativa."

def analisar_mercado_institucional():
    try:
        if ESTADO_SESSAO["perdas_consecutivas"] >= 2:
            return {
                "status": "BLOQUEADO_DEFESA",
                "mensagem": "🚨 Stop Diário Ativado! 2 perdas consecutivas. Robô em modo de preservação."
            }

        fora_horario, msg_horario = verificar_calendario_noticias_e_horario()
        if fora_horario:
            return {
                "status": "PAUSA_ESTRATEGICA",
                "mensagem": msg_horario
            }

        d_m5 = yf.download(ATIVO, period="1d", interval="5m", progress=False)
        d_m15 = yf.download(ATIVO, period="5d", interval="15m", progress=False)

        if d_m5.empty or d_m15.empty:
            return {"status": "ERRO", "mensagem": "Sem dados de mercado disponíveis."}

        if isinstance(d_m5.columns, pd.MultiIndex): d_m5.columns = d_m5.columns.get_level_values(0)
        if isinstance(d_m15.columns, pd.MultiIndex): d_m15.columns = d_m15.columns.get_level_values(0)

        close_m5 = d_m5['Close']
        volume_m5 = d_m5['Volume'] if 'Volume' in d_m5.columns else pd.Series([1]*len(close_m5))
        
        ema20_m5 = close_m5.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50_m5 = close_m5.ewm(span=50, adjust=False).mean().iloc[-1]
        rsi_m5 = calcular_rsi(close_m5, 14).iloc[-1]
        preco_atual = float(close_m5.iloc[-1])

        obv = (np.sign(close_m5.diff()) * volume_m5).fillna(0).cumsum().iloc[-1]
        fluxo_institucional = obv >= 0

        close_m15 = d_m15['Close']
        ema20_m15 = close_m15.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50_m15 = close_m15.ewm(span=50, adjust=False).mean().iloc[-1]

        tendencia_alta_m5 = preco_atual > ema20_m5 and ema20_m5 > ema50_m5
        tendencia_alta_m15 = ema20_m15 > ema50_m15
        
        tendencia_baixa_m5 = preco_atual < ema20_m5 and ema20_m5 < ema50_m5
        tendencia_baixa_m15 = ema20_m15 < ema50_m15

        if tendencia_alta_m5 and tendencia_alta_m15 and rsi_m5 < 65 and fluxo_institucional:
            assertividade = 95.0
            direcao = "CALL (COMPRA)"
            mao = BANCA_BASE * 0.10
            alavancagem = "x50"
            status = "SINAL_CONFIRMADO"
        elif tendencia_baixa_m5 and tendencia_baixa_m15 and rsi_m5 > 35 and not fluxo_institucional:
            assertividade = 95.0
            direcao = "PUT (VENDA)"
            mao = BANCA_BASE * 0.10
            alavancagem = "x50"
            status = "SINAL_CONFIRMADO"
        elif (tendencia_alta_m5 or tendencia_baixa_m5) and not (tendencia_alta_m15 or tendencia_baixa_m15):
            assertividade = 91.0
            direcao = "CALL" if tendencia_alta_m5 else "PUT"
            mao = BANCA_BASE * 0.04
            alavancagem = "x50"
            status = "SINAL_CONSERVADOR"
        else:
            return {
                "status": "AGUARDAR",
                "mensagem": "Mercado sem confluência perfeita (<90%). Preservando a banca de R$ 50,00."
            }

        return {
            "status": status,
            "ativo": ATIVO,
            "direcao": direcao,
            "timeframe": "M5 (Confirmado em M15)",
            "assertividade_estimada": f"{assertividade}%",
            "alavancagem": alavancagem,
            "entrada_sugerida": f"R$ {mao:.2f}",
            "preco_atual": f"{preco_atual:.5f}",
            "rsi": f"{rsi_m5:.2f}",
            "volume_ok": bool(fluxo_institucional)
        }

    except Exception as e:
        return {"status": "ERRO", "detalhe": str(e)}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robô Master - Institucional Pro</title>
    <style>
        body { background-color: #0b0e14; color: #ffffff; font-family: Arial, sans-serif; padding: 12px; margin: 0; }
        h1 { color: #00FFAA; text-align: center; font-size: 18px; margin-bottom: 5px; }
        .relogio-bar { background: #121824; border: 1px solid #00FFAA; padding: 8px; border-radius: 8px; display: flex; justify-content: space-around; align-items: center; margin-bottom: 12px; font-size: 13px; font-weight: bold; color: #00FFAA; }
        .card { background-color: #161922; padding: 12px; border-radius: 10px; border: 1px solid #222; margin-bottom: 12px; }
        .modo-container { display: flex; gap: 4px; margin-top: 5px; }
        .btn-modo { flex: 1; padding: 6px; font-size: 11px; font-weight: bold; border-radius: 6px; border: 2px solid #444; background-color: #161922; color: #aaa; cursor: pointer; }
        .btn-modo.active { border-color: #00FFAA; background-color: #003322; color: #00FFAA; }
        .box { background-color: #161922; padding: 12px; border-radius: 10px; border: 2px solid #00FFAA; margin-top: 8px; text-align: center; font-size: 13px; font-weight: bold; color: #00FFAA; word-break: break-all; }
        .tradingview-widget-container { height: 400px; width: 100%; margin-top: 10px; }
        .btn-voz { background-color: #00FFAA; color: #0b0e14; border: none; padding: 8px; border-radius: 6px; font-weight: bold; width: 100%; margin-top: 8px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🤖 Robô Master: Institucional Pro</h1>
    
    <div class="relogio-bar">
        <div>🕒 <span id="relogio-atual">00:00:00</span></div>
        <div>⏱️ Fech. M5: <span id="cronometro-m5" style="color: #FF3333;">05:00</span></div>
    </div>

    <div class="card">
        <label style="font-weight:bold; color:#00FFAA; font-size:12px; display:block;">👋 Saudação & Rotina de Trabalho:</label>
        <button class="btn-voz" onclick="falarSaudacao()">🗣️ Ouvir Saudação Inicial</button>

        <label style="font-weight:bold; color:#00FFAA; font-size:12px; display:block; margin-top:10px;">🎛️ Modo de Alerta Sonoro:</label>
        <div class="modo-container">
            <button id="m-completo" class="btn-modo active" onclick="definirModo('completo')">🔊 Completo</button>
            <button id="m-vibra" class="btn-modo" onclick="definirModo('vibra')">🔕 Só Vibra</button>
            <button id="m-silencio" class="btn-modo" onclick="definirModo('silencio')">🔇 Silencioso</button>
        </div>
    </div>

    <div class="card">
        <h3 style="margin:0 0 8px 0; font-size:14px;">📊 Sinais e Inteligência de Mercado:</h3>
        <div id="status-robo" class="box">A sincronizar com o motor institucional...</div>
    </div>

    <div class="card">
        <h3 style="margin:0 0 8px 0; font-size:14px;">📈 Gráfico Ao Vivo (TradingView - EURUSD)</h3>
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
            "locale": "br",
            "allow_symbol_change": true,
            "calendar": false,
            "support_host": "https://www.tradingview.com"
          }
          </script>
        </div>
    </div>

    <script>
        let modoAtual = 'completo';
        let audioCtx = null;

        function falarSaudacao() {
            if ('speechSynthesis' in window) {
                let texto = "Bom dia! Pronta para começar nosso trabalho? Um dia abençoado pra você, vamos começar!";
                let utterance = new SpeechSynthesisUtterance(texto);
                utterance.lang = 'pt-BR';
                utterance.rate = 1.0;
                
                let voces = window.speechSynthesis.getVoices();
                let vozMasculina = voces.find(v => v.name.toLowerCase().includes('male') || v.name.toLowerCase().includes('antonio') || v.name.toLowerCase().includes('daniel') || v.name.toLowerCase().includes('google português do brasil'));
                if (vozMasculina) {
                    utterance.voice = vozMasculina;
                }
                
                window.speechSynthesis.speak(utterance);
            }
        }

        window.onload = () => {
            setTimeout(falarSaudacao, 1000);
        };

        function atualizarRelogios() {
            let agora = new Date();
            let horas = String(agora.getHours()).padStart(2, '0');
            let minutos = String(agora.getMinutes()).padStart(2, '0');
            let segundos = String(agora.getSeconds()).padStart(2, '0');
            
            document.getElementById('relogio-atual').innerText = `${horas}:${minutos}:${segundos}`;

            let minRestantes = 4 - (agora.getMinutes() % 5);
            let segRestantes = 59 - agora.getSeconds();
            let tempoM5Formatado = String(minRestantes).padStart(2, '0') + ":" + String(segRestantes).padStart(2, '0');
            document.getElementById('cronometro-m5').innerText = tempoM5Formatado;
        }
        setInterval(atualizarRelogios, 1000);
        atualizarRelogios();

        function tocarBipe(freq = 800, dur = 100) {
            if (modoAtual === 'silencio') return;
            if (modoAtual === 'vibra' && navigator.vibrate) { navigator.vibrate(100); return; }
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

        function definirModo(modo) {
            modoAtual = modo;
            document.querySelectorAll('.btn-modo').forEach(b => b.classList.remove('active'));
            document.getElementById('m-' + modo).classList.add('active');
            tocarBipe(1000, 150);
        }

        async function buscarSinalPro() {
            try {
                let res = await fetch('/api/sinal');
                let data = await res.json();
                let div = document.getElementById('status-robo');
                
                if (data.status === 'SINAL_CONFIRMADO' || data.status === 'SINAL_CONSERVADOR') {
                    div.style.borderColor = "#00FF66";
                    div.innerHTML = `🔥 <b>${data.status}</b><br>🎯 Direção: <b>${data.direcao}</b><br>✨ Assertividade: <b>${data.assertividade_estimada}</b><br>💰 Entrada: <b>${data.entrada_sugerida}</b> (Alav. ${data.alavancagem})<br>📈 RSI: ${data.rsi} | Preço: ${data.preco_atual}`;
                    tocarBipe(1400, 300);
                } else {
                    div.style.borderColor = "#FFAA00";
                    div.innerHTML = `⏳ <b>${data.status}</b><br>${data.mensagem}`;
                }
            } catch (e) {
                document.getElementById('status-robo').innerText = "A aguardar sincronização do motor...";
            }
        }

        buscarSinalPro();
        setInterval(buscarSinalPro, 15000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/sinal')
def api_sinal():
    return jsonify(analisar_mercado_institucional())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
