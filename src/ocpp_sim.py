import json


class OcppLog:
    def __init__(self):
        self.msgs = []
        self._n = 0

    def _emit(self, hora, origem, destino, acao, payload):
        self._n += 1
        # tipo 2 = CALL (requisição), conforme o formato OCPP-J
        self.msgs.append({
            "hora": hora, "de": origem, "para": destino,
            "msg": [2, f"{self._n:05d}", acao, payload],
        })

    # Carregador -> Central
    def boot(self, hora, cp, marca, modelo):
        self._emit(hora, cp, "CENTRAL", "BootNotification",
                   {"chargePointVendor": marca, "chargePointModel": modelo})

    def start(self, hora, cp, sid):
        self._emit(hora, cp, "CENTRAL", "StartTransaction",
                   {"connectorId": 1, "transactionId": sid, "meterStart": 0})

    def meter(self, hora, cp, sid, kwh, kw):
        self._emit(hora, cp, "CENTRAL", "MeterValues",
                   {"transactionId": sid,
                    "energia_kWh": round(kwh, 3), "potencia_kW": round(kw, 2)})

    def stop(self, hora, cp, sid, kwh):
        self._emit(hora, cp, "CENTRAL", "StopTransaction",
                   {"transactionId": sid, "energia_kWh": round(kwh, 3)})

    # Central -> Carregador (comando automatizado do ChargeGrid)
    def set_profile(self, hora, cp, limite_kw, motivo):
        self._emit(hora, "CENTRAL", cp, "SetChargingProfile",
                   {"connectorId": 1, "limite_kW": round(limite_kw, 2), "motivo": motivo})

    def salvar(self, caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            for m in self.msgs:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

    def contar(self):
        c = {}
        for m in self.msgs:
            a = m["msg"][2]
            c[a] = c.get(a, 0) + 1
        return c
