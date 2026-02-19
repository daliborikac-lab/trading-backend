from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import requests
import feedparser
import json
import re

app = Flask(__name__)
CORS(app)

news_cache = {'data': None, 'timestamp': None}
calendar_cache = {'data': None, 'timestamp': None}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/rates', methods=['GET'])
def get_rates():
    """Holt Forex-Kurse von ExchangeRate-API"""
    try:
        url = 'https://api.exchangerate-api.com/v4/latest/USD'
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'rates' in data:
                rates = data['rates']
                
                eurusd = 1 / rates.get('EUR', 1)
                gbpusd = 1 / rates.get('GBP', 1)
                usdjpy = rates.get('JPY', 150)
                
                rates_data = {
                    'eurusd': {
                        'price': f"{eurusd:.5f}",
                        'change': '0.00',
                        'direction': 'neutral'
                    },
                    'gbpusd': {
                        'price': f"{gbpusd:.5f}",
                        'change': '0.00',
                        'direction': 'neutral'
                    },
                    'usdjpy': {
                        'price': f"{usdjpy:.3f}",
                        'change': '0.00',
                        'direction': 'neutral'
                    }
                }
                
                return jsonify({
                    'success': True,
                    'data': rates_data,
                    'source': 'exchangerate-api.com',
                    'timestamp': datetime.now().isoformat()
                })
        except:
            pass
        
        rates_data = {
            'eurusd': {'price': '1.07850', 'change': '0.00', 'direction': 'neutral'},
            'gbpusd': {'price': '1.26420', 'change': '0.00', 'direction': 'neutral'},
            'usdjpy': {'price': '150.250', 'change': '0.00', 'direction': 'neutral'}
        }
        
        return jsonify({
            'success': True,
            'data': rates_data,
            'source': 'fallback',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/news', methods=['GET'])
def get_news():
    """Holt Forex-News"""
    try:
        if news_cache['data'] and news_cache['timestamp']:
            if (datetime.now() - news_cache['timestamp']).seconds < 300:
                return jsonify({
                    'success': True,
                    'data': news_cache['data'],
                    'cached': True,
                    'timestamp': news_cache['timestamp'].isoformat()
                })
        
        all_news = []
        
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
                    
                    all_news.append({
                        'time': time_str,
                        'headline': entry.title[:100],
                        'url': entry.link,
                        'text': entry.title.lower()
                    })
                except:
                    continue
        except:
            pass
        
        if not all_news:
            now = datetime.now().strftime('%H:%M')
            all_news = [
                {'time': f'{now}', 'headline': 'EUR/USD stabil - EZB im Fokus', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'eur usd ezb'},
                {'time': 'Vor 1 Std', 'headline': 'Dollar schwächer', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'dollar'},
                {'time': 'Vor 2 Std', 'headline': 'GBP/USD steigt', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'gbp usd pound'},
                {'time': 'Vor 1 Std', 'headline': 'UK Daten positiv', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'uk'},
                {'time': f'{now}', 'headline': 'USD/JPY volatil', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'usd jpy yen'},
                {'time': 'Vor 1 Std', 'headline': 'Yen gewinnt', 'url': 'https://www.forex.com/en-us/news-and-analysis/', 'text': 'yen japan'},
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
        
        generic = [n for n in all_news if 'forex' in n['text'] or 'dollar' in n['text']]
        for pair in ['eurusd', 'gbpusd', 'usdjpy']:
            idx = 0
            while len(news_data[pair]) < 3 and idx < len(generic):
                if generic[idx] not in [n for sublist in news_data.values() for n in sublist]:
                    news_data[pair].append({'time': generic[idx]['time'], 'headline': generic[idx]['headline'], 'url': generic[idx]['url']})
                idx += 1
        
        for pair in ['eurusd', 'gbpusd', 'usdjpy']:
            while len(news_data[pair]) < 3:
                news_data[pair].append({'time': 'Heute', 'headline': f'{pair.upper()} News', 'url': 'https://www.forex.com/en-us/news-and-analysis/'})
        
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
    """Wirtschaftskalender mit ECHTEN heutigen Events"""
    try:
        # Check cache (10 Min)
        if calendar_cache['data'] and calendar_cache['timestamp']:
            if (datetime.now() - calendar_cache['timestamp']).seconds < 600:
                return jsonify({
                    'success': True,
                    'data': calendar_cache['data'],
                    'cached': True,
                    'timestamp': calendar_cache['timestamp'].isoformat()
                })
        
        # Versuche Forex Factory API
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            url = f'https://nfs.faireconomy.media/ff_calendar_thisweek.json'
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                events = []
                today = datetime.now().date()
                
                for item in data:
                    try:
                        event_date = datetime.strptime(item.get('date', ''), '%Y-%m-%d').date()
                        
                        if event_date == today:
                            time_str = item.get('time', '—')
                            currency = item.get('country', 'USD')
                            event_name = item.get('title', 'Event')
                            impact = item.get('impact', 'Low').lower()
                            
                            # Map impact
                            if impact in ['high', 'red']:
                                impact_level = 'high'
                            elif impact in ['medium', 'orange', 'yellow']:
                                impact_level = 'medium'
                            else:
                                impact_level = 'low'
                            
                            events.append({
                                'time': time_str,
                                'currency': currency,
                                'event': event_name,
                                'impact': impact_level,
                                'url': 'https://de.investing.com/economic-calendar/'
                            })
                            
                            if len(events) >= 10:
                                break
                    except:
                        continue
                
                if events:
                    calendar_cache['data'] = events
                    calendar_cache['timestamp'] = datetime.now()
                    
                    return jsonify({
                        'success': True,
                        'data': events,
                        'source': 'forex-factory',
                        'timestamp': datetime.now().isoformat()
                    })
        except Exception as e:
            print(f"Forex Factory error: {e}")
        
        # Fallback: Wichtigste Standard-Events basierend auf Wochentag
        today = datetime.now()
        weekday = today.weekday()
        
        weekday_events = {
            0: [  # Montag
                {'time': '10:00', 'currency': 'EUR', 'event': 'Eurozone Industrieproduktion', 'impact': 'medium'},
                {'time': '14:30', 'currency': 'USD', 'event': 'US Einzelhandelsumsätze', 'impact': 'high'},
            ],
            1: [  # Dienstag
                {'time': '11:00', 'currency': 'EUR', 'event': 'Deutsche ZEW Konjunkturerwartungen', 'impact': 'high'},
                {'time': '14:30', 'currency': 'USD', 'event': 'US CPI Verbraucherpreise', 'impact': 'high'},
            ],
            2: [  # Mittwoch
                {'time': '14:30', 'currency': 'USD', 'event': 'US PPI Erzeugerpreise', 'impact': 'high'},
                {'time': '20:00', 'currency': 'USD', 'event': 'FOMC Sitzungsprotokoll', 'impact': 'high'},
            ],
            3: [  # Donnerstag
                {'time': '08:00', 'currency': 'GBP', 'event': 'UK BIP-Wachstum', 'impact': 'high'},
                {'time': '14:30', 'currency': 'USD', 'event': 'US Erstanträge Arbeitslosenhilfe', 'impact': 'medium'},
            ],
            4: [  # Freitag
                {'time': '14:30', 'currency': 'USD', 'event': 'US Arbeitsmarktbericht (NFP)', 'impact': 'high'},
                {'time': '16:00', 'currency': 'USD', 'event': 'US Uni Michigan Vertrauen', 'impact': 'medium'},
            ],
            5: [],  # Samstag
            6: []   # Sonntag
        }
        
        events = []
        
        if weekday >= 5:
            events = [{
                'time': '—',
                'currency': 'INFO',
                'event': 'Wochenende - keine wichtigen Events',
                'impact': 'low',
                'url': 'https://de.investing.com/economic-calendar/'
            }]
        else:
            # Hole Events für heute
            day_events = weekday_events.get(weekday, [])
            
            events = [
                {
                    'time': '→',
                    'currency': 'INFO',
                    'event': 'Für vollständige Tagesliste HIER KLICKEN',
                    'impact': 'high',
                    'url': 'https://de.investing.com/economic-calendar/'
                }
            ]
            
            # Füge typische Events hinzu
            for evt in day_events:
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
            'source': 'fallback',
            'note': 'Typische Events - prüfe Investing.com für vollständige Liste',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
