# Traffic_Simulator — Funzionalità e utilizzo

## Cosa è stato implementato

- **Segmenti arricchiti**: categorie/materiali con colore/larghezza, id mnemonici, max speed opzionale, freccia direzionale, stile per corsie riservate (taxi/bus/altre), supporto a curve quadratiche/cubiche con metadata.
- **Veicoli estesi**: classi veicolo (vehicle, truck, bus, tank, ev) con colore/forma predefiniti, attributi per telemetria (CO2, tipo motore, RPM, A/C, luci, sensori pioggia/foschia), forma personalizzabile (rect/triangle/circle).
- **Topologia per id**: i percorsi possono usare id stringa dei segmenti; il `Simulation` mantiene una mappa id→indice per risoluzione automatica e verifica duplicati.
- **Config JSON**: loader (`load_simulation_from_json`) che costruisce segmenti, veicoli, generatori, ambiente e eventi; UI configurabile (titolo, dimensioni viewport, colore sfondo). Esposizione in `trafficSimulator.__init__`.
- **Ambiente**: supporto a elementi statici (alberi, lampioni, edifici, RSU, VRU, marker generici) con posizione/colore/dimensione da config; layer disattivabile da GUI.
- **Eventi dinamici**: eventi temporizzati (works, accident, animal, generico) con start/durata/end, posizione via segmento+offset o coordinate; marker visivi ridotti; layer disattivabile da GUI. Gli eventi riducono la velocità consentita sul segmento, e i veicoli rallentano se l’evento è entro un lookahead di 50 m anche sul segmento successivo.
- **Rendering migliorato**: colori/larghezze da metadata, frecce direzionali, veicoli disegnati per classe/forma, layer toggles (ambiente/eventi/frecce). Contatori di veicoli ed eventi attivi nel pannello di stato.
- **Esempi pronti**:
  - `examples/config_sample.json`: due corsie opposte, generatori, ambiente ed eventi demo.
  - `examples/config_city.json`: piccola topologia “campus/district” con più categorie di corsia, generatori vari, ambiente ed eventi.
  - `examples/test_config.py`: runner che carica un config JSON e avvia la GUI; basta cambiare `config_name`.

## Come usare

1. **Installazione dipendenze**

   ```bash
   pip install -r requirements.txt
   ```

2. **Eseguire un esempio JSON**

   ```bash
   python examples/test_config.py
   ```

   - Nel file scegli `config_name = "config_sample.json"` oppure `"config_city.json"` (o un tuo file).

3. **Controlli GUI**

   - `Run/Stop` per avviare/fermare la simulazione; `Next frame` avanza di un frame.
   - `Speed` scala i passi di simulazione per frame.
   - `Camera` slider per zoom e offset; drag sul canvas per pan; scroll per zoom inerziale.
   - `Layers` per mostrare/nascondere ambiente, eventi, frecce.
   - Pannello stato: tempo, frame, numero veicoli, eventi attivi.

4. **Definire una topologia via codice (API classica)**

   ```python
   import trafficSimulator as ts
   sim = ts.Simulation()
   sim.create_segment((-100, 3), (100, 2), id="east", category="general", width=3.5)
   sim.create_segment((100, -3), (-100, -2), id="west", category="bus", width=4.0)
   sim.create_vehicle_generator(vehicle_rate=20, vehicles=[(1, {"path": ["east"], "v": 15.0})])
   win = ts.Window(sim)
   win.show()
   ```

5. **Definire una topologia via JSON**

   Schema essenziale (campi opzionali tra parentesi):

   ```json
   {
     "ui": {"title": "", "width": 1280, "height": 720, "background_color": [245,245,245]},
     "segments": [
       {"id": "s1", "type": "segment"|"quadratic"|"cubic", "points": [[x,y], ...] | "start"/"end"/"control"..., "category": "general", "material": "asphalt", "width": 3.5, "direction_hint": true, "max_speed": 16.6}
     ],
     "vehicles": [ {"path": ["s1", ...], "v": 15.0, "vehicle_class": "ev", "shape": "triangle"} ],
     "vehicle_generators": [ {"vehicle_rate": 20, "vehicles": [[weight, {config}]]} ],
     "environment": [ {"type": "tree"|"lamp"|"building"|"rsu"|"vru"|"marker", "position": [x,y], "size": 3, "color": [r,g,b]} ],
     "events": [ {"id": "e1", "type": "works"|"accident"|"animal"|"event", "segment_id": "s1", "offset": 0.5, "start_time": 5, "duration": 60, "speed_factor": 0.5, "size": 2, "color": [r,g,b]} ]
   }
   ```

   Caricamento:

   ```python
   import trafficSimulator as ts
   sim, ui_cfg = ts.load_simulation_from_json("examples/config_city.json")
   win = ts.Window(sim, ui_cfg)
   win.show()
   ```

## Note su comportamento

- **Rallentamento eventi**: lookahead 50 m sul segmento corrente; se il veicolo è vicino alla fine, considera anche il prossimo segmento. Più eventi sovrapposti applicano il fattore minimo.
- **Compatibilità**: gli esempi originali funzionano ancora (path per indice o id). Metadata hanno default sicuri.
- **Rendering**: le dimensioni di frecce e marker sono scalate a grandezze piccole e leggibili; layer disattivabili.

## Estensioni possibili

- Legenda per colori/classi e toggle rapidi in GUI.
- Import/Export di layout direttamente da GUI.
- Aggiunta di controlli per lookahead e severity per eventi.
- Interazioni future con RSU/OBU (e.g., messaggi MQTT) usando i campi già presenti nei veicoli/eventi.
