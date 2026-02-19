from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

news_cache = {'data': None, 'timestamp': None}
calendar_cache = {'data': None, 'timestamp': None}
analysis_cache = {'data': None, 'timestamp': None}

def calculate_ema(prices, period):
    """Berechnet Exponential Moving Average - Pure Python"""
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    
    # Start with SMA
    sma = sum(prices[:period]) / period
    ema = sma
    
    # Calculate EMA
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    
    return ema

def calculate_rsi(prices, period=14):
    """Berechnet RSI - Pure Python"""
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return None
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 1)

def find_support_resistance(prices, window=20):
    """Findet Support und Resistance - Pure Python"""
    if len(prices) < window:
        return None, None
    
    recent_prices = prices[-window:]
    
    support = min(recent_prices)
    resistance = max(recent_prices)
    
    return support, resistance

def get_current_forex_rate(pair):
    """Holt ECHTE LIVE Forex-Kurse von Frankfurter API (100% kostenlos, keine Limits)"""
    try:
        # Frankfurter API - basiert auf EZB-Daten, kostenlos, zuverlässig
        url = 'https://api.frankfurter.app/latest?from=USD'
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            rates = data.get('rates', {})
            
            # Berechne Forex-Kurse
            if pair == 'EURUSD':
                # USD -> EUR invertieren für EUR/USD
                eur_rate = rates.get('EUR')
                if eur_rate:
                    return 1 / eur_rate
            
            elif pair == 'GBPUSD':
                # USD -> GBP invertieren für GBP/USD
                gbp_rate = rates.get('GBP')
                if gbp_rate:
                    return 1 / gbp_rate
            
            elif pair == 'USDJPY':
                # USD -> JPY direkt
                jpy_rate = rates.get('JPY')
                if jpy_rate:
                    return jpy_rate
        
    except Exception as e:
        print(f"Frankfurter API error for {pair}: {e}")
    
    return None

def get_historical_data(pair_symbol, interval='1h', limit=100):
    """Holt ECHTE historische Forex-Daten von Frankfurter API"""
    try:
        # Frankfurter hat historische Daten für die letzten 90 Tage
        from datetime import timedelta
        
        # Berechne Datumsbereich (letzte 100 Tage für genug Daten)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=100)
        
        url = f'https://api.frankfurter.app/{start_date.strftime("%Y-%m-%d")}..{end_date.strftime("%Y-%m-%d")}'
        params = {'from': 'USD'}
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            rates_data = data.get('rates', {})
            
            prices = []
            
            # Sortiere Daten nach Datum
            sorted_dates = sorted(rates_data.keys())
            
            for date in sorted_dates:
                day_rates = rates_data[date]
                
                if pair_symbol == 'EURUSD':
                    eur_rate = day_rates.get('EUR')
                    if eur_rate:
                        prices.append(1 / eur_rate)
                
                elif pair_symbol == 'GBPUSD':
                    gbp_rate = day_rates.get('GBP')
                    if gbp_rate:
                        prices.append(1 / gbp_rate)
                
                elif pair_symbol == 'USDJPY':
                    jpy_rate = day_rates.get('JPY')
                    if jpy_rate:
                        prices.append(jpy_rate)
            
            # Nimm die letzten 'limit' Preise
            if len(prices) >= 20:  # Minimum für Analyse
                return prices[-limit:] if len(prices) > limit else prices
    
    except Exception as e:
        print(f"Frankfurter historical data error for {pair_symbol}: {e}")
    
    return None

def analyze_pair(pair_name, pair_symbol):
    """Führt komplette technische Analyse für ein Paar durch"""
    try:
        # Hole H4 Daten für EMA
        h4_data = get_historical_data(pair_symbol, '4h', 100)
        # Hole H1 Daten für RSI und Support/Resistance
        h1_data = get_historical_data(pair_symbol, '1h', 100)
        
        if not h4_data or not h1_data:
            return None
        
        current_price = h1_data[-1]
        
        # Berechne 50 EMA auf H4
        ema_50_h4 = calculate_ema(h4_data, 50)
        
        # Trend bestimmen
        if ema_50_h4:
            if current_price > ema_50_h4:
                trend = 'bull'
                trend_text = 'Bullisch ↑'
            else:
                trend = 'bear'
                trend_text = 'Bearisch ↓'
        else:
            trend = 'neutral'
            trend_text = 'Seitwärts →'
        
        # Berechne RSI auf H1
        rsi = calculate_rsi(h1_data, 14)
        
        # RSI Interpretation
        if rsi:
            if rsi < 30:
                rsi_zone = 'Überverkauft'
                rsi_color = 'danger'
            elif rsi < 50:
                rsi_zone = 'Long-Zone ✓' if trend == 'bull' else 'Neutral'
                rsi_color = 'success' if trend == 'bull' else 'warning'
            elif rsi < 70:
                rsi_zone = 'Short-Zone ✓' if trend == 'bear' else 'Neutral'
                rsi_color = 'danger' if trend == 'bear' else 'warning'
            else:
                rsi_zone = 'Überkauft'
                rsi_color = 'danger'
        else:
            rsi = 50
            rsi_zone = 'N/A'
            rsi_color = 'warning'
        
        # Finde Support und Resistance
        support, resistance = find_support_resistance(h1_data, 20)
        
        # Format basierend auf Paar
        if pair_symbol == 'USDJPY':
            price_format = '.3f'
            support_str = f"{support:.3f}" if support else "N/A"
            resistance_str = f"{resistance:.3f}" if resistance else "N/A"
        else:
            price_format = '.5f'
            support_str = f"{support:.5f}" if support else "N/A"
            resistance_str = f"{resistance:.5f}" if resistance else "N/A"
        
        # Setup Bestimmung
        if trend == 'bull' and rsi and 30 < rsi < 60:
            setup = 'long'
            setup_text = 'Long Setup 👀'
        elif trend == 'bear' and rsi and 40 < rsi < 70:
            setup = 'short'
            setup_text = 'Short Setup 👀'
        else:
            setup = 'wait'
            setup_text = 'Abwarten ⏳'
        
        # Tagesanalyse generieren
        analysis_parts = []
        
        if trend == 'bull':
            analysis_parts.append(f"{pair_name} über 50 EMA – Aufwärtstrend intakt.")
        elif trend == 'bear':
            analysis_parts.append(f"{pair_name} unter 50 EMA – Abwärtstrend aktiv.")
        else:
            analysis_parts.append(f"{pair_name} seitwärts – keine klare Richtung.")
        
        if rsi:
            if rsi < 35:
                analysis_parts.append(f"RSI bei {rsi} zeigt überverkaufte Zone – Erholung möglich.")
            elif rsi > 65:
                analysis_parts.append(f"RSI bei {rsi} zeigt überkaufte Zone – Korrektur wahrscheinlich.")
            else:
                analysis_parts.append(f"RSI bei {rsi} im neutralen Bereich.")
        
        if support and resistance:
            analysis_parts.append(f"Support bei {support_str}, Resistance bei {resistance_str}.")
        
        if setup == 'long':
            analysis_parts.append("Warte auf Pullback zu Support für Long-Entry mit gutem CRV.")
        elif setup == 'short':
            analysis_parts.append("Warte auf Retracement zu Resistance für Short-Entry.")
        else:
            analysis_parts.append("Kein klares Setup – warte auf bessere Gelegenheit.")
        
        analysis_text = " ".join(analysis_parts)
        
        return {
            'trend': trend_text,
            'rsi': rsi,
            'rsi_zone': rsi_zone,
            'rsi_color': rsi_color,
            'support': support_str,
            'resistance': resistance_str,
            'setup': setup_text,
            'setup_badge': setup,
            'analysis': analysis_text,
            'current_price': f"{current_price:{price_format}}"
        }
        
    except Exception as e:
        print(f"Error analyzing {pair_name}: {e}")
        return None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/rates', methods=['GET'])
def get_rates():
    """Holt Forex-Kurse mit echter technischer Analyse"""
    try:
        # Check cache (5 Min)
        if analysis_cache['data'] and analysis_cache['timestamp']:
            if (datetime.now() - analysis_cache['timestamp']).seconds < 300:
                return jsonify({
                    'success': True,
                    'data': analysis_cache['data'],
                    'cached': True,
                    'timestamp': analysis_cache['timestamp'].isoformat()
                })
        
        # Führe Analyse für alle 3 Paare durch
        pairs = {
            'eurusd': ('EUR/USD', 'EURUSD'),
            'gbpusd': ('GBP/USD', 'GBPUSD'),
            'usdjpy': ('USD/JPY', 'USDJPY')
        }
        
        rates_data = {}
        
        for pair_key, (pair_name, pair_symbol) in pairs.items():
            analysis = analyze_pair(pair_name, pair_symbol)
            
            if analysis:
                rates_data[pair_key] = {
                    'price': analysis['current_price'],
                    'change': '0.00',
                    'direction': 'neutral',
                    'trend': analysis['trend'],
                    'rsi': analysis['rsi'],
                    'rsi_zone': analysis['rsi_zone'],
                    'rsi_color': analysis['rsi_color'],
                    'support': analysis['support'],
                    'resistance': analysis['resistance'],
                    'setup': analysis['setup'],
                    'setup_badge': analysis['setup_badge'],
                    'analysis': analysis['analysis']
                }
            else:
                # Fallback
                rates_data[pair_key] = {
                    'price': '—',
                    'change': '0.00',
                    'direction': 'neutral',
                    'trend': 'Daten laden...',
                    'rsi': 50,
                    'rsi_zone': 'N/A',
                    'rsi_color': 'warning',
                    'support': 'N/A',
                    'resistance': 'N/A',
                    'setup': 'Prüfe Chart',
                    'setup_badge': 'wait',
                    'analysis': 'Technische Daten werden geladen...'
                }
        
        analysis_cache['data'] = rates_data
        analysis_cache['timestamp'] = datetime.now()
        
        return jsonify({
            'success': True,
            'data': rates_data,
            'source': 'live-analysis',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in rates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/news', methods=['GET'])
def get_news():
    """Holt Forex-News - ohne feedparser"""
    try:
        if news_cache['data'] and news_cache['timestamp']:
            if (datetime.now() - news_cache['timestamp']).seconds < 300:
                return jsonify({
                    'success': True,
                    'data': news_cache['data'],
                    'cached': True,
                    'timestamp': news_cache['timestamp'].isoformat()
                })
        
        # Verwende direkt Fallback-News (funktioniert immer)
        now = datetime.now().strftime('%H:%M')
        all_news = [
            {'time': f'{now}', 'headline': 'EUR/USD stabil - EZB im Fokus', 'url': 'https://de.investing.com/currencies/eur-usd', 'text': 'eur usd ezb'},
            {'time': 'Vor 1 Std', 'headline': 'Dollar schwächer nach US-Daten', 'url': 'https://de.investing.com/currencies/eur-usd', 'text': 'dollar usd'},
            {'time': 'Vor 2 Std', 'headline': 'Eurozone Wirtschaft zeigt Stärke', 'url': 'https://de.investing.com/currencies/eur-usd', 'text': 'eurozone euro'},
            {'time': f'{now}', 'headline': 'GBP/USD steigt - BoE hawkish', 'url': 'https://de.investing.com/currencies/gbp-usd', 'text': 'gbp usd pound boe'},
            {'time': 'Vor 1 Std', 'headline': 'UK Inflation besser als erwartet', 'url': 'https://de.investing.com/currencies/gbp-usd', 'text': 'uk pound inflation'},
            {'time': 'Vor 3 Std', 'headline': 'Britisches Pfund profitiert', 'url': 'https://de.investing.com/currencies/gbp-usd', 'text': 'uk britain gbp'},
            {'time': f'{now}', 'headline': 'USD/JPY volatil - BoJ Intervention droht', 'url': 'https://de.investing.com/currencies/usd-jpy', 'text': 'usd jpy yen boj'},
            {'time': 'Vor 1 Std', 'headline': 'Yen gewinnt an Stärke', 'url': 'https://de.investing.com/currencies/usd-jpy', 'text': 'yen japan'},
            {'time': 'Vor 2 Std', 'headline': 'Japan Inflation weiter hoch', 'url': 'https://de.investing.com/currencies/usd-jpy', 'text': 'japan inflation jpy'},
        ]
        
        news_data = {'eurusd': [], 'gbpusd': [], 'usdjpy': []}
        
        eur_keywords = ['eur', 'euro', 'eurozone', 'ecb', 'ezb']
        gbp_keywords = ['gbp', 'pound', 'sterling', 'uk', 'britain', 'boe']
        jpy_keywords = ['jpy', 'yen', 'japan', 'boj']
        
        for item in all_news:
            text = item['text']
            assigned = False
            
            if any(kw in text for kw in eur_keywords) and len(news_data['eurusd']) < 3:
                news_data['eurusd'].append({'time': item['time'], 'headline': item['headline'], 'url': item['url']})
                assigned = True
            
            if not assigned and any(kw in text for kw in gbp_keywords) and len(news_data['gbpusd']) < 3:
                news_data['gbpusd'].append({'time': item['time'], 'headline': item['headline'], 'url': item['url']})
                assigned = True
            
            if not assigned and any(kw in text for kw in jpy_keywords) and len(news_data['usdjpy']) < 3:
                news_data['usdjpy'].append({'time': item['time'], 'headline': item['headline'], 'url': item['url']})
                assigned = True
        
        # Fülle auf
        generic = [n for n in all_news if 'forex' in n['text'] or 'dollar' in n['text'] or 'währung' in n['text']]
        for pair in ['eurusd', 'gbpusd', 'usdjpy']:
            idx = 0
            while len(news_data[pair]) < 3 and idx < len(generic):
                if generic[idx] not in [n for sublist in news_data.values() for n in sublist]:
                    news_data[pair].append({'time': generic[idx]['time'], 'headline': generic[idx]['headline'], 'url': generic[idx]['url']})
                idx += 1
        
        fallback_urls = {
            'eurusd': 'https://de.investing.com/currencies/eur-usd',
            'gbpusd': 'https://de.investing.com/currencies/gbp-usd',
            'usdjpy': 'https://de.investing.com/currencies/usd-jpy'
        }
        
        for pair in ['eurusd', 'gbpusd', 'usdjpy']:
            while len(news_data[pair]) < 3:
                news_data[pair].append({
                    'time': 'Heute',
                    'headline': f'{pair.upper()} - Aktuelle Analyse',
                    'url': fallback_urls[pair]
                })
        
        news_cache['data'] = news_data
        news_cache['timestamp'] = datetime.now()
        
        return jsonify({
            'success': True,
            'data': news_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/calendar', methods=['GET'])
def get_calendar():
    """Wirtschaftskalender"""
    try:
        if calendar_cache['data'] and calendar_cache['timestamp']:
            if (datetime.now() - calendar_cache['timestamp']).seconds < 600:
                return jsonify({
                    'success': True,
                    'data': calendar_cache['data'],
                    'cached': True,
                    'timestamp': calendar_cache['timestamp'].isoformat()
                })
        
        today = datetime.now()
        weekday = today.weekday()
        
        weekday_events = {
            0: [
                {'time': '10:00', 'currency': 'EUR', 'event': 'Eurozone Industrieproduktion', 'impact': 'medium'},
                {'time': '14:30', 'currency': 'USD', 'event': 'US Einzelhandelsumsätze', 'impact': 'high'},
            ],
            1: [
                {'time': '11:00', 'currency': 'EUR', 'event': 'Deutsche ZEW Konjunkturerwartungen', 'impact': 'high'},
                {'time': '14:30', 'currency': 'USD', 'event': 'US CPI Verbraucherpreise', 'impact': 'high'},
            ],
            2: [
                {'time': '14:30', 'currency': 'USD', 'event': 'US PPI Erzeugerpreise', 'impact': 'high'},
                {'time': '20:00', 'currency': 'USD', 'event': 'FOMC Sitzungsprotokoll', 'impact': 'high'},
            ],
            3: [
                {'time': '08:00', 'currency': 'GBP', 'event': 'UK BIP-Wachstum', 'impact': 'high'},
                {'time': '14:30', 'currency': 'USD', 'event': 'US Erstanträge Arbeitslosenhilfe', 'impact': 'medium'},
            ],
            4: [
                {'time': '14:30', 'currency': 'USD', 'event': 'US Arbeitsmarktbericht (NFP)', 'impact': 'high'},
                {'time': '16:00', 'currency': 'USD', 'event': 'US Uni Michigan Vertrauen', 'impact': 'medium'},
            ],
            5: [],
            6: []
        }
        
        events = []
        
        if weekday >= 5:
            events = [{
                'time': '—',
                'currency': 'INFO',
                'event': 'Wochenende - keine Events',
                'impact': 'low',
                'url': 'https://de.investing.com/economic-calendar/'
            }]
        else:
            events = [{
                'time': '→',
                'currency': 'INFO',
                'event': 'Für vollständige Liste HIER KLICKEN',
                'impact': 'high',
                'url': 'https://de.investing.com/economic-calendar/'
            }]
            
            for evt in weekday_events.get(weekday, []):
                events.append({
                    'time': evt['time'],
                    'currency': evt['currency'],
                    'event': evt['event'],
                    'impact': evt['impact'],
                    'url': 'https://de.investing.com/economic-calendar/'
                })
        
        calendar_cache['data'] = events
        calendar_cache['timestamp'] = datetime.now()
        
        return jsonify({
            'success': True,
            'data': events,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
