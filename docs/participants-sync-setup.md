# Guida per il Test e Setup della Sincronizzazione Partecipanti

Questa documentazione spiega come configurare e testare la funzionalità di sincronizzazione manuale dei partecipanti da Microsoft Teams a Notion, inclusi i permessi necessari lato Notion e Microsoft Graph API.

---

## 1. Configurazione lato Notion

Per salvare i partecipanti all'interno della pagina Notion della formazione, è necessario aggiungere una nuova colonna nel database Notion e configurare i permessi del token d'integrazione.

### A. Aggiungere la colonna `Partecipanti`
1. Apri il database delle formazioni su Notion.
2. Clicca su `+` per aggiungere una nuova proprietà.
3. Configura la colonna come segue:
   - **Nome**: `Partecipanti`
   - **Tipo**: `Persone` (People)

### B. Configurare i permessi del Token d'Integrazione
L'applicazione Formazing deve poter leggere l'elenco degli utenti di Notion per poter associare le email/nomi estratti da Teams agli account Notion reali del workspace.
1. Accedi a [Notion My Integrations](https://www.notion.so/my-integrations).
2. Seleziona l'integrazione configurata nel file `.env` tramite il campo `NOTION_TOKEN`.
3. Sotto la scheda **Capabilities** (Funzionalità), assicurati che la seguente opzione sia abilitata:
   - **Read user information (including email addresses)** (Leggi le informazioni dell'utente, inclusi gli indirizzi email).
4. Salva le modifiche.

---

## 2. Configurazione lato Microsoft Azure (Graph API)

La sincronizzazione effettua chiamate a Microsoft Graph API per conto dell'applicazione stessa (tramite Client Credentials Flow, usando Client ID e Client Secret). Per questo motivo, sono richiesti **permessi di tipo Applicazione** (Application Permissions) nel portale Azure AD.

### A. Aggiungere i permessi in Azure AD
1. Accedi al portale di [Azure Portal](https://portal.azure.com/).
2. Vai su **Azure Active Directory** (o Entra ID) -> **App registrations** (Registrazioni app).
3. Seleziona l'applicazione registrata per Formazing (corrispondente al tuo `MICROSOFT_CLIENT_ID`).
4. Nel menu laterale, seleziona **API permissions** -> **Add a permission** -> **Microsoft Graph**.
5. Seleziona **Application permissions** (Permessi applicazione) e aggiungi i seguenti permessi:
   - **`OnlineMeetings.Read.All`** (o `OnlineMeetings.ReadWrite.All`) — Per cercare la riunione online tramite il link Teams (`joinWebUrl`).
   - **`OnlineMeetingArtifact.Read.All`** — Fondamentale per scaricare i report di presenza della riunione.
   - **`User.Read.All`** — Consente all'app di leggere le informazioni degli utenti associati ai partecipanti.
6. Clicca sul pulsante **"Grant admin consent for [Nome Organizzazione]"** (pulsante con la spunta verde) per approvare i permessi a livello di tenant.

### B. Configurazione della Application Access Policy in Teams (PowerShell)
Di default, in Microsoft 365, un'applicazione con permessi applicativi non è autorizzata ad accedere ai meeting degli utenti a meno che non venga definita una policy. Se l'API Graph risponde con errori del tipo `403 Forbidden` o `404 Not Found`, l'amministratore IT dell'organizzazione dovrà eseguire i seguenti passaggi in **PowerShell**:

1. Apri PowerShell come amministratore ed installa il modulo di Teams (se non già presente):
   ```powershell
   Install-Module -Name MicrosoftTeams -Force -AllowClobber
   ```
2. Connettiti a Microsoft Teams:
   ```powershell
   Connect-MicrosoftTeams
   ```
3. Crea la policy che associa l'applicazione registrata:
   ```powershell
   # Sostituisci YOUR_CLIENT_ID con il valore di MICROSOFT_CLIENT_ID presente nel tuo .env
   New-CsApplicationAccessPolicy -Identity "FormazingSyncPolicy" -AppIds "YOUR_CLIENT_ID" -Description "Consenti all'app Formazing di scaricare i report delle presenze dei meeting"
   ```
4. Assegna la policy all'account dell'organizzatore (la mail configurata in `MICROSOFT_USER_EMAIL` nel tuo `.env`):
   ```powershell
   # Sostituisci con la mail configurata in .env
   Grant-CsApplicationAccessPolicy -PolicyName "FormazingSyncPolicy" -Identity "lucadileo@jemore.it"
   ```

---

## 3. Flusso di Test Passo-Passo

Una volta completata la configurazione dei permessi Notion e Microsoft, puoi procedere al test operativo.

### Passo 1: Verificare la Diagnostica su Formazing
1. Avvia l'applicazione Formazing (`python run.py`).
2. Accedi alla dashboard ed esegui i test di diagnostica per assicurarti che la connessione a Notion sia corretta.
   - Se la colonna `Partecipanti` non è ancora stata creata in Notion, la diagnostica mostrerà un **Warning** spiegando che il campo è mancante, ma non bloccherà l'avvio dell'applicazione.
   - Se la colonna è stata creata correttamente come tipo `Persone`, il warning scomparirà.

### Passo 2: Trovare una formazione conclusa
1. Vai alla scheda delle formazioni **"Concluse"** (la terza scheda della dashboard).
2. Se non ci sono elementi, seleziona una formazione nella scheda **"Calendarizzate"**, effettua la preview di feedback e clicca su "Conferma e invia". Questo cambierà lo stato in "Conclusa".
3. Assicurati che la formazione selezionata abbia il campo `Link Teams` popolato con un URL valido di una riunione Teams effettivamente tenutasi.

### Passo 3: Avviae il Sync delle Presenze
1. Sulla riga della formazione conclusa, noterai un pulsante blu **"Importa Presenze"** con l'icona dei partecipanti (👥).
2. Clicca sul pulsante. L'applicazione mostrerà l'overlay grafico: *"Connessione a Microsoft Graph e recupero report presenze da Teams..."*.
3. L'applicazione cercherà il meeting, recupererà il report delle presenze Teams e proverà ad abbinare gli indirizzi email o i nomi dei partecipanti con gli utenti Notion del workspace.

### Passo 4: Controllo e Aggiornamento
- A sincronizzazione ultimata, la dashboard si ricaricherà mostrando un banner verde di conferma (es: *"Sincronizzazione completata: 4 partecipanti trovati."*).
- Il pulsante diventerà verde e cambierà dicitura in **"Aggiorna Presenze"** (con icona di reload), permettendo di rieseguire la sincronizzazione in caso di partecipanti che si sono collegati in ritardo.
- Apri Notion: la colonna `Partecipanti` mostrerà gli account degli utenti Notion reali abbinati!
