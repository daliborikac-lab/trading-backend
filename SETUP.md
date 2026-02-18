# Trading Dashboard - KOMPLETTE SETUP ANLEITUNG

## BACKEND DEPLOYMENT (15 Minuten)

### Schritt 1: Render.com Account erstellen
1. Gehe auf **render.com**
2. Klicke "Get Started" → "Sign Up with GitHub" (oder Email)
3. Bestätige deine Email-Adresse

### Schritt 2: Backend deployen
1. Klicke auf **"New +"** oben rechts
2. Wähle **"Web Service"**
3. Wähle **"Build and deploy from a Git repository"**
4. Klicke **"Public Git Repository"** → Gib ein:
   ```
   https://github.com/render-examples/flask-hello-world
   ```
   (Das ist nur zum Testen - wir ersetzen es gleich)

5. **ODER EINFACHER:** Klicke **"Deploy from a GitHub repository"**
   - Verbinde dein GitHub (falls du eins hast)
   - Erstelle ein neues Repository "trading-backend"
   - Lade die Backend-Dateien hoch (app.py, requirements.txt, render.yaml)

6. **ODER AM EINFACHSTEN:**
   - Klicke "Deploy from a zip file"
   - Lade die `trading-backend.zip` hoch die ich dir gebe

### Schritt 3: Konfiguration
Setze folgendes:
- **Name:** `trading-backend` (oder ein eigener Name)
- **Region:** Frankfurt (EU)
- **Branch:** main
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Plan:** FREE

Klicke **"Create Web Service"**

### Schritt 4: Warte auf Deployment
- Render deployed automatisch (2-3 Minuten)
- Du bekommst eine URL wie: `https://trading-backend-xyz.onrender.com`
- **KOPIERE DIESE URL** - du brauchst sie gleich!

---

## DASHBOARD UPDATE (5 Minuten)

### Schritt 5: Dashboard anpassen
1. Öffne die `dashboard-live/index.html` Datei die ich dir gebe
2. Suche nach der Zeile (ganz oben im JavaScript):
   ```javascript
   const BACKEND_URL = 'https://DEINE-BACKEND-URL-HIER';
   ```
3. Ersetze `DEINE-BACKEND-URL-HIER` mit deiner echten Render-URL
4. Speichern!

### Schritt 6: Auf Netlify hochladen
1. Gehe zu deiner bestehenden Netlify-Site
2. Klicke "Deploys"
3. Ziehe den **dashboard-live** Ordner rein
4. Fertig!

---

## TESTEN

Öffne dein Dashboard:
1. Klick auf **"Kurse laden"**
2. **Es sollten echte Live-Kurse erscheinen**
3. **News sollten aktuell sein**
4. **Alles klickbar**

---

## TROUBLESHOOTING

**Backend-URL funktioniert nicht?**
- Gehe zu Render.com → Logs
- Schau ob Fehler da sind
- Backend braucht 1-2 Minuten zum Aufwärmen beim ersten Aufruf

**Kurse laden nicht?**
- Öffne Browser Console (F12)
- Schau ob CORS-Fehler da sind
- Prüfe ob Backend-URL korrekt eingesetzt ist

**Noch Fragen?**
- Schreib mir hier - ich helfe!
