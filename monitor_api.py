#!/usr/bin/env python3
"""
Steam Deck Refurbished Monitor - Version API
Utilise l'API officielle Steam (méthode la plus fiable et rapide).
Inspiré de github.com/oblassgit/refurbished-steam-deck-notifier
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# === CONFIGURATION ===

# Pays (codes: FR, DE, US, UK, etc.)
COUNTRY_CODE = os.environ.get("COUNTRY_CODE", "FR")

# Notification Signal via CallMeBot (recommandé)
SIGNAL_PHONE = os.environ.get("SIGNAL_PHONE", "")  # Format: +33612345678
SIGNAL_APIKEY = os.environ.get("SIGNAL_APIKEY", "")

# Notification Discord (optionnel)
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

# API Steam
STEAM_API_URL = "https://api.steampowered.com/IPhysicalGoodsService/CheckInventoryAvailableByPackage/v1"

# Package IDs des Steam Deck Refurbished
STEAM_DECK_PACKAGES = {
    "903905": {"name": "Steam Deck 64GB LCD", "storage": "64GB", "type": "LCD"},
    "903906": {"name": "Steam Deck 256GB LCD", "storage": "256GB", "type": "LCD"},
    "903907": {"name": "Steam Deck 512GB LCD", "storage": "512GB", "type": "LCD"},
    "1202542": {"name": "Steam Deck 512GB OLED", "storage": "512GB", "type": "OLED"},
    "1202547": {"name": "Steam Deck 1TB OLED", "storage": "1TB", "type": "OLED"},
}

STORE_URL = "https://store.steampowered.com/sale/steamdeckrefurbished"


def check_stock(package_id: str, country: str = "FR"):
    """Vérifie le stock d'un package via l'API Steam."""
    url = f"{STEAM_API_URL}?origin=https://store.steampowered.com&country_code={country}&packageid={package_id}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("response", {}).get("inventory_available", False)
    except Exception as e:
        print(f"   ⚠️  Erreur API pour {package_id}: {e}")
        return None


def send_signal(message: str) -> bool:
    """Envoie une notification Signal via CallMeBot."""
    if not all([SIGNAL_PHONE, SIGNAL_APIKEY]):
        return False

    try:
        # API CallMeBot pour Signal
        url = "https://signal.callmebot.com/signal/send.php"
        params = {
            "phone": SIGNAL_PHONE,
            "apikey": SIGNAL_APIKEY,
            "text": message,
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        print(f"   📱 Signal envoyé à {SIGNAL_PHONE}")
        return True
    except Exception as e:
        print(f"   ❌ Erreur Signal: {e}")
        return False


def send_discord(message: str, models_available: list) -> bool:
    """Envoie une notification Discord."""
    if not DISCORD_WEBHOOK:
        return False

    try:
        embed = {
            "title": "🎮 Steam Deck Disponible!",
            "description": message,
            "color": 0x00FF00,  # Vert
            "fields": [
                {"name": model, "value": "✅ EN STOCK", "inline": True}
                for model in models_available
            ],
            "url": STORE_URL,
            "timestamp": datetime.utcnow().isoformat(),
        }

        payload = {"embeds": [embed]}
        response = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()

        print("   📢 Notification Discord envoyée")
        return True
    except Exception as e:
        print(f"   ❌ Erreur Discord: {e}")
        return False


def load_previous_state() -> dict:
    """Charge l'état précédent depuis un fichier."""
    state_file = Path(__file__).parent / f"state_{COUNTRY_CODE}.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict):
    """Sauvegarde l'état actuel."""
    state_file = Path(__file__).parent / f"state_{COUNTRY_CODE}.json"
    state_file.write_text(json.dumps(state, indent=2))


def main():
    print("=" * 60)
    print("🎮 Steam Deck Refurbished Monitor - API Edition")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌍 Pays: {COUNTRY_CODE}")
    print("=" * 60)

    previous_state = load_previous_state()
    current_state = {}
    available_models = []
    newly_available = []

    print("\n📊 Vérification du stock:\n")

    for pkg_id, info in STEAM_DECK_PACKAGES.items():
        available = check_stock(pkg_id, COUNTRY_CODE)

        if available is None:
            status = "⚠️  Erreur"
            current_state[pkg_id] = previous_state.get(pkg_id, False)
        else:
            current_state[pkg_id] = available
            if available:
                status = "✅ EN STOCK"
                available_models.append(info["name"])

                # Vérifier si c'est nouveau
                if not previous_state.get(pkg_id, False):
                    newly_available.append(info["name"])
            else:
                status = "❌ Épuisé"

        print(f"   {info['name']:25} {status}")

    # Sauvegarder l'état
    save_state(current_state)

    # Notifications si nouveau stock
    if newly_available:
        print("\n" + "🚨" * 20)
        print("   NOUVEAU STOCK DÉTECTÉ!")
        print("🚨" * 20)

        models_text = "\n".join([f"• {m}" for m in newly_available])

        # Signal
        if SIGNAL_PHONE:
            signal_message = f"""🎮 STEAM DECK EN STOCK!

{models_text}

👉 {STORE_URL}"""
            send_signal(signal_message)

        # Discord
        if DISCORD_WEBHOOK:
            send_discord(f"Nouveau stock détecté pour {COUNTRY_CODE}!", newly_available)

    elif available_models:
        print(f"\n📦 {len(available_models)} modèle(s) en stock (pas de changement)")
    else:
        print("\n😴 Aucun modèle disponible")

    print("\n✅ Vérification terminée")
    return 0 if not newly_available else 0


if __name__ == "__main__":
    sys.exit(main())
