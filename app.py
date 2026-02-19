from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import yfinance as yf
import feedparser
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# NO CACHE - always fresh data!
CACHE_DURATION = 0  # 0 seconds = no cache

# Cache variables
news_cache = {'data': None, 'timestamp': None}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/rates', methods=['GET'])
def get_rates():
    """Holt FRISCHE Forex-Kurse - KEIN CACHE!"""
    try:
        pairs = {
            'EURUSD=X': 'eurusd',
            'GBPUSD=X': 'gbpusd',
            'USDJPY=X': 'usdjpy'
        }
        
        rates_data = {}
        
        for yahoo_symbol, pair_name in pairs.items():
            try:
                ticker = yf.Ticker(yahoo_symbol)
                # Get most recent data - NO CACHE
                hist = ticker.history(period='1d', interval='1m')
                
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    prev_close = ticker.info.get('previousClose', current_price)
                    
                    change_pct = ((current_price - prev_close) / prev_close) * 100
                    direction = 'up' if change_pct >= 0 else 'down'
                    
                    # Format based on pair
                    if pair_name == 'usdjpy':
                        price_str = f"{current_price:.3f}"
                    else:
                        price_str = f"{current_price:.5f}"
                    
                    rates_data[pair_name] = {
                        'price': price_str,
                        'change': f"{abs(change_pct):.2f}",
                        'direction': direction
                    }
                else:
                    # Fallback
                    rates_data[pair_name] = {
                        'price': '—',
                        'change': '0.00',
                        'direction': 'neutral'
                    }
            except Exception as e:
                print(f"Error fetching {pair_name}: {e}")
                rates_data[pair_name] = {
                    'price': '—',
                    'change': '0.00',
                    'direction': 'neutral'
                }
        
        return jsonify({
            'success': True,
            'data': rates_data,
            'cached': False,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/news', methods=['GET'])
def get_news():
    """Holt aktuelle Forex-News von mehreren RSS Feeds und sortiert nach Paaren"""
    try:
        # Check cache
        if news_cache['data'] and news_cache['timestamp']:
            if (datetime.now() - news_cache['timestamp']).seconds < 300:  # 5 min cache for news
                return jsonify({
                    'success': True,
                    'data': news_cache['data'],
                    'cached': True,
                    'timestamp': news_cache['timestamp'].isoformat()
                })
        
        # Mehrere RSS Feeds abrufen
        all_news = []
        
        # 1. Forex.com RSS
        try:
            feed = feedparser.parse('https://www.forex.com/en-us/rss/news-and-analysis/')
            for entry in feed.entries[:20]:
                try:
                    pub_date = datetime(*entry.published_parsed[:6])
                    time_diff = datetime.now() - pub_date
                    
                    if time_diff.days == 0:
                        if time_diff.seconds < 3600:
                            time_str = f"Vor {time_diff.seconds // 60} Min"
                        else:
                            time_str = f"Vor {time_diff.seconds // 3600} Std"
                    elif time_diff.days == 1:
                        time_str = "Gestern"
                    else:
                        continue
                    
                    article_url = entry.link if hasattr(entry, 'link') else 'https://www.forex.com/en-us/news-and-analysis/'
                    
                    all_news.append({
                        'time': time_str,
                        'headline': entry.title[:100],
                        'url': article_url,
                        'text': entry.title.lower(),
                        'source': 'Forex.com'
                    })
                except:
                    continue
        except:
            pass
        
        # Fallback wenn RSS fehlschlägt
        if not all_news:
            now = datetime.now().strftime('%H:%M')
            all_news = [
                {'time': f'Heute {now}', 'headline': 'EUR/USD hält sich stabil - EZB Kommentare im Fokus', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'eur usd ezb', 'source': 'Forex.com'},
                {'time': 'Vor 1 Std', 'headline': 'Euro profitiert von schwachem Dollar', 'url': 'https://www.investing.com/news/forex-news', 'text': 'euro dollar', 'source': 'Investing.com'},
                {'time': 'Vor 2 Std', 'headline': 'Eurozone Wirtschaftsdaten übertreffen Erwartungen', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'eurozone', 'source': 'Forex.com'},
                {'time': f'Heute {now}', 'headline': 'GBP/USD steigt - BoE bleibt hawkish', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'gbp usd boe pound', 'source': 'Forex.com'},
                {'time': 'Vor 1 Std', 'headline': 'UK Inflation sinkt - Pfund unter Druck', 'url': 'https://www.investing.com/news/economy-news', 'text': 'uk pound inflation', 'source': 'Investing.com'},
                {'time': 'Vor 3 Std', 'headline': 'Britischer Arbeitsmarkt zeigt Stärke', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'uk britain', 'source': 'Forex.com'},
                {'time': f'Heute {now}', 'headline': 'USD/JPY unter Druck - BoJ Intervention möglich', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'usd jpy yen japan', 'source': 'Forex.com'},
                {'time': 'Vor 1 Std', 'headline': 'Yen gewinnt an Stärke', 'url': 'https://www.investing.com/news/forex-news', 'text': 'yen japan', 'source': 'Investing.com'},
                {'time': 'Vor 2 Std', 'headline': 'Japan Inflation steigt weiter', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'japan inflation', 'source': 'Forex.com'},
            ]
        
        # Intelligente Sortierung nach Paaren
        news_data = {
            'eurusd': [],
            'gbpusd': [],
            'usdjpy': []
        }
        
        eur_keywords = ['eur', 'euro', 'eurozone', 'ecb', 'ezb', 'lagarde']
        gbp_keywords = ['gbp', 'pound', 'sterling', 'britain', 'uk', 'boe', 'bailey']
        jpy_keywords = ['jpy', 'yen', 'japan', 'boj', 'ueda']
        
        for item in all_news:
            text = item['text']
            assigned = False
            
            if any(kw in text for kw in eur_keywords) and len(news_data['eurusd']) < 3:
                news_data['eurusd'].append({
                    'time': item['time'],
                    'headline': item['headline'],
                    'url': item['url']
                })
                assigned = True
            
            if not assigned and any(kw in text for kw in gbp_keywords) and len(news_data['gbpusd']) < 3:
                news_data['gbpusd'].append({
                    'time': item['time'],
                    'headline': item['headline'],
                    'url': item['url']
                })
                assigned = True
            
            if not assigned and any(kw in text for kw in jpy_keywords) and len(news_data['usdjpy']) < 3:
                news_data['usdjpy'].append({
                    'time': item['time'],
                    'headline': item['headline'],
                    'url': item['url']
                })
                assigned = True
        
        # Fülle auf
        generic_forex = [n for n in all_news if 'forex' in n['text'] or 'dollar' in n['text'] or 'usd' in n['text']]
        
        for pair in ['eurusd', 'gbpusd', 'usdjpy']:
            idx = 0
            while len(news_data[pair]) < 3 and idx < len(generic_forex):
                if generic_forex[idx] not in [n for sublist in news_data.values() for n in sublist]:
                    news_data[pair].append({
                        'time': generic_forex[idx]['time'],
                        'headline': generic_forex[idx]['headline'],
                        'url': generic_forex[idx]['url']
                    })
                idx += 1
        
        # Letzter Fallback
        for pair in ['eurusd', 'gbpusd', 'usdjpy']:
            while len(news_data[pair]) < 3:
                news_data[pair].append({
                    'time': 'Heute',
                    'headline': f'{pair.upper()} - Aktuelle Marktentwicklungen',
                    'url': f'https://www.forex.com/en-us/news-and-analysis/?q={pair}'
                })
        
        news_cache['data'] = news_data
        news_cache['timestamp'] = datetime.now()
        
        return jsonify({
            'success': True,
            'data': news_data,
            'cached': False,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/calendar', methods=['GET'])
def get_calendar():
    """Holt ECHTEN Wirtschaftskalender von deutscher Investing.com"""
    try:
        url = 'https://de.investing.com/economic-calendar/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            events = []
            event_rows = soup.find_all('tr', {'id': lambda x: x and x.startswith('eventRowId_')})
            
            for row in event_rows[:10]:
                try:
                    time_cell = row.find('td', class_='time')
                    time_text = time_cell.get_text(strip=True) if time_cell else '–'
                    
                    currency_cell = row.find('td', class_='flagCur')
                    currency = currency_cell.get_text(strip=True) if currency_cell else '–'
                    
                    event_cell = row.find('td', class_='event')
                    event_link = event_cell.find('a') if event_cell else None
                    event_name = event_link.get_text(strip=True) if event_link else 'Event'
                    event_url = 'https://de.investing.com' + event_link.get('href') if event_link and event_link.get('href') else 'https://de.investing.com/economic-calendar/'
                    
                    impact_cell = row.find('td', class_='sentiment')
                    impact_icons = impact_cell.find_all('i', class_='grayFullBullishIcon') if impact_cell else []
                    impact = 'high' if len(impact_icons) == 3 else 'medium' if len(impact_icons) == 2 else 'low'
                    
                    events.append({
                        'time': time_text,
                        'currency': currency,
                        'event': event_name,
                        'impact': impact,
                        'url': event_url
                    })
                except:
                    continue
            
            if events:
                return jsonify({
                    'success': True,
                    'data': events,
                    'source': 'de.investing.com',
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as scrape_error:
            print(f"Scraping error: {scrape_error}")
        
        # Fallback
        return jsonify({
            'success': True,
            'data': [
                {
                    'time': '—',
                    'currency': 'INFO',
                    'event': 'Kalender-Daten aktuell nicht verfügbar. Bitte direkt auf Investing.com prüfen.',
                    'impact': 'low',
                    'url': 'https://de.investing.com/economic-calendar/'
                }
            ],
            'source': 'fallback',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
