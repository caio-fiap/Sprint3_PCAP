from config import (GRID_LIMIT_KW, SAFETY, BATT_CAPACITY_KWH, BATT_MAX_KW,
                    BATT_SOC_MIN, BATT_SOC_MAX, BATT_EFF, DT_H)


def prever(serie, n=6, horizonte=1):
    """Previsão por regressão linear simples (mínimos quadrados) nos últimos n pontos.

    É uma técnica estatística leve (não é deep learning). Retorna valor >= 0.
    """
    ys = serie[-n:]
    if len(ys) < 3:
        return ys[-1]
    k = len(ys)
    xs = list(range(k))
    mx, my = sum(xs) / k, sum(ys) / k
    den = sum((x - mx) ** 2 for x in xs)
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    b = my - a * mx
    return max(0.0, a * (k - 1 + horizonte) + b)


def distribuir(potencia_total, pedidos):
    """Balanceamento dinâmico (water-filling): divide a potência igualmente
    entre os carregadores ativos, respeitando o teto de cada um e
    redistribuindo a sobra dos que pedem menos.

    pedidos: dict {id_carregador: kW desejado}.  Retorna dict {id: kW}.
    """
    resto = max(0.0, potencia_total)
    faltam = dict(pedidos)
    saida = {cp: 0.0 for cp in pedidos}
    while faltam and resto > 1e-9:
        cota = resto / len(faltam)
        saturados = [cp for cp, p in faltam.items() if p <= cota]
        if not saturados:
            for cp in faltam:
                saida[cp] += cota
            break
        for cp in saturados:
            saida[cp] += faltam[cp]
            resto -= faltam[cp]
            del faltam[cp]
    return saida


class Controlador:
    def __init__(self, usar_previsao=True):
        self.usar_previsao = usar_previsao
        self.hist_predio = []
        self.hist_solar = []

    def medir(self, predio_kw, solar_kw):
        """Registra a última medição (sensores / medidor do inversor)."""
        self.hist_predio.append(predio_kw)
        self.hist_solar.append(solar_kw)

    def decidir(self, pedidos, energia_bateria_kwh):
        """Decide a potência de cada carregador e da bateria no próximo passo.

        Retorna (setpoints, bateria_kw, motivo). bateria_kw > 0 carrega, < 0 descarrega.
        """
        if self.usar_previsao:
            predio = prever(self.hist_predio)
            solar = prever(self.hist_solar)
        else:
            predio, solar = self.hist_predio[-1], self.hist_solar[-1]

        teto = GRID_LIMIT_KW * SAFETY
        pedido_total = sum(pedidos.values())
        oferta = max(0.0, teto + solar - predio)     # o que cabe sem usar a bateria

        if pedido_total <= oferta:
            ev_kw = pedido_total
            sobra_solar = solar - predio - ev_kw
            espaco = (BATT_SOC_MAX * BATT_CAPACITY_KWH - energia_bateria_kwh) / (DT_H * BATT_EFF)
            bat = min(max(sobra_solar, 0.0), BATT_MAX_KW, max(espaco, 0.0))
            motivo = "livre" if bat <= 0.01 else "carrega bateria (sobra solar)"
            return distribuir(ev_kw, pedidos), bat, motivo

        falta = pedido_total - oferta
        disponivel = max(0.0, (energia_bateria_kwh - BATT_SOC_MIN * BATT_CAPACITY_KWH) * BATT_EFF / DT_H)
        desc = min(falta, BATT_MAX_KW, disponivel)
        ev_kw = oferta + desc
        motivo = "balanceamento + bateria" if desc > 0.01 else "balanceamento (limite da rede)"
        return distribuir(ev_kw, pedidos), -desc, motivo
