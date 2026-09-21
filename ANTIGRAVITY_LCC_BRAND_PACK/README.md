# LOW CONFIDENCE CLUB — Antigravity Brand Pack

Pacchetto di onboarding per far conoscere a Google Antigravity l'identità di
Low Confidence Club senza costringerlo a ricostruire il brand da file sparsi.

Versione: 1.0  
Data: 21 settembre 2026  
Stato: onboarding operativo; non autorizza pubblicazione o deploy

## Uso rapido

### Opzione A — aprire il pacchetto come progetto

1. Decomprimi l'archivio.
2. Apri la cartella `ANTIGRAVITY_LCC_BRAND_PACK` come progetto Antigravity.
3. Incolla il contenuto di `START_PROMPT.md` nella prima conversazione.
4. Attendi il riepilogo iniziale prima di chiedere proposte o modifiche.

### Opzione B — integrare le regole in un progetto esistente

1. Copia `.agents/rules/` nella radice del progetto.
2. Copia `.agents/workflows/` nella radice del progetto se vuoi il workflow
   riutilizzabile.
3. Copia `lcc_brand/` nella radice del progetto.
4. Avvia Antigravity con il prompt contenuto in `START_PROMPT.md`.

Le regole workspace sono separate in due file brevi, così il contesto essenziale
resta sempre chiaro: uno definisce identità e confini, l'altro il sistema visivo.

## Ordine di lettura per l'agente

1. `.agents/rules/low-confidence-club-core.md`
2. `.agents/rules/low-confidence-club-brand.md`
3. `lcc_brand/context/01-brand-foundation.md`
4. `lcc_brand/context/02-brand-character-and-voice.md`
5. `lcc_brand/context/03-visual-system.md`
6. `lcc_brand/context/04-operating-boundaries.md`
7. `lcc_brand/ASSET_MANIFEST.md`

## Cosa contiene

- prompt iniziale pronto da incollare;
- regole persistenti per Antigravity;
- workflow di onboarding riutilizzabile;
- fondazione, carattere e voce del brand;
- token visivi in JSON e CSS;
- logo ufficiale e linee guida ufficiali;
- social card corrente;
- un esempio editoriale approvato;
- manifest degli asset e checksum per controllarne l'integrità.

## Confine importante

Questo pacchetto insegna il brand e il suo comportamento pubblico. Non contiene
segreti, credenziali o materiali dell'area privata. Non concede ad Antigravity
l'autorizzazione a pubblicare, fare deploy, inviare messaggi o modificare
servizi esterni.

