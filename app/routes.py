#!/usr/bin/env python3
"""
🌐 Routes Flask per Formazing

Gestisce tutte le pagine web dell'applicazione:
- Homepage con login
- Dashboard formazioni  
- API endpoints per operazioni
- Pagine di gestione e preview
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import auth
from app.services.notion import NotionService, NotionServiceError
from app.services.training_service import TrainingService, TrainingServiceError
from config import Config
import logging
import traceback
import asyncio
import yaml
import os

# Logger per routes (configurazione centralizzata già attiva)
logger = logging.getLogger(__name__)

# Blueprint principale per le routes
main = Blueprint('main', __name__)


@main.route('/')
def home():
    """
    Homepage con form di login.
    Se già autenticato, redirect alla dashboard.
    """
    return render_template('pages/login.html', 
                         title='Formazing - Gestione Formazioni',
                         app_name='Formazing')


@main.route('/dashboard')
@auth.login_required
async def dashboard():
    """Dashboard principale con formazioni organizzate per status (Flask Async)."""
    try:
        logger.info("📊 Caricamento dashboard - richiesta ricevuta")
        
        # Inizializzazione NotionService (via Singleton)
        training_service = TrainingService.get_instance()
        notion_service = training_service.notion_service
        logger.debug("✅ NotionService recuperato da TrainingService Singleton")
        
        # PERFORMANCE BOOST: Chiamate parallele con asyncio.gather()
        logger.debug("🔄 Recupero formazioni da Notion (chiamate parallele)...")
        formazioni_results = await asyncio.gather(
            notion_service.get_formazioni_by_status('Programmata'),
            notion_service.get_formazioni_by_status('Calendarizzata'),
            notion_service.get_formazioni_by_status('Conclusa'),
            return_exceptions=True  # Continua anche se una chiamata fallisce
        )
        
        # Gestione risultati con error handling
        formazioni_programmata = formazioni_results[0] if not isinstance(formazioni_results[0], Exception) else []
        formazioni_calendarizzata = formazioni_results[1] if not isinstance(formazioni_results[1], Exception) else []
        formazioni_conclusa = formazioni_results[2] if not isinstance(formazioni_results[2], Exception) else []
        
        # Log eventuali errori nelle chiamate Notion
        for idx, result in enumerate(formazioni_results):
            if isinstance(result, Exception):
                status = ['Programmata', 'Calendarizzata', 'Conclusa'][idx]
                logger.error(f"❌ Errore recupero formazioni '{status}': {result}")
        
        # Statistiche con null safety
        stats = {
            'programmata': len(formazioni_programmata or []),
            'calendarizzata': len(formazioni_calendarizzata or []),
            'conclusa': len(formazioni_conclusa or []),
        }
        stats['totale'] = stats['programmata'] + stats['calendarizzata'] + stats['conclusa']
        
        logger.info(f"✅ Dashboard caricata | Totale: {stats['totale']} | "
                   f"Programmata: {stats['programmata']} | Calendarizzata: {stats['calendarizzata']} | "
                   f"Conclusa: {stats['conclusa']}")
        
        # Usa il nuovo template atomic design
        return render_template('pages/dashboard.html',
                             formazioni_programmata=formazioni_programmata or [],
                             formazioni_calendarizzata=formazioni_calendarizzata or [],
                             formazioni_conclusa=formazioni_conclusa or [],
                             stats=stats,
                             title='Dashboard - Formazing')
                             
    except NotionServiceError as e:
        # Errore specifico NotionService
        logger.error(f"❌ NotionService error nella dashboard: {e}", exc_info=True)
        flash(f"❌ Errore servizio Notion: {e}", 'error')
        return redirect(url_for('main.home'))
        
    except Exception as e:
        # Errore generico
        logger.error(f"❌ Errore imprevisto nella dashboard: {e}", exc_info=True)
        flash(f"❌ Errore imprevisto: {e}", 'error')
        return redirect(url_for('main.home'))


@main.route('/tutorial')
def tutorial():
    """Pagina Tutorial e FAQ con dati da YAML."""
    try:
        faq_path = os.path.join(Config.BASE_DIR, 'config', 'faqs.yaml')
        with open(faq_path, 'r', encoding='utf-8') as f:
            faq_data = yaml.safe_load(f)
        faqs = faq_data.get('faqs', [])
    except Exception as e:
        logger.error(f"❌ Errore caricamento FAQ: {e}")
        faqs = []
        
    return render_template('pages/tutorial.html', 
                         title='Tutorial & FAQ - Formazing',
                         faqs=faqs)


# === PAGINE PREVIEW CON FORM CONFERMA ===

@main.route('/preview/notification/<training_id>')
@auth.login_required
def preview_notification_page(training_id):
    """Pagina preview calendarizzazione con form conferma."""
    try:
        logger.info(f"� Preview calendarizzazione richiesta | Training ID: {training_id}")
        
        # Usa Singleton TrainingService
        training_service = TrainingService.get_instance()
        preview_data = asyncio.run(training_service.generate_preview(training_id))
        
        logger.info(f"✅ Preview generata | Formazione: {preview_data['training'].get('Nome', 'N/A')}")
        
        # Renderizza template preview
        return render_template('pages/preview.html',
                             preview=preview_data,
                             action_type='notification',
                             action_title='Calendarizzazione Formazione',
                             action_icon='📅',
                             training_id=training_id,
                             title=f"Preview - {preview_data['training']['Nome']}")
        
    except TrainingServiceError as e:
        logger.error(f"❌ Errore preview calendarizzazione | Training ID: {training_id} | Error: {e}")
        flash(f'❌ Errore: {e}', 'error')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"❌ Errore imprevisto preview calendarizzazione | Training ID: {training_id} | Error: {e}", exc_info=True)
        flash(f'❌ Errore imprevisto: {e}', 'error')
        return redirect(url_for('main.dashboard'))


@main.route('/preview/feedback/<training_id>')
@auth.login_required
def preview_feedback_page(training_id):
    """Pagina preview richiesta feedback con form conferma."""
    try:
        logger.info(f"� Preview feedback richiesta | Training ID: {training_id}")
        
        # Usa Singleton TrainingService
        training_service = TrainingService.get_instance()
        preview_data = asyncio.run(training_service.generate_feedback_preview(training_id))
        
        logger.info(f"✅ Preview feedback generata | Formazione: {preview_data['training'].get('Nome', 'N/A')}")
        
        # Renderizza template preview
        return render_template('pages/preview.html',
                             preview=preview_data,
                             action_type='feedback',
                             action_title='Richiesta Feedback',
                             action_icon='📝',
                             training_id=training_id,
                             title=f"Preview Feedback - {preview_data['training']['Nome']}")
        
    except TrainingServiceError as e:
        logger.error(f"❌ Errore preview feedback | Training ID: {training_id} | Error: {e}")
        flash(f'❌ Errore: {e}', 'error')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"❌ Errore imprevisto preview feedback | Training ID: {training_id} | Error: {e}", exc_info=True)
        flash(f'❌ Errore imprevisto: {e}', 'error')
        return redirect(url_for('main.dashboard'))


@main.route('/confirm/notification/<training_id>', methods=['POST'])
@auth.login_required
def confirm_notification(training_id):
    """Conferma ed esegue calendarizzazione (chiamata da form preview)."""
    try:
        logger.info(f"🚀 Conferma calendarizzazione | Training ID: {training_id}")
        
        # Usa Singleton TrainingService
        training_service = TrainingService.get_instance()
        result = asyncio.run(training_service.send_training_notification(training_id))
        
        logger.info(f"✅ Calendarizzazione completata | Training ID: {training_id} | "
                   f"Codice: {result.get('codice_generato', 'N/A')} | "
                   f"Gruppi notificati: {len(result.get('telegram_results', {}))}")
        
        flash('✅ Comunicazione inviata con successo! La formazione è stata calendarizzata.', 'success')
        return redirect(url_for('main.dashboard'))
        
    except TrainingServiceError as e:
        logger.error(f"❌ Errore conferma calendarizzazione | Training ID: {training_id} | Error: {e}")
        flash(f'❌ Errore: {e}', 'error')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"❌ Errore imprevisto conferma calendarizzazione | Training ID: {training_id} | Error: {e}", exc_info=True)
        flash(f'❌ Errore imprevisto: {e}', 'error')
        return redirect(url_for('main.dashboard'))


@main.route('/confirm/feedback/<training_id>', methods=['POST'])
@auth.login_required
def confirm_feedback(training_id):
    """Conferma ed esegue invio feedback (chiamata da form preview)."""
    try:
        logger.info(f"📝 Conferma invio feedback | Training ID: {training_id}")
        
        # Usa Singleton TrainingService
        training_service = TrainingService.get_instance()
        result = asyncio.run(training_service.send_feedback_request(training_id))
        
        logger.info(f"✅ Feedback inviato con successo | Training ID: {training_id} | "
                   f"Gruppi notificati: {len(result.get('telegram_results', {}))}")
        
        flash('✅ Richiesta feedback inviata con successo! La formazione è stata conclusa.', 'success')
        return redirect(url_for('main.dashboard'))
        
    except TrainingServiceError as e:
        logger.error(f"❌ Errore conferma feedback | Training ID: {training_id} | Error: {e}")
        flash(f'❌ Errore: {e}', 'error')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"❌ Errore imprevisto conferma feedback | Training ID: {training_id} | Error: {e}", exc_info=True)
        flash(f'❌ Errore imprevisto: {e}', 'error')
        return redirect(url_for('main.dashboard'))
