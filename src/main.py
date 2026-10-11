"""ChargeGrid Intelligence - Sprint 3: protótipo funcional integrado (simulado).

Uso:
  python main.py                 roda os cenários, grava CSV/JSONL em data/ e mostra o resumo
  python main.py --live          demonstração ao vivo no terminal (para gravar o vídeo)
  python main.py --live --extra  injeta um veículo extra às 18:00 durante a demonstração
  python main.py --previsao      ativa a previsão por regressão linear (experimental)
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C
import simulacao as S

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(RAIZ, "data")


def barra(v, vmax, larg=30):
    n = int(round(larg * min(v, vmax) / vmax))
    return "#" * n + "." * (larg - n)


def painel(l, cps):
    estado = "SOBRECARGA!" if l["sobrecarga"] else "normal"
    print(f"\n=== {l['hora']} | tarifa R$ {l['tarifa_rs_kwh']:.2f}/kWh | decisão: {l['decisao']} ===")
    print(f" Solar    {l['solar_kw']:6.1f} kW  [{barra(l['solar_kw'], 80)}]")
    print(f" Prédio   {l['predio_kw']:6.1f} kW  [{barra(l['predio_kw'], 100)}]")
    print(f" EVs      {l['ev_kw']:6.1f} kW  [{barra(l['ev_kw'], 100)}] (pedido {l['pedido_ev_kw']:.1f})")
    bat = l["bateria_carga_kw"] - l["bateria_descarga_kw"]
    print(f" Bateria  {bat:+6.1f} kW  SoC {l['bateria_soc_pct']:5.1f}%")
    print(f" REDE     {l['rede_kw']:6.1f} kW  [{barra(l['rede_kw'], 150)}] limite {C.GRID_LIMIT_KW:.0f} kW -> {estado}")
    for cp, c in cps.items():
        if c.ativa:
            s = c.ativa
            print(f"   {cp} {c.marca:<14} {l[cp + '_kw']:5.1f}/{c.max_kw:.0f} kW  "
                  f"sessão {s.sid}: {s.entregue:5.1f}/{s.energia:.0f} kWh")


def resumo(m):
    print(f"\n--- {m['modo'].upper()} ---")
    print(f" pico na rede: {m['pico_rede_kw']:.1f} kW (limite {C.GRID_LIMIT_KW:.0f})")
    print(f" minutos acima do limite: {m['minutos_sobrecarga']} | energia acima do limite: {m['energia_acima_limite_kwh']} kWh")
    print(f" energia entregue aos EVs: {m['energia_ev_kwh']} kWh | sessões concluídas: {m['sessoes_concluidas']}/{m['sessoes_total']}")
    print(f" receita simulada: R$ {m['receita_rs']:.2f} | duração média da sessão: {m['duracao_media_sessao_min']} min")
    print(f" parcela renovável do consumo: {m['parcela_renovavel_pct']}% | solar aproveitado: {m['aproveitamento_solar_pct']}%")
    print(f" mensagens OCPP simuladas: {m['msgs_ocpp']} (SetChargingProfile: {m['msgs_set_profile']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="demonstração ao vivo no terminal")
    ap.add_argument("--extra", action="store_true", help="com --live: veículo extra às 18:00 em CP05")
    ap.add_argument("--previsao", action="store_true", help="usa previsão por regressão linear")
    ap.add_argument("--velocidade", type=float, default=0.4, help="segundos por passo exibido (--live)")
    ap.add_argument("--de", default="17:00", help="hora inicial exibida (--live)")
    ap.add_argument("--ate", default="21:00", help="hora final exibida (--live)")
    a = ap.parse_args()

    amb = S.gerar_ambiente()
    extra = [("18:00", "CP05", 25)] if a.extra else []

    if a.live:
        ini, fim = S.minuto_para_passo(a.de), S.minuto_para_passo(a.ate)

        def cb(l, cps):
            if ini <= l["passo"] <= fim:
                painel(l, cps)
                sys.stdout.flush()
                time.sleep(a.velocidade)
        print("ChargeGrid Intelligence - demonstração ao vivo (simulada)")
        S.simular("chargegrid", a.previsao, amb, sessoes_extra=extra, callback=cb)
        return

    os.makedirs(DATA, exist_ok=True)
    todas = []
    for modo in ("sem_controle", "chargegrid"):
        r = S.simular(modo, a.previsao and modo == "chargegrid", amb)
        S.salvar_csvs(r, DATA, modo)
        m = S.metricas(r)
        todas.append(m)
        resumo(m)
    import csv
    with open(os.path.join(DATA, "metricas.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(todas[0].keys()))
        w.writeheader()
        w.writerows(todas)
    print(f"\nArquivos gravados em: {os.path.abspath(DATA)}")


if __name__ == "__main__":
    main()
