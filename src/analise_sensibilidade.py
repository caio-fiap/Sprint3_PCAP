import csv, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import config as C
import controlador
import simulacao as S

RAIZ = os.path.join(os.path.dirname(__file__), "..")
SEMENTES = range(1, 31)
linhas = []
for safety in (0.95, 1.00):
    C.SAFETY = safety
    controlador.SAFETY = safety
    for prev in (False, True):
        ms = [S.metricas(S.simular("chargegrid", prev, S.gerar_ambiente(sd))) for sd in SEMENTES]
        n = len(ms)
        linhas.append({
            "margem_seguranca": safety, "previsao": "sim" if prev else "nao",
            "pico_rede_medio_kw": round(sum(m["pico_rede_kw"] for m in ms) / n, 2),
            "min_sobrecarga_medio": round(sum(m["minutos_sobrecarga"] for m in ms) / n, 2),
            "execucoes_com_sobrecarga": sum(1 for m in ms if m["minutos_sobrecarga"] > 0),
            "msgs_set_profile_medio": round(sum(m["msgs_set_profile"] for m in ms) / n, 1),
            "execucoes": n,
        })
os.makedirs(os.path.join(RAIZ, "data"), exist_ok=True)
with open(os.path.join(RAIZ, "data", "ablacao_previsao.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
    w.writeheader(); w.writerows(linhas)
for l in linhas:
    print(l)
