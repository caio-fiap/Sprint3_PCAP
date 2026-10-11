# ChargeGrid Intelligence — Sprint 3: Prototipagem Funcional e Integração

**FIAP — Ciência da Computação — 1CCPH, Equipe 1**
Challenge Sprint 3: Pensamento Computacional e Automação com Python 

## Equipe

| Integrante | RM |
|---|---|
| Guilhereme De Oliveira Santos  | 572195 |
| Luis Cesar Conti Salvador | 571305 |
| Victor do Prado Manzini | 572123 |
| Ricardo Tunes Vaca | 555919 |
| Caio Marinho Pereira | 572873 |

## Links

- Repositório:  https://github.com/caio-fiap/Sprint_3PCAP.git
- Vídeo técnico (YouTube, não listado): https://youtube.com/shorts/8szeydU3hxU?feature=share

##Como executar

Requisitos: Python 3 (testado com Python 3.13; a simulação não precisa de bibliotecas externas). Para os gráficos: pip install -r requirements.txt.
```
python src/main.py                            # roda os dois cenários e grava os arquivos em data/
python src/main.py --live                     # demonstração ao vivo no terminal (17:00 às 21:00)
python src/main.py --live --extra             # com um veículo extra conectado às 18:00 
python src/main.py --live --velocidade 0.15 --de 17:30 --ate 20:30 
python src/main.py --previsao                 # liga a previsão linear
python src/analise_sensibilidade.py           # análise com 30 sementes (seção 6.4) 
python src/gerar_graficos.py                  # gráficos e diagramas em docs
```

## Observações

Detalhes do projeto e imagens estão no arquivo pdf e na pasta `docs`, disponíveis no repositório
