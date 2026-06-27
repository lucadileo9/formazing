"""
NotionCrudOperations - Operazioni CRUD su database Not                "properties": {
                    "Stato": {
                        "status": {
                            "name": new_status
                        }
                    }
                }Questo modulo gestisce:
- Update status, codici, link formazioni
- Create nuove formazioni (futuro)
- Delete operations (futuro)
- Operazioni batch e transazioni
"""

import logging
from typing import Dict, Optional, List
from notion_client.errors import APIResponseError


logger = logging.getLogger(__name__)


class NotionCrudOperations:
    """
    Operazioni CRUD specializzate per database formazioni.
    
    RESPONSABILITÀ:
    - Update status formazioni (workflow transitions)
    - Update codici e link Teams (calendarizzazione)
    - Recupero formazioni singole per ID
    - Gestione errori operazioni critiche
    """
    
    def __init__(self, notion_client):
        """
        Inizializza CRUD operations.
        
        Args:
            notion_client: Client Notion autenticato
        """
        self.client = notion_client.get_client()
        logger.debug("NotionCrudOperations inizializzato")
    
    async def update_formazione_status(self, notion_id: str, new_status: str) -> bool:
        """
        Aggiorna status di una formazione specifica.
        
        WORKFLOW TRANSITIONS:
        - Programmata -> Calendarizzata (dopo invio notifiche)
        - Calendarizzata -> Conclusa (dopo feedback inviato)
        
        Args:
            notion_id: ID interno Notion della formazione
            new_status: Nuovo status ("Programmata", "Calendarizzata", "Conclusa")
        
        Returns:
            bool: True se aggiornamento successful
        """
        if not notion_id:
            logger.error("notion_id nullo in update_formazione_status")
            return False
            
        try:
            response = self.client.pages.update(
                page_id=notion_id,
                properties={
                    "Stato": {
                        "status": {
                            "name": new_status
                        }
                    }
                }
            )
            
            logger.info(f"Status aggiornato | ID: ...{notion_id[-8:]} | New status: {new_status}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Errore API aggiornamento status | ID: ...{notion_id[-8:]} | Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore generico aggiornamento status | ID: ...{notion_id[-8:]} | Error: {e}")
            return False
    
    async def update_codice_e_link(self, notion_id: str, codice: str, link_teams: str) -> bool:
        """
        Aggiorna codice formazione e link Teams.
        
        CALENDARIZZAZIONE WORKFLOW:
        - Genera codice univoco (es: IT-Sicurezza_Web-2024-SPRING-01)
        - Salva link Teams generato da Microsoft Graph
        
        Args:
            notion_id: ID interno Notion della formazione
            codice: Codice formazione generato
            link_teams: URL meeting Teams
        
        Returns:
            bool: True se aggiornamento successful
        """
        try:
            properties = {
                "Codice": {
                    "rich_text": [
                        {
                            "text": {
                                "content": codice
                            }
                        }
                    ]
                }
            }
            
            # Aggiungi link Teams solo se presente
            if link_teams and link_teams.strip():
                properties["Link Teams"] = {
                    "url": link_teams
                }
            
            response = self.client.pages.update(
                page_id=notion_id,
                properties=properties
            )
            
            logger.info(f"Codice e link aggiornati | ID: ...{notion_id[-8:]} | Codice: {codice}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Errore aggiornamento codice/link {notion_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore generico aggiornamento codice/link {notion_id}: {e}")
            return False
    
    async def get_formazione_by_id(self, notion_id: str, data_parser) -> Optional[Dict]:
        """
        Recupera formazione specifica per ID Notion.
        
        UTILITY per:
        - Operazioni puntuali
        - Validazione dati post-update
        - Refresh stato singola formazione
        
        Args:
            notion_id: ID interno Notion della formazione
            data_parser: Parser per conversione dati
        
        Returns:
            Dict: Formazione normalizzata o None se non trovata
        """
        logger.debug(f"Recupero formazione | ID: ...{notion_id[-8:]}")
        
        try:
            response = self.client.pages.retrieve(page_id=notion_id)
            formazione = data_parser.parse_single_formazione(response)
            
            if formazione:
                logger.debug(f"Formazione recuperata: {formazione['Nome']}")
            else:
                logger.warning(f"Formazione non parsabile: {notion_id}")
            
            return formazione
            
        except APIResponseError as e:
            logger.error(f"Errore recupero formazione {notion_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Errore generico recupero formazione {notion_id}: {e}")
            return None
    async def get_workspace_users_mapping(self) -> tuple:
        """
        Recupera tutti gli utenti del workspace Notion e restituisce due mappe:
        1. email -> id (in minuscolo)
        2. name -> id (in minuscolo)
        
        Usa la paginazione per garantire di recuperare tutti gli utenti.
        """
        email_to_id = {}
        name_to_id = {}
        try:
            has_more = True
            next_cursor = None
            
            while has_more:
                params = {}
                if next_cursor:
                    params['start_cursor'] = next_cursor
                
                # Chiamata sincrona all'API utenti di Notion
                response = self.client.users.list(**params)
                
                for user in response.get('results', []):
                    user_id = user.get('id')
                    if not user_id:
                        continue
                    
                    # Mapping per email
                    email = user.get('person', {}).get('email')
                    if email:
                        email_to_id[email.lower().strip()] = user_id
                    
                    # Mapping per nome (fallback)
                    name = user.get('name')
                    if name:
                        name_to_id[name.lower().strip()] = user_id
                
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
                
            logger.info(f"Mappatura utenti Notion completata | Trovati {len(email_to_id)} utenti con email e {len(name_to_id)} con nome")
            
        except Exception as e:
            logger.error(f"Errore nel recupero degli utenti Notion: {e}")
            
        return email_to_id, name_to_id

    async def update_multiple_fields(self, notion_id: str, updates: Dict) -> bool:
        """
        Aggiorna multipli campi in una singola operazione.
        
        OPERAZIONE ATOMICA per aggiornamenti complessi.
        
        Args:
            notion_id: ID interno Notion della formazione
            updates: Dizionario con campi da aggiornare
        
        Returns:
            bool: True se aggiornamento successful
        """
        try:
            properties = {}
            
            # Costruisci properties Notion format da updates
            for field, value in updates.items():
                if field == 'Stato':
                    properties["Stato"] = {"status": {"name": value}}
                elif field == 'Codice':
                    properties["Codice"] = {"rich_text": [{"text": {"content": value}}]}
                elif field == 'Link':
                    properties["Link"] = {"url": value}
                elif field == 'Link Teams':
                    properties["Link Teams"] = {"url": value}
                elif field == 'Partecipanti':
                    # Se value è già una lista di ID utente pre-formattata
                    if isinstance(value, list) and all(isinstance(i, dict) and 'id' in i for i in value):
                        properties["Partecipanti"] = {"people": value}
                    # Se value è una lista di partecipanti da mappare, es: [{"name": "...", "email": "..."}]
                    elif isinstance(value, list):
                        email_map, name_map = await self.get_workspace_users_mapping()
                        
                        people_list = []
                        for attendee in value:
                            email = attendee.get('email', '').lower().strip()
                            name = attendee.get('name', '').lower().strip()
                            
                            user_id = None
                            if email and email in email_map:
                                user_id = email_map[email]
                            elif name and name in name_map:
                                user_id = name_map[name]
                                
                            if user_id:
                                people_list.append({"object": "user", "id": user_id})
                            else:
                                logger.warning(f"Partecipante Teams non trovato in Notion: {attendee.get('name')} ({attendee.get('email')})")
                        
                        properties["Partecipanti"] = {"people": people_list}
                elif field == 'Numero Partecipanti':
                    properties["Numero Partecipanti"] = {"number": value}
                elif field == 'Durata':
                    properties["Durata"] = {"number": value}
                # Aggiungi altri campi se necessario
            
            response = self.client.pages.update(
                page_id=notion_id,
                properties=properties
            )
            
            logger.info(f"Multipli campi aggiornati | ID: ...{notion_id[-8:]} | Campi: {list(updates.keys())}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Errore aggiornamento multiplo {notion_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore generico aggiornamento multiplo {notion_id}: {e}")
            return False
    
    async def batch_update_status(self, formazioni_ids: List[str], new_status: str) -> Dict:
        """
        Aggiorna status per batch di formazioni.
        
        UTILE PER: Operazioni bulk (es: chiusura fine anno)
        
        Args:
            formazioni_ids: Lista ID formazioni da aggiornare
            new_status: Nuovo status per tutte
        
        Returns:
            Dict: Risultati batch (success_count, failed_ids)
        """
        logger.info(f"Batch update status | Formazioni: {len(formazioni_ids)} | Target status: {new_status}")
        
        results = {
            'success_count': 0,
            'failed_ids': [],
            'total': len(formazioni_ids)
        }
        
        for notion_id in formazioni_ids:
            success = await self.update_formazione_status(notion_id, new_status)
            if success:
                results['success_count'] += 1
            else:
                results['failed_ids'].append(notion_id)
        
        logger.info(f"Batch update completato | Successo: {results['success_count']}/{results['total']}")
        return results