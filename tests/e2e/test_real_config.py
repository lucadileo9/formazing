#!/usr/bin/env python3
"""
Test di verifica configurazione reale per Notion e Telegram
==========================================================

Questo script verifica che:
1. NotionService si connetta al database reale
2. TelegramService si connetta al bot reale
3. I gruppi Telegram siano configurati correttamente
4. I token e ID siano validi

Usage: python test_real_config.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Aggiungi la directory root del progetto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.notion import NotionService
from app.services.telegram_service import TelegramService
from config import Config

# Configura logging per output pulito
logging.basicConfig(
    level=logging.WARNING,  # Nascondi log INFO per output più pulito
    format='%(levelname)s: %(message)s'
)

async def verify_notion_connection():
    """Verifies the connection to the Notion service by fetching data.
    This asynchronous function performs a series of steps to ensure that the
    NotionService is correctly configured and can communicate with the Notion API.
    The process includes:
    1. Initializing the `NotionService`.
    2. Iterating through predefined statuses ('Programmata', 'Calendarizzata', 'Conclusa').
    3. For each status, fetching the corresponding "formazioni" (training sessions).
    4. Printing the number of sessions found for each status to the console.
    5. Displaying details of the first session found for each status as an example.
    6. Calculating and printing the total number of sessions found across all statuses.
    The function prints detailed logs of its progress and any errors encountered
    to the standard output.
    Returns:
        bool: True if the entire process completes successfully, False if any
              exception is raised during service initialization or data fetching.
    """
    print("🔍 Testing Notion Service...")
    
    try:
        # Inizializza NotionService
        notion = NotionService()
        print("✅ NotionService inizializzato con successo")
        
        # Testa connessione recuperando formazioni
        print("📊 Recupero formazioni per status...")
        
        # Test per ogni status principale
        statuses = ['Programmata', 'Calendarizzata', 'Conclusa']
        total_formazioni = 0
        
        for status in statuses:
            try:
                formazioni = await notion.get_formazioni_by_status(status)
                count = len(formazioni)
                total_formazioni += count
                print(f"   📚 Status '{status}': {count} formazioni")
                
                # Mostra dettagli della prima formazione se presente
                if formazioni:
                    esempio = formazioni[0]
                    nome = esempio.get('Nome', 'N/A')
                    area = esempio.get('Area', ['N/A'])
                    area_str = ', '.join(area) if isinstance(area, list) else str(area)
                    data = esempio.get('Data', 'N/A')
                    print(f"      → Esempio: {nome} | Area: {area_str} | Data: {data}")
            except Exception as e:
                print(f"   ❌ Errore recupero status '{status}': {e}")
                return False
        
        print(f"✅ Notion: {total_formazioni} formazioni totali trovate")
        return True
        
    except Exception as e:
        print(f"❌ Errore NotionService: {e}")
        return False

async def verify_telegram_connection():
    """Verifies the Telegram service configuration and connection.
    This asynchronous function performs a comprehensive end-to-end check of the
    Telegram integration. It follows these steps:
    1.  Initializes the `TelegramService` using the bot token and configuration
        file paths from the global `Config` object.
    2.  Connects to the Telegram API to verify the bot token is valid
    3.  Reads and parses the `telegram_groups.json` file, displaying the
        configured groups and their associated chat IDs.
    The function prints detailed feedback to the console at each step.
    Returns:
        bool: True if the core configuration (initialization, bot connection,
              group file parsing) is successful, False if any of these steps fail.
              The success of sending the optional test message does not affect
              the final return value.
    """
    print("\n🤖 Testing Telegram Service...")
    
    try:
        # Inizializza NotionService (necessario per TelegramService)
        notion_service = NotionService()
        print("✅ NotionService inizializzato")
        
        # Inizializza TelegramService con token da config
        telegram_token = Config.TELEGRAM_BOT_TOKEN
        if not telegram_token:
            print("❌ TELEGRAM_BOT_TOKEN non configurato")
            return False
            
        telegram = TelegramService(
            token=telegram_token,
            notion_service=notion_service,  # ✅ Passa NotionService
            groups_config_path=Config.TELEGRAM_GROUPS_CONFIG,
            templates_config_path=Config.TELEGRAM_TEMPLATES_CONFIG
        )
        print("✅ TelegramService inizializzato con successo")
        
        # Ottieni info del bot usando l'API diretta di python-telegram-bot
        try:
            import telegram as tg
            async with tg.Bot(token=telegram_token) as bot:
                bot_info = await bot.get_me()
            print(f"✅ Bot connesso: @{bot_info.username} (ID: {bot_info.id})")
            print(f"   📛 Nome: {bot_info.first_name}")
        except Exception as e:
            print(f"❌ Errore connessione bot: {e}")
            return False
        
        # Verifica gruppi configurati
        print("📱 Verifica gruppi Telegram configurati...")
        import json
        
        # Leggi configurazione gruppi da JSON
        groups_file = project_root / "config" / "telegram_groups.json"
        try:
            with open(groups_file, 'r', encoding='utf-8') as f:
                TELEGRAM_GROUPS = json.load(f)
            
            # Filtra commenti (chiavi che iniziano con _)
            groups_filtered = {k: v for k, v in TELEGRAM_GROUPS.items() if not k.startswith('_')}
            
            for gruppo_nome, chat_id in groups_filtered.items():
                print(f"   🗂️ {gruppo_nome}: {chat_id}")
            
            print(f"✅ {len(groups_filtered)} gruppi configurati")
            TELEGRAM_GROUPS = groups_filtered  # Usa solo gruppi validi
        except Exception as e:
            print(f"❌ Errore lettura gruppi Telegram: {e}")
            return False
                
        return True
        
    except Exception as e:
        print(f"❌ Errore TelegramService: {e}")
        return False

def verify_environment_config():
    """Verifies that required environment variables for the application are set.
    This function checks for the existence of `NOTION_TOKEN`, `NOTION_DATABASE_ID`,
    and `TELEGRAM_BOT_TOKEN` in the environment. It prints the status of each
    variable to standard output. For security, if a variable is set, only a
    masked version of its value is displayed.
    If any variables are missing, it prints a summary of the missing variables
    and suggests checking the `.env` file.
    Returns:
        bool: True if all necessary environment variables are set, False otherwise.
    """
    print("\n🔧 Verifica variabili d'ambiente...")
    
    required_vars = [
        'NOTION_TOKEN',
        'NOTION_DATABASE_ID', 
        'TELEGRAM_BOT_TOKEN'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: Non configurata")
        else:
            # Mostra solo primi e ultimi caratteri per sicurezza
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"✅ {var}: {masked}")
    
    if missing_vars:
        print(f"\n❌ Variabili mancanti: {', '.join(missing_vars)}")
        print("💡 Verifica il file .env nella directory root del progetto")
        return False
    
    print("✅ Tutte le variabili d'ambiente sono configurate")
    return True

async def main():
    """Esegue tutti i test di verifica configurazione"""
    print("🚀 FORMAZING - Test Configurazione Reale")
    print("=" * 50)
    
    # 1. Verifica environment
    env_ok = verify_environment_config()
    if not env_ok:
        print("\n❌ Configurazione environment fallita. Impossibile continuare.")
        return False
    
    # 2. Verifica Notion
    notion_ok = await verify_notion_connection()
    
    # 3. Verifica Telegram  
    telegram_ok = await verify_telegram_connection()
    
    # 4. Risultato finale
    print("\n" + "=" * 50)
    print("📋 RISULTATO FINALE:")
    print(f"🔧 Environment: {'✅ OK' if env_ok else '❌ FAIL'}")
    print(f"📊 Notion: {'✅ OK' if notion_ok else '❌ FAIL'}")
    print(f"🤖 Telegram: {'✅ OK' if telegram_ok else '❌ FAIL'}")
    
    if env_ok and notion_ok and telegram_ok:
        print("\n🎉 Configurazione completa: TUTTO FUNZIONA!")
        print("📱 Pronto per test di integrazione reale")
        return True
    else:
        print("\n❌ Alcuni servizi hanno problemi. Controlla la configurazione.")
        return False

if __name__ == "__main__":
    try:
        # Esegui test (Config carica automaticamente le env vars)
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrotto dall'utente")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Errore imprevisto: {e}")
        sys.exit(1)