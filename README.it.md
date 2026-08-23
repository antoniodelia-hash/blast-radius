# blast-radius — in italiano

**Dodici regole per tenere a bada un assistente AI che lavora sui dati veri di un'azienda.**

Nascono da 18 guasti accaduti fra giugno e agosto 2026 a cinque assistenti automatici in un contesto manifatturiero di piccole dimensioni: alcuni presso lo stesso cliente, uno di uso personale. Ogni guasto ha una data, un costo o un rimedio, e un programmino che chiunque può scaricare e provare.

**In nessuno dei diciotto c'era qualcuno che attaccava.**

## Perché la cosa riguarda anche te, se stai valutando un progetto AI

Quando si parla di rischi dell'intelligenza artificiale in azienda si pensa a un malintenzionato: qualcuno che inganna il sistema, ruba dati, manda comandi truccati. Le classifiche ufficiali dei rischi descrivono esattamente quello.

I guasti che si pagano davvero, in tre mesi di lavoro vero, sono stati altri:

- **Un lavoro automatico che ogni notte diceva** «fatto» mentre era
  fallito. Il programma andava in errore, l'assistente leggeva l'errore, scriveva un riassunto sensato, e il registro segnava «completato con successo». Sei lavori sono andati avanti muti per due mesi.
- **Una frase gentile al posto di un'azione.** «Giro io la richiesta.» Il messaggio partiva davvero, la richiesta non veniva mai aperta. Tre volte su quattro in due mesi. L'ultima è costata 6.272 €: un mezzo a noleggio fermo 32 giorni a 196 € al giorno.
- **File salvati che non arrivavano sul disco.** L'assistente scriveva, rileggeva quello che aveva scritto, lo trovava. Fuori, quel file non era mai esistito. Sembrava una cancellazione, e nessuno aveva cancellato niente.
- **Chi chiedeva una modifica non sapeva mai com'era finita**: su 29 richieste, 25 non avevano un destinatario valido.

Nessuno di questi ha un colpevole. Succedono da soli, mentre tutte le spie restano verdi.

## Cosa distingue un lavoro fatto bene

Le dodici regole si riassumono in poche idee, e sono le domande da fare a chi ti installa un assistente AI:

1. **Il freno di spesa sta fuori dall'assistente.** Un limite scritto nelle sue istruzioni è una cosa che lui sa citare mentre la supera.
2. **Ogni azione annunciata lascia una traccia verificabile**, scritta da un workflow (che non è l'assistente stesso).
3. **Un semaforo verde deve saper diventare rosso.** Se non è mai diventato rosso, va provato: finché non l'hai visto fallire, non sai se funziona.
4. **I permessi vivono nel codice**, con un rifiuto esplicito. Un permesso scritto in una frase è un consiglio.
5. **Chi controlla si verifica da fuori.** Una protezione che risulta installata leggendo la configurazione può non esistere nel programma in funzione: succede, e non dà nessun errore.
6. **Ogni controllo dichiara quanti elementi ha esaminato**, e considera lo zero un guasto. Un controllo che non guarda niente passa sempre.

## Come è fatto il materiale

Ogni regola porta il guasto che l'ha generata con la sua data, quanto è costato, il rimedio installato e come si verifica che il rimedio sia ancora vivo. I programmini si scaricano e girano senza installare niente: servono a provare i controlli sul proprio sistema, in due minuti.

Il nome del cliente non compare, e la cosa è stata messa alla prova sul serio: due modelli esterni hanno ricevuto solo il testo pubblico con la consegna di scoprire l'azienda. Non ci sono riusciti; quello che li aveva avvicinati — a partire dalla tabella che avrebbe dovuto nascondere il lessico di mestiere, e che invece lo pubblicava — è stato riscritto.

## Chi l'ha scritto

[Antonio D'Elia](https://antoniodelia.it) — consulenza AI e organizzazione per PMI. Questi guasti li ho visti succedere sui miei impianti, e i rimedi sono quelli che uso.

Il materiale tecnico completo è in inglese: [README.md](README.md).
Licenza Apache 2.0.
