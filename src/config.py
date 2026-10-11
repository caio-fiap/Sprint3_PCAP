
#  Tempo
STEP_MIN = 5                      # passo da simulação (minutos)
DT_H = STEP_MIN / 60.0            # passo em horas
STEPS_DIA = 24 * 60 // STEP_MIN   # 288 passos = 24 h

#  Ponto de conexão com a rede
GRID_LIMIT_KW = 100.0             # limite da instalação (mesmo valor da Sprint 2)
SAFETY = 0.95                     # margem de segurança usada pelo controlador

#  Geração solar (inversor híbrido GoodWe simulado)
SOLAR_PEAK_KW = 80.0

#  Bateria
BATT_CAPACITY_KWH = 60.0
BATT_MAX_KW = 30.0
BATT_SOC_INIT = 0.20
BATT_SOC_MIN = 0.10
BATT_SOC_MAX = 0.95
BATT_EFF = 0.95                   # eficiência de carga e de descarga (cada)

#  Tarifação (R$/kWh)
TARIFA_BASE = 1.20                # mesmo valor da Sprint 2
TARIFA_SOLAR = 0.90               # 10h-15h: incentivo ao uso de energia solar
TARIFA_PICO = 1.80                # 18h-21h: horário de ponta

#  Carregadores (interoperabilidade entre marcas)
# (id, marca, modelo, potência máxima em kW)
CARREGADORES = [
    ("CP01", "GoodWe", "HCA G2 (simulado)", 22.0),
    ("CP02", "GoodWe", "HCA G2 (simulado)", 22.0),
    ("CP03", "ABB",    "AC genérico (simulado)", 22.0),
    ("CP04", "WEG",    "AC genérico (simulado)", 22.0),
    ("CP05", "Genérico OCPP", "AC 11 kW (simulado)", 11.0),
    ("CP06", "Genérico OCPP", "AC 11 kW (simulado)", 11.0),
]

#  Cenário de sessões de recarga (estacionamento comercial)
# (chegada "HH:MM", carregador, energia solicitada em kWh)
SESSOES = [
    ("09:00", "CP01", 30), ("09:30", "CP03", 25), ("10:15", "CP04", 35),
    ("11:00", "CP02", 20), ("12:00", "CP05", 15), ("12:30", "CP06", 18),
    ("13:30", "CP01", 28), ("14:00", "CP03", 40),
    ("17:30", "CP02", 32), ("17:45", "CP04", 30), ("18:00", "CP01", 35),
    ("18:15", "CP05", 20), ("18:30", "CP06", 15), ("18:45", "CP03", 28),
]

SEED = 42                         # semente do ruído (resultados reprodutíveis)
OCPP_METER_EVERY = 3              # MeterValues a cada 3 passos (15 min)
SETPOINT_DEADBAND_KW = 0.5        # só reenvia SetChargingProfile se mudar mais que isso
