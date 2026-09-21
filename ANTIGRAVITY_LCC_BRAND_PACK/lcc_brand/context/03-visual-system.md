# Sistema visivo

## Direzione

Club-Lab / Progetti: un sistema editoriale e tecnico, non una skin da terminale.
Il contrasto principale è tra nero materico, avorio caldo e verde oliva. La
grafica lavora con grandi masse tipografiche, griglie, linee sottili, parentesi,
prompt e blocchi di cursore.

## Palette canonica

| Ruolo | Dark | Light |
|---|---:|---:|
| Background | `#080907` | `#EEE8DC` |
| Surface | `#11130F` | `#E2DACB` |
| Text | `#F2EDE3` | `#10120E` |
| Text muted | `#C4BEB2` | `#4A4C43` |
| Olive | `#AEBA7F` | `#53612F` |
| Olive deep | `#778454` | `#657241` |
| Focus | `#D9E6A3` | `#354019` |

Questi sono i token della superficie digitale corrente. Per produzione fisica,
stampa o conversioni Pantone/CMYK serve una prova dedicata: non dedurre valori
di stampa dagli esadecimali.

## Tipografia

- display: sans-serif condensata, maiuscola o molto grande, alta densità;
- testo e metadata: monospaziato leggibile;
- fallback digitale corrente: `Arial Narrow`, `Aptos Narrow`, Arial per display;
  `SFMono-Regular`, Consolas, `Liberation Mono`, monospace per metadata e corpo;
- nessun font commerciale specifico è fornito o licenziato in questo pack.

Non sostituire il logo con testo composto usando i fallback.

## Segni

- `[ ]`: perimetro, selezione, soglia;
- `>_`: prompt e disponibilità a costruire;
- cursore a blocco: stato vivo, non ornamento casuale;
- griglia e coordinate: struttura e verifica;
- texture: materia e imperfezione controllata.

## Uso del logo

- mantenere proporzioni e composizione;
- preferire il file ufficiale fornito;
- lasciare spazio libero attorno al segno;
- non stirare, inclinare, ricolorare o applicare glow;
- non ricostruire il wordmark con font simili;
- non separare `LOW`, parentesi e prompt senza approvazione;
- su fondo chiaro usare un'isola scura coerente, non invertire automaticamente.

## Immagini editoriali

Le immagini devono avere una funzione leggibile. Una texture o una metafora
visiva non sostituisce documentazione o prova. Dichiarare sempre provenienza,
diritti e uso di AI. Un'immagine generata non va presentata come fotografia di
un sistema, luogo o evento reale.

## Accessibilità

- contrasto almeno WCAG AA;
- focus visibile;
- target interattivi almeno 44 × 44 px;
- supporto `prefers-reduced-motion`;
- nessuna informazione affidata al solo colore;
- ordine visivo coerente con ordine del documento;
- testo utilizzabile a 320 px e con zoom 200%.

