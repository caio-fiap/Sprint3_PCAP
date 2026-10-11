import io
import os
import sys
from contextlib import redirect_stdout

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C
import simulacao as S
import main as M

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RES = os.path.join(RAIZ, "docs", "resultados")
DIA = os.path.join(RAIZ, "docs", "diagramas")
os.makedirs(RES, exist_ok=True)
os.makedirs(DIA, exist_ok=True)

AZUL, LARANJA, VERDE, CINZA, VERM, ROXO = "#1f77b4", "#e07b00", "#2a9d4b", "#6b7280", "#c0392b", "#7e57c2"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25})


def horas(L):
    return [l["passo"] * C.STEP_MIN / 60 for l in L]


def eixo_hora(ax):
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 3))
    ax.set_xticklabels([f"{h:02d}h" for h in range(0, 25, 3)])


def grafico_rede(a, b):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    h = horas(a["linhas"])
    ax.plot(h, [l["rede_kw"] for l in a["linhas"]], color=VERM, lw=2, label="Sem controle")
    ax.plot(h, [l["rede_kw"] for l in b["linhas"]], color=VERDE, lw=2, label="Com ChargeGrid")
    ax.axhline(C.GRID_LIMIT_KW, color="black", ls="--", lw=1.2, label=f"Limite da instalação ({C.GRID_LIMIT_KW:.0f} kW)")
    ax.fill_between(h, C.GRID_LIMIT_KW, [max(C.GRID_LIMIT_KW, l["rede_kw"]) for l in a["linhas"]],
                    color=VERM, alpha=0.25)
    ax.set_ylabel("Potência importada da rede (kW)")
    ax.set_title("Demanda na rede elétrica: sem controle x com ChargeGrid (cenário simulado)")
    eixo_hora(ax)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "01_rede_sem_vs_com.png"), dpi=150)
    plt.close(fig)


def grafico_fluxos(b):
    L = b["linhas"]
    h = horas(L)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
    ax1.stackplot(h, [l["solar_usado_kw"] for l in L], [l["bateria_descarga_kw"] for l in L], [l["rede_kw"] for l in L],
                  colors=[LARANJA, ROXO, CINZA], labels=["Solar", "Bateria (descarga)", "Rede"], alpha=0.85)
    ax1.plot(h, [l["predio_kw"] + l["ev_kw"] + l["bateria_carga_kw"] for l in L], color="black", lw=1.2,
             label="Carga total (prédio + EVs + carga da bateria)")
    ax1.set_ylabel("Potência (kW)")
    ax1.set_title("Origem da energia ao longo do dia - com ChargeGrid")
    ax1.legend(loc="upper left", fontsize=8)
    cps = [c[0] for c in C.CARREGADORES]
    ax2.stackplot(h, *[[l[f"{cp}_kw"] for l in L] for cp in cps], labels=cps, alpha=0.9)
    ax2.plot(h, [l["pedido_ev_kw"] for l in L], color="black", lw=1.2, ls=":", label="Pedido dos veículos (potência máx.)")
    ax2.set_ylabel("Potência entregue aos EVs (kW)")
    ax2.set_title("Potência por carregador (comandos SetChargingProfile do ChargeGrid)")
    ax2.legend(loc="upper left", ncol=4, fontsize=8)
    eixo_hora(ax2)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "02_fluxos_chargegrid.png"), dpi=150)
    plt.close(fig)


def grafico_bateria(b):
    L = b["linhas"]
    h = horas(L)
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.plot(h, [l["bateria_soc_pct"] for l in L], color=ROXO, lw=2, label="Carga da bateria (SoC %)")
    ax.set_ylabel("SoC (%)")
    ax.set_ylim(0, 100)
    ax2 = ax.twinx()
    ax2.bar(h, [l["bateria_carga_kw"] - l["bateria_descarga_kw"] for l in L], width=0.08, color=VERDE, alpha=0.6,
            label="Potência (+ carrega / - descarrega)")
    ax2.set_ylabel("kW")
    ax2.grid(False)
    ax.set_title("Bateria: recarga com sobra solar e descarga no horário de ponta")
    eixo_hora(ax)
    l1, n1 = ax.get_legend_handles_labels()
    l2, n2 = ax2.get_legend_handles_labels()
    ax.legend(l1 + l2, n1 + n2, loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "03_bateria_soc.png"), dpi=150)
    plt.close(fig)


def grafico_sessoes(a, b):
    ids = [s.sid for s in a["sessoes"]]
    da = [(s.fim - s.inicio + 1) * C.STEP_MIN for s in a["sessoes"]]
    db = [(s.fim - s.inicio + 1) * C.STEP_MIN for s in b["sessoes"]]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    w = 0.38
    ax.bar([i - w / 2 for i in ids], da, w, color=VERM, label="Sem controle")
    ax.bar([i + w / 2 for i in ids], db, w, color=VERDE, label="Com ChargeGrid")
    ax.set_xticks(ids)
    ax.set_xticklabels([f"#{i}\n{S.hhmm(s.chegada)}" for i, s in zip(ids, b["sessoes"])], fontsize=8)
    ax.set_ylabel("Duração da recarga (min)")
    ax.set_title("Custo do controle: sessões da ponta demoram um pouco mais (a energia entregue é a mesma)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "04_duracao_sessoes.png"), dpi=150)
    plt.close(fig)


def imagem_terminal(passo_txt="18:45"):
    """Renderiza como imagem a saída REAL do modo --live para um instante."""
    amb = S.gerar_ambiente()
    buf = io.StringIO()
    alvo = S.minuto_para_passo(passo_txt)

    def cb(l, cps):
        if l["passo"] == alvo:
            with redirect_stdout(buf):
                M.painel(l, cps)
    S.simular("chargegrid", False, amb, callback=cb)
    texto = buf.getvalue().strip("\n")
    n = texto.count("\n") + 1
    fig = plt.figure(figsize=(9, 0.205 * n + 0.45), facecolor="#111827")
    fig.text(0.02, 0.97, texto, family="DejaVu Sans Mono", fontsize=9.5, color="#e5e7eb", va="top")
    fig.savefig(os.path.join(RES, "05_terminal_ao_vivo_1845.png"), dpi=150, facecolor="#111827",
                bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


# ----------------------------- diagramas ------------------------------------
def caixa(ax, x, y, w, h, texto, cor, fs=9, tc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc=cor, ec="none"))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold")


def seta(ax, p, q, cor="#374151", bidir=False, estilo="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if bidir else estilo, mutation_scale=14,
                                 color=cor, lw=1.6, linestyle=ls))


def diagrama_blocos():
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 11)
    ax.set_ylim(-0.8, 6.4)
    ax.axis("off")
    ax.text(5.5, 6.15, "Arquitetura do protótipo ChargeGrid Intelligence (Sprint 3)", ha="center",
            fontsize=13, fontweight="bold")
    # Linha de geração / armazenamento / rede
    caixa(ax, 0.2, 4.4, 1.9, 0.9, "Painéis solares\n(80 kWp simulado)", LARANJA)
    caixa(ax, 2.9, 4.4, 2.2, 0.9, "Inversor híbrido\nGoodWe (simulado)", AZUL)
    caixa(ax, 5.9, 4.4, 1.8, 0.9, "Bateria\n60 kWh", ROXO)
    caixa(ax, 8.5, 4.4, 2.2, 0.9, "Rede elétrica\nlimite 100 kW", CINZA)
    seta(ax, (2.1, 4.85), (2.9, 4.85), "#b45309")
    seta(ax, (5.1, 4.85), (5.9, 4.85), "#6d28d9", bidir=True)
    # Barramento CA
    ax.plot([3.0, 10.6], [3.5, 3.5], color="#374151", lw=6, solid_capstyle="round")
    ax.text(6.3, 3.68, "Barramento CA da instalação", ha="center", fontsize=9, style="italic", color="#374151")
    seta(ax, (4.0, 4.4), (4.0, 3.55), "#374151", bidir=True)
    seta(ax, (9.6, 4.4), (9.6, 3.55), "#374151", bidir=True)
    ax.text(9.7, 3.95, "importa / exporta", fontsize=7.5, color="#374151")
    # Cargas no barramento
    caixa(ax, 2.9, 2.0, 2.2, 0.8, "Carga do prédio\n(ar-cond., iluminação)", "#0f766e", fs=8.5)
    seta(ax, (4.0, 3.45), (4.0, 2.8), "#374151")
    caixa(ax, 8.2, 1.6, 2.6, 1.3, "Carregadores (OCPP simulado)\nCP01-02 GoodWe\nCP03 ABB • CP04 WEG\nCP05-06 genérico", "#b91c1c", fs=8)
    seta(ax, (9.5, 3.45), (9.5, 2.9), "#374151")
    ax.text(9.6, 3.1, "potência de carga", fontsize=7.5, color="#374151")
    # Medição e ChargeGrid
    caixa(ax, 0.2, 0.55, 2.4, 0.85, "Medição\n(solar, prédio, SoC, kWh)", "#475569", fs=8.5)
    caixa(ax, 3.3, 0.2, 4.2, 1.45, "", "#14532d")
    ax.text(5.4, 1.42, "CHARGEGRID (software)", ha="center", color="white", fontsize=10, fontweight="bold")
    for i, t in enumerate(["Balanceamento dinâmico", "Gestão da bateria", "Tarifação por horário", "Previsão (opcional)"]):
        ax.text(5.4, 1.12 - i * 0.23, "• " + t, ha="center", color="#dcfce7", fontsize=8.5)
    seta(ax, (2.6, 0.97), (3.3, 0.97), "#374151")
    seta(ax, (6.8, 1.65), (6.8, 4.4), "#14532d", ls=":")
    ax.text(6.9, 2.35, "setpoint\nda bateria", fontsize=7.5, color="#14532d")
    seta(ax, (7.5, 0.9), (8.9, 1.6), "#b91c1c", bidir=True)
    ax.text(8.55, 0.95, "OCPP-J\n(SetChargingProfile,\nMeterValues...)", fontsize=7.5, color="#b91c1c")
    # Saídas
    caixa(ax, 2.4, -0.75, 6.0, 0.5, "Saídas: CSV • log OCPP • painel no terminal • gráficos", "#334155", fs=8.5)
    seta(ax, (5.4, 0.2), (5.4, -0.25), "#334155")
    fig.savefig(os.path.join(DIA, "diagrama_blocos.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


def fluxograma():
    fig, ax = plt.subplots(figsize=(8, 10.5))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 10.5)
    ax.axis("off")
    ax.text(4, 10.25, "Fluxograma do ciclo de decisão (a cada 5 minutos simulados)", ha="center", fontsize=12, fontweight="bold")
    passos = [
        (9.3, "Chegam veículos / iniciam sessões\n(StartTransaction)", AZUL),
        (8.2, "Lê medições do passo anterior\n(solar, prédio, SoC)", "#475569"),
        (7.1, "Calcula pedido dos EVs\n(potência máx. de cada carregador ativo)", AZUL),
        (5.2, "", None),
        (3.7, "Distribui potência entre os carregadores\n(balanceamento dinâmico)", VERDE),
        (2.6, "Envia SetChargingProfile se mudou > 0,5 kW", "#b91c1c"),
        (1.5, "Entrega energia, calcula tarifa e receita,\natualiza bateria e grava CSV", "#334155"),
        (0.4, "Sessão concluída? → StopTransaction", AZUL),
    ]
    for y, t, c in passos:
        if t:
            caixa(ax, 1.5, y - 0.35, 5, 0.75, t, c, fs=9)
    # losango de decisão
    ax.add_patch(plt.Polygon([(4, 6.4), (6.4, 5.5), (4, 4.6), (1.6, 5.5)], fc="#f59e0b", ec="none"))
    ax.text(4, 5.5, "Pedido total ≤ potência\ndisponível sem a bateria?", ha="center", va="center", fontsize=8.5, fontweight="bold")
    for y0, y1 in [(8.95, 8.55), (7.85, 7.45), (6.75, 6.4)]:
        seta(ax, (4, y0 - 0.05), (4, y1))
    seta(ax, (4, 4.6), (4, 4.1))
    ax.text(4.1, 4.3, "SIM: carrega bateria com sobra solar", fontsize=7.5, color="#92400e")
    # ramo NÃO
    caixa(ax, 6.7, 4.0, 1.25, 0.8, "NÃO: descarrega\nbateria e reduz\npotência", "#b45309", fs=7)
    seta(ax, (6.4, 5.5), (7.3, 4.8), "#b45309")
    seta(ax, (7.3, 4.0), (6.5, 3.75), "#b45309")
    for y0, y1 in [(3.3, 2.95), (2.2, 1.9), (1.1, 0.8)]:
        seta(ax, (4, y0), (4, y1))
    fig.savefig(os.path.join(DIA, "fluxograma_decisao.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    amb = S.gerar_ambiente()
    a = S.simular("sem_controle", False, amb)
    b = S.simular("chargegrid", False, amb)
    grafico_rede(a, b)
    grafico_fluxos(b)
    grafico_bateria(b)
    grafico_sessoes(a, b)
    imagem_terminal("18:45")
    diagrama_blocos()
    fluxograma()
    print("imagens geradas em", os.path.abspath(RES), "e", os.path.abspath(DIA))
