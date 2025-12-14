# Guida alla creazione di configurazioni per il simulatore

Questa guida spiega come descrivere ogni elemento del simulatore (strade dritte, curve, veicoli, generatori, oggetti di ambiente, eventi, incroci e UI) usando i file JSON caricati con `trafficSimulator.config.load_simulation_from_json`.

## Come eseguire un file di esempio

```bash
python examples/test_config.py
```

Nel file `examples/test_config.py` puoi cambiare `config_name` per puntare al JSON che preferisci.

## Struttura generale del JSON

Campi di primo livello supportati:

- `ui`: impostazioni della finestra.
- `segments`: elenco di strade (lineari o curve) con metadati.
- `vehicles`: veicoli pre-iniettati sulla mappa.
- `vehicle_generators`: generatori periodici di veicoli.
- `environment`: oggetti statici (alberi, lampioni, edifici, RSU, ecc.).
- `events`: rallentamenti temporanei (cantieri, incidenti, ecc.).
- `junctions`: incroci con semafori o dare precedenza.

## Segmenti (strade)

Campi comuni dei segmenti:

- `id` (consigliato): stringa usata nei percorsi dei veicoli.
- `category`: `general`, `highway`, `taxi`, `bus`, `reserved` (influenza colore/larghezza di default).
- `material`: `asphalt`, `concrete`, `gravel`, `dirt` (puo' modificare il colore se `color` non e' fornito).
- `max_speed`: velocita' massima opzionale in m/s.
- `width`: larghezza corsia in metri.
- `color`: colore RGB come lista di interi `[r, g, b]` (override di categoria/materiale).
- `direction_hint`: se `true` disegna una freccia direzionale.

Tipi di segmenti:

1. **Linea spezzata (type "segment")**
   - Opzione completa: `points` come lista di coordinate `[[x1, y1], [x2, y2], ...]`.
   - Scorciatoia per rette: `start` e `end` al posto di `points`.
2. **Curva di Bezier quadratica (type "quadratic")**
   - Punti: `start`, `control`, `end`.
3. **Curva di Bezier cubica (type "cubic")**
   - Punti: `start`, `control_1`, `control_2`, `end`.
4. **Curva quadratica con aggancio/controllo automatico (type "quadratic" + auto_control)**

- `connect_from` (opzionale): id di un segmento esistente; lo start della curva viene agganciato all'endpoint di quel segmento.
- `connect_to` (opzionale): id di un segmento esistente; l'end della curva viene agganciato allo start di quel segmento (oppure all'endpoint se `connect_to_end: true`).
- `auto_control: true` (opzionale): calcola automaticamente il punto di controllo seguendo la direzione finale di `connect_from` e una distanza proporzionale (`control_scale`, default 0.35) con una componente laterale (`control_offset`, default 0.25). Puoi fornire `control` per override manuale.

Esempi:

```json
{
  "segments": [
    { "id": "dritta", "type": "segment", "start": [0, 0], "end": [100, 0] },
    {
      "id": "curva_auto",
      "type": "quadratic",
      "connect_from": "dritta",
      "end": [160, 40],
      "auto_control": true,
      "control_scale": 0.3
    },
    {
      "id": "spezzata",
      "type": "segment",
      "points": [
        [0, 0],
        [0, 40],
        [50, 40]
      ]
    },
    {
      "id": "curva_q",
      "type": "quadratic",
      "start": [100, 0],
      "control": [140, 40],
      "end": [180, 0]
    },
    {
      "id": "curva_c",
      "type": "cubic",
      "start": [0, 0],
      "control_1": [30, 30],
      "control_2": [60, -30],
      "end": [90, 0]
    }
  ]
}
```

## Veicoli singoli

Creano veicoli gia' presenti sulla mappa.
Campi chiave:

- `path`: lista di id (o indici) di segmenti, in ordine di percorrenza.
- `v`: velocita' iniziale (m/s).
- `vehicle_class`: `vehicle`, `truck`, `bus`, `tank`, `ev` (influenza colore/shape di default).
- `color`, `shape`: opzionali, per override (`shape` supporta `rect`, `triangle`, `circle`).
- Parametri dinamici opzionali: `l` (lunghezza), `s0` (distanza min), `T` (headway), `v_max`, `a_max`, `b_max`.
- `start_segment`, `end_segment`: opzionali; se `path` e' vuoto, il simulatore calcola automaticamente il percorso piu' corto tra questi segmenti seguendo il verso start->end di ogni strada.

Esempio:

```json
{
  "vehicles": [
    { "path": ["dritta", "curva_q"], "v": 12, "vehicle_class": "ev" }
  ]
}
```

## Generatori di veicoli

Creano traffico continuo.
Campi chiave:

- `vehicle_rate`: veicoli per minuto.
- `vehicles`: lista di coppie `[peso, config]`, dove `peso` e' la probabilita' relativa e `config` e' identico a quello di un veicolo singolo.
  - Anche qui puoi usare `start_segment` e `end_segment` invece di `path` per auto-routing.

Esempio:

```json
{
  "vehicle_generators": [
    {
      "vehicle_rate": 20,
      "vehicles": [
        [8, { "path": ["dritta"], "v": 14, "vehicle_class": "vehicle" }],
        [2, { "path": ["spezzata"], "v": 12, "vehicle_class": "bus", "l": 8 }],
        [1, { "path": ["curva_q"], "v": 10, "vehicle_class": "truck" }]
      ]
    }
  ]
}
```

## Oggetti di ambiente

Oggetti statici renderizzati sulla scena.
Campi: `type` (es. `tree`, `lamp`, `building`, `rsu`, `vru`), `position` `[x, y]`, `size`, opzionale `color` `[r, g, b]`.

Esempio:

```json
{
  "environment": [
    { "type": "tree", "position": [10, 20], "size": 3 },
    {
      "type": "building",
      "position": [-30, 15],
      "size": 6,
      "color": [190, 190, 210]
    }
  ]
}
```

## Eventi

Rallentano i veicoli su un tratto per un periodo.
Campi chiave:

- `id` (opzionale, viene generato se assente).
- `segment_id`: id del segmento interessato.
- `offset`: posizione lungo il segmento (0 = inizio, 1 = fine).
- `speed_factor`: fattore moltiplicativo della velocita' (es. 0.5 dimezza la velocita').
- `start_time`: tempo di inizio (secondi).
- `duration` o `end_time`: durata o tempo di fine.
- Facoltativi: `type`, `size`, `color`.

Esempio:

```json
{
  "events": [
    {
      "id": "cantiere_dritta",
      "type": "works",
      "segment_id": "dritta",
      "offset": 0.6,
      "start_time": 15,
      "duration": 90,
      "speed_factor": 0.5,
      "size": 2.5
    }
  ]
}
```

## Incroci (junctions)

Permettono semafori o dare precedenza.
Campi chiave:

- `id`: facoltativo (generato se assente).
- `approaches`: lista di bracci, ciascuno con:
  - `segment_id`: segmento che entra nell'incrocio.
  - `offset`: posizione dell'incrocio sul segmento (0 inizio, 1 fine).
  - `type`: `light` (semaforo) o `yield` (dare precedenza/merge).
  - Per `light`: `green` e `red` (durate in secondi).

Esempio:

```json
{
  "junctions": [
    {
      "id": "incrocio_centrale",
      "approaches": [
        {
          "segment_id": "dritta",
          "offset": 0.5,
          "type": "light",
          "green": 20,
          "red": 20
        },
        { "segment_id": "spezzata", "offset": 0.5, "type": "yield" }
      ]
    }
  ]
}
```

## UI

Opzioni per la finestra: `title`, `width`, `height`, `background_color` `[r, g, b]`.

Esempio:

```json
{
  "ui": {
    "title": "Demo",
    "width": 1280,
    "height": 720,
    "background_color": [240, 245, 250]
  }
}
```

## Esempio minimo completo

```json
{
  "ui": {
    "title": "Mini demo",
    "width": 900,
    "height": 600,
    "background_color": [245, 245, 245]
  },
  "segments": [
    { "id": "dritta", "type": "segment", "start": [0, 0], "end": [120, 0] },
    {
      "id": "curva",
      "type": "quadratic",
      "start": [120, 0],
      "control": [150, 40],
      "end": [120, 80]
    }
  ],
  "vehicle_generators": [
    {
      "vehicle_rate": 15,
      "vehicles": [
        [
          1,
          { "path": ["dritta", "curva"], "v": 13, "vehicle_class": "vehicle" }
        ]
      ]
    }
  ],
  "environment": [{ "type": "tree", "position": [40, 10], "size": 3 }],
  "events": [
    {
      "segment_id": "dritta",
      "offset": 0.7,
      "start_time": 20,
      "duration": 60,
      "speed_factor": 0.6
    }
  ],
  "junctions": []
}
```

## Suggerimenti pratici

- Usa sempre `id` sui segmenti per costruire percorsi leggibili.
- Se vuoi il percorso automatico piu' corto, ometti `path` e indica `start_segment` e `end_segment` (il senso di marcia e' dal primo all'ultimo punto di ciascun segmento; i segmenti si collegano quando l'endpoint di uno coincide con lo startpoint del successivo).
- Mantieni le coordinate in metri; le curve Bezier vengono discretizzate automaticamente.
- Imposta `direction_hint: true` per visualizzare la direzione di marcia.
- Se compare un errore "no points/start/end defined", assicurati di fornire `points` o la coppia `start`/`end`.
- Per riprodurre rapidamente un crash o una nuova configurazione, cambia `config_name` in `examples/test_config.py` e riesegui lo script.
