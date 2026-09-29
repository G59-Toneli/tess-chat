"""Tabela por Ligação a partir do log `trilha` (ticket 85). Uso: python tabela.py trilha-prod.log
Por turno: VAD = último mic_silencio antes do ACTIVITY_END até o ACTIVITY_END; modelo = ACTIVITY_END até o 1º áudio."""
import re, sys, collections
ev = collections.defaultdict(list)
for l in open(sys.argv[1], encoding="utf-8", errors="ignore"):
    m = re.search(r"trilha (\w+) (\w+) \+(\d+)ms(.*)", l)
    if m: ev[m[1]].append((m[2], int(m[3]), m[4]))
for cid, es in ev.items():
    turnos, sil, end, th = [], None, None, None
    for nome, t, extra in es:
        if nome == "mic_silencio": sil = t
        elif nome == "voice_activity" and "ACTIVITY_END" in extra: end = (t, sil)
        elif nome == "audio_gemini_1o" and end:
            turnos.append((end[0] - end[1] if end[1] else None, t - end[0])); end = None
        elif nome == "turn_complete": th = extra
    print(cid, "vad/modelo por turno (ms):", turnos)
