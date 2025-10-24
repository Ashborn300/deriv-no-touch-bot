# Deriv No-Touch Bot — V5 (Martingale 2-6-18-60)

Bot Deriv (Volatility 10 1s) No-Touch, barrière inversée (`-` sur marteau haussier, `+` sur marteau inversé), EMA100/RSI/S&R, **martingale** : 2 → 6 → 18 → 60 → reset.

## Configuration
1. Copier `.env.example` en `.env` et remplir `DERIV_APP_ID` & `DERIV_API_TOKEN` (démo d'abord)
2. Installer et lancer localement :
   ```bash
   pip install -r requirements.txt
   python bot_notouch.py
   ```

## Coolify (Dockerfile App)
- Type : **Dockerfile App**
- Env : coller le contenu de `.env`
- Deploy : auto-restart + logs

## Journal CSV
Chaque trade est loggé dans `trades_log.csv` (OPEN/CLOSE, barrière, stake, profit, step martingale).

## Avertissement
La martingale peut accélérer les pertes. À utiliser **uniquement** en démo.
