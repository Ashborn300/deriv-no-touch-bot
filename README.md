# Deriv No-Touch Bot — V10 (1s)

Bot de trading automatique pour **Deriv.com** utilisant des **contrats No-Touch** avec détection de **marteaux / marteaux inversés**, **EMA100**, **RSI**, et **supports / résistances**. Barrière **inversée** automatiquement : `-1.55` sur signal haussier, `+1.55` sur signal baissier. Expiration **2 minutes**.

## ⚙️ Configuration locale
1. Copier `.env.example` en `.env` et remplir vos identifiants Deriv.
2. Installer et lancer :
   ```bash
   pip install -r requirements.txt
   python bot_notouch.py
   ```

## ☁️ Déploiement Coolify (Dockerfile App)
1. Connecter ce repo → sélectionner **Dockerfile App**.
2. Coller vos variables `.env` dans l’onglet **Environment**.
3. **Deploy** — redémarrage auto en cas d’arrêt.

## 🔍 Journal CSV
Chaque trade est enregistré dans `trades_log.csv` (heure, OPEN/CLOSE, barrière, stake, profit).

## ⚠️ Avertissement
- Utiliser d’abord en **DEMO**.
- Les indices synthétiques sont générés par RNG : **risque de perte** réel.
