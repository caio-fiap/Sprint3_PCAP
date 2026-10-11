import csv
import math
import random
from dataclasses import dataclass, field

import config as C
from controlador import Controlador
from ocpp_sim import OcppLog


def hhmm(passo):
    m = passo * C.STEP_MIN
    return f"{m // 60:02d}:{m % 60:02d}"


def tarifa(passo):
    h = passo * C.STEP_MIN / 60.0
    if 18 <= h < 21:
        return C.TARIFA_PICO
    if 10 <= h < 15:
        return C.TARIFA_SOLAR
    return C.TARIFA_BASE


def gerar_ambiente(seed=C.SEED):
    """Gera séries de geração solar e carga do prédio (mesmas para todos os modos)."""
    rng = random.Random(seed)
    solar, predio = [], []
    nuvem = 1.0
    for t in range(C.STEPS_DIA):
        h = t * C.STEP_MIN / 60.0
        base = 0.0
        if 6 <= h <= 18:
            base = C.SOLAR_PEAK_KW * math.sin(math.pi * (h - 6) / 12) ** 1.5
        nuvem = min(1.0, max(0.55, nuvem + rng.uniform(-0.12, 0.12)))
        solar.append(base * nuvem)
        carga = 25.0
        if 8 <= h < 18:
            carga += 15.0                      # horário comercial (ar-condicionado, iluminação)
        if 18 <= h < 20:
            carga += 10.0                      # fechamento / limpeza
        predio.append(carga + rng.uniform(-2.0, 2.0))
    return solar, predio


@dataclass
class Sessao:
    sid: int
    cp: str
    chegada: int
    energia: float
    entregue: float = 0.0
    inicio: int = None
    fim: int = None
    receita: float = 0.0
    kwh_ponta: float = 0.0


@dataclass
class Carregador:
    cp: str
    marca: str
    modelo: str
    max_kw: float
    fila: list = field(default_factory=list)
    ativa: Sessao = None
    ultimo_limite: float = None


def minuto_para_passo(txt):
    h, m = txt.split(":")
    return (int(h) * 60 + int(m)) // C.STEP_MIN


def simular(modo="chargegrid", usar_previsao=False, ambiente=None, sessoes_extra=None, callback=None):
    """modo: 'sem_controle' (carregadores no máximo) ou 'chargegrid' (controle inteligente).

    Retorna dict com 'linhas' (série temporal), 'sessoes', 'ocpp'.
    """
    solar, predio = ambiente or gerar_ambiente()
    cps = {c[0]: Carregador(*c) for c in C.CARREGADORES}
    sessoes = []
    for i, (hora, cp, kwh) in enumerate(C.SESSOES + list(sessoes_extra or []), start=1):
        sessoes.append(Sessao(sid=i, cp=cp, chegada=minuto_para_passo(hora), energia=float(kwh)))

    ocpp = OcppLog()
    for c in cps.values():
        ocpp.boot("00:00", c.cp, c.marca, c.modelo)

    ctrl = Controlador(usar_previsao=usar_previsao)
    ctrl.medir(predio[0], solar[0])
    bat_kwh = C.BATT_SOC_INIT * C.BATT_CAPACITY_KWH
    linhas = []

    for t in range(C.STEPS_DIA):
        hora = hhmm(t)
        for s in sessoes:
            if s.chegada == t:
                cps[s.cp].fila.append(s)
        for c in cps.values():
            if c.ativa is None and c.fila:
                c.ativa = c.fila.pop(0)
                c.ativa.inicio = t
                c.ultimo_limite = None
                ocpp.start(hora, c.cp, c.ativa.sid)

        ativos = {c.cp: c for c in cps.values() if c.ativa}
        pedidos = {cp: min(c.max_kw, (c.ativa.energia - c.ativa.entregue) / C.DT_H)
                   for cp, c in ativos.items()}

        # ---- decisão ----
        if modo == "sem_controle":
            setpoints, bat_cmd, motivo = dict(pedidos), 0.0, "sem controle"
        else:
            setpoints, bat_cmd, motivo = ctrl.decidir(pedidos, bat_kwh)

        # ---- comandos automatizados (SetChargingProfile) ----
        for cp, c in ativos.items():
            novo = setpoints[cp]
            if c.ultimo_limite is None or abs(novo - c.ultimo_limite) >= C.SETPOINT_DEADBAND_KW:
                if modo != "sem_controle":
                    ocpp.set_profile(hora, cp, novo, motivo)
                c.ultimo_limite = novo

        # ---- planta (valores reais do passo) ----
        ev_kw = 0.0
        ponta = tarifa(t)
        for cp, c in ativos.items():
            p = min(setpoints[cp], pedidos[cp])
            e = p * C.DT_H
            c.ativa.entregue += e
            c.ativa.receita += e * ponta
            if ponta == C.TARIFA_PICO:
                c.ativa.kwh_ponta += e
            ev_kw += p
            setpoints[cp] = p

        carga_bat, desc_bat = 0.0, 0.0
        if bat_cmd > 0:
            espaco = (C.BATT_SOC_MAX * C.BATT_CAPACITY_KWH - bat_kwh) / (C.DT_H * C.BATT_EFF)
            carga_bat = max(0.0, min(bat_cmd, C.BATT_MAX_KW, espaco))
            bat_kwh += carga_bat * C.DT_H * C.BATT_EFF
        elif bat_cmd < 0:
            disp = max(0.0, (bat_kwh - C.BATT_SOC_MIN * C.BATT_CAPACITY_KWH) * C.BATT_EFF / C.DT_H)
            desc_bat = max(0.0, min(-bat_cmd, C.BATT_MAX_KW, disp))
            bat_kwh -= desc_bat * C.DT_H / C.BATT_EFF

        liquido = predio[t] + ev_kw + carga_bat - solar[t] - desc_bat
        rede = max(0.0, liquido)
        exportado = max(0.0, -liquido)
        solar_usado = max(0.0, solar[t] - exportado)

        # ---- eventos de fim de sessão e medições ----
        for cp, c in ativos.items():
            s = c.ativa
            if (t - s.inicio) % C.OCPP_METER_EVERY == 0:
                ocpp.meter(hora, cp, s.sid, s.entregue, setpoints[cp])
            if s.energia - s.entregue <= 1e-6:
                s.fim = t
                ocpp.stop(hora, cp, s.sid, s.entregue)
                c.ativa = None

        linha = {
            "hora": hora, "passo": t,
            "solar_kw": round(solar[t], 2), "predio_kw": round(predio[t], 2),
            "ev_kw": round(ev_kw, 2), "bateria_carga_kw": round(carga_bat, 2),
            "bateria_descarga_kw": round(desc_bat, 2),
            "bateria_soc_pct": round(100 * bat_kwh / C.BATT_CAPACITY_KWH, 1),
            "rede_kw": round(rede, 2), "exportado_kw": round(exportado, 2),
            "solar_usado_kw": round(solar_usado, 2),
            "limite_kw": C.GRID_LIMIT_KW,
            "sobrecarga": int(rede > C.GRID_LIMIT_KW + 1e-9),
            "pedido_ev_kw": round(sum(pedidos.values()), 2),
            "carregadores_ativos": len(ativos),
            "tarifa_rs_kwh": ponta, "decisao": motivo,
        }
        for cp in cps:
            linha[f"{cp}_kw"] = round(setpoints.get(cp, 0.0), 2)
        linhas.append(linha)
        if callback:
            callback(linha, cps)

        ctrl.medir(predio[t], solar[t])

    return {"linhas": linhas, "sessoes": sessoes, "ocpp": ocpp, "modo": modo}


def metricas(res):
    L = res["linhas"]
    dt = C.DT_H
    consumo = sum(l["predio_kw"] + l["ev_kw"] for l in L) * dt
    rede = sum(l["rede_kw"] for l in L) * dt
    solar_ger = sum(l["solar_kw"] for l in L) * dt
    solar_usado = sum(l["solar_usado_kw"] for l in L) * dt
    ss = [s for s in res["sessoes"] if s.fim is not None]
    atraso = [((s.fim - s.inicio + 1) * C.STEP_MIN) for s in ss]
    return {
        "modo": res["modo"],
        "pico_rede_kw": max(l["rede_kw"] for l in L),
        "minutos_sobrecarga": sum(l["sobrecarga"] for l in L) * C.STEP_MIN,
        "energia_acima_limite_kwh": round(sum(max(0.0, l["rede_kw"] - C.GRID_LIMIT_KW) for l in L) * dt, 2),
        "energia_ev_kwh": round(sum(l["ev_kw"] for l in L) * dt, 1),
        "sessoes_concluidas": len(ss),
        "sessoes_total": len(res["sessoes"]),
        "receita_rs": round(sum(s.receita for s in res["sessoes"]), 2),
        "aproveitamento_solar_pct": round(100 * solar_usado / solar_ger, 1) if solar_ger else 0,
        "parcela_renovavel_pct": round(100 * (1 - rede / consumo), 1) if consumo else 0,
        "duracao_media_sessao_min": round(sum(atraso) / len(atraso), 1) if atraso else 0,
        "msgs_ocpp": sum(res["ocpp"].contar().values()),
        "msgs_set_profile": res["ocpp"].contar().get("SetChargingProfile", 0),
        "energia_rede_kwh": round(rede, 1),
        "energia_consumida_kwh": round(consumo, 1),
        "solar_gerado_kwh": round(solar_ger, 1),
    }


def salvar_csvs(res, pasta, prefixo):
    L = res["linhas"]
    with open(f"{pasta}/{prefixo}_serie_temporal.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(L[0].keys()))
        w.writeheader()
        w.writerows(L)
    with open(f"{pasta}/{prefixo}_sessoes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sessao", "carregador", "chegada", "inicio", "fim", "energia_kwh",
                    "espera_min", "duracao_min", "kwh_ponta", "receita_rs"])
        for s in res["sessoes"]:
            fim = hhmm(s.fim) if s.fim is not None else "nao_concluida"
            dur = (s.fim - s.inicio + 1) * C.STEP_MIN if s.fim is not None else ""
            w.writerow([s.sid, s.cp, hhmm(s.chegada), hhmm(s.inicio) if s.inicio is not None else "",
                        fim, round(s.entregue, 2), (s.inicio - s.chegada) * C.STEP_MIN if s.inicio is not None else "",
                        dur, round(s.kwh_ponta, 2), round(s.receita, 2)])
    res["ocpp"].salvar(f"{pasta}/{prefixo}_ocpp.jsonl")
