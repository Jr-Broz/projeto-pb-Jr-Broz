# ARACNE — percepção de aracnídeos por câmera com ROS 2

> Projeto de Bloco — Sistemas Robóticos · INFNET 2026.2
> Aluno: **[SEU NOME]** · Repositório: `projeto-pb-[SEU-USUARIO]`

<!-- PB:PROJETO -->

## Domínio

Identificação visual de aracnídeos a partir de imagem de câmera, com
resolução da linhagem taxonômica da espécie reconhecida.

O Brasil registra milhares de acidentes anuais com aranhas, e boa parte da
gravidade não vem da picada em si, mas do atraso na identificação do animal —
a conduta correta depende de saber a que gênero pertence o exemplar. Esse
conhecimento é especializado e não está disponível no momento e no local em
que o encontro acontece.

Do ponto de vista robótico, é um problema de percepção visual em ambiente não
controlado: o agente observa, segmenta a região de interesse, extrai
características e classifica. É o mesmo pipeline de um robô de inspeção.

## Usuário

Estudante ou técnico em campo (ambiental, agrícola, controle de pragas) que
encontra um exemplar e precisa de uma identificação preliminar imediata, sem
depender de um aracnólogo presente.

O sistema é **auxílio de identificação visual, de caráter acadêmico**. Ele não
emite diagnóstico, não recomenda tratamento e não substitui atendimento médico.
Essa limitação está declarada na interface e no relatório.

## Classes percebidas

Quatro espécies brasileiras, escolhidas por disponibilidade em acervos
públicos e por separabilidade visual entre si, mais uma classe negativa.

| Classe | Espécie | Família | Traço visual dominante |
|---|---|---|---|
| `viuva-negra` | *Latrodectus curacaviensis* | Theridiidae | Abdome globoso escuro com marcas vermelhas |
| `teia-dourada` | *Trichonephila clavipes* | Araneidae | Corpo alongado, tufos nas pernas, seda dourada |
| `aranha-de-grama` | *Lycosa erythrognatha* | Lycosidae | Corpo robusto acinzentado, quelíceras vermelhas |
| `caranguejeira` | *Avicularia avicularia* | Theraphosidae | Porte grande, pilosidade densa, pontas claras |
| `negativo` | — | — | Qualquer outra coisa; predição rejeitada |

Linhagem comum às quatro: Animalia → Arthropoda → Chelicerata → Arachnida → Araneae.

**Decisão de projeto:** o classificador prediz apenas a **espécie**. A linhagem
taxonômica é determinística — dada a espécie, reino, filo, subfilo, classe,
ordem, família e gênero são consequência lógica, não inferência. Fazer a rede
aprender oito saídas correlacionadas desperdiça capacidade e permite predições
internamente inconsistentes (uma família incompatível com o gênero). A
resolução é feita por consulta a `config/taxonomy.json`, indexado pela espécie.

No TP1, a percepção é **segmentação clássica por cor em HSV**, com contagem de
alvos. O classificador entra a partir do TP2.

<!-- PB:TRILHA -->

## Trilha S/H/R

| Etapa | Trilha | Justificativa |
|---|---|---|
| TP1 | **S** (simulação/fonte sintética) + webcam quando disponível | O nó de câmera aceita `fonte:=webcam\|video\|sintetico`. A fonte sintética garante o grafo de pé sem depender de passagem de USB. |
| TP2–TP4 | **S** | SLAM, Nav2 e percepção veicular em Gazebo e MetaDrive. |
| TP5 | a decidir no G5.0 (14/11) | Opção A (hardware) ou B (drone PX4 simulado). |

### Plano B declarado

| Se falhar | Então |
|---|---|
| Webcam não abre no ambiente | `fonte:=sintetico` — cena controlada com alvos de cor conhecida |
| Ambiente containerizado rejeitado | Migração para VirtualBox com a ISO fornecida (rota oficial do professor) |
| Dataset insuficiente para as 4 espécies | Reduzir para 2 espécies e declarar a redução em `docs/decisoes.md` |
| Hardware Raspberry Pi 3 inoperante | Item opcional; o escopo obrigatório é atendido pela webcam USB |

## Ambiente

| Camada | Tecnologia |
|---|---|
| Host | Fedora Linux nativo, 8 GB RAM |
| Ambiente ROS 2 | Container Docker `osrf/ros:humble-desktop` (Ubuntu 22.04, Python 3.10) |
| Middleware | ROS 2 Humble Hawksbill |
| Visão | OpenCV 4 + cv_bridge |
| Câmera | Logitech 720p USB |

**Desvio declarado:** o professor indica três rotas (WSL2, VirtualBox, Ubuntu
nativo). Optei por container Docker sobre a imagem oficial do ROS 2, que é
Ubuntu 22.04 com Python 3.10 — mesma base das rotas oficiais. O motivo foi
tempo de montagem do ambiente. Migração para VirtualBox planejada antes do TP2.
Registrado em `docs/decisoes.md`.

## Arquitetura do TP1

```
camera_node  ──►  /camera/image_raw  ──►  vision_node
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                     ▼                     ▼
                /vision/contagem       /vision/mask         /vision/anotada
                                              │
                                     serviço /vision/status
```

| Nó | Papel |
|---|---|
|  `camera_node` | Publica frames em `/camera/image_raw` (câmera, vídeo ou sintético) |
| `vision_node` | Converte BGR→HSV, segmenta, conta alvos, serve `/vision/status` |

<!-- PB:GATES -->

### TP1 — entrega 28/08

- [ ] G1.0 ambiente operante (07/08)
- [ ] G1.1 projeto declarado: domínio, classes, trilha, plano B (11/08)
- [ ] G1.2 grafo de imagem estável (15/08)
- [ ] G1.3 segmentação + contagem do meu objeto (20/08)
- [ ] G1.4 serviço /vision/status + rqt_graph (24/08)
- [ ] G1.5 relatório fechado (26/08)
- [ ] G1.6 tag tp1 + Moodle (28/08)

## Como rodar

```bash
colcon build --packages-select percepcao_aracnideos
source install/setup.bash

ros2 launch percepcao_aracnideos tp1.launch.py fonte:=sintetico
# ou fonte:=webcam para a webcam

# em outro terminal
ros2 topic hz /vision/contagem
ros2 topic echo /vision/contagem --once
ros2 service call /vision/status std_srvs/srv/Trigger "{}"
rqt_graph
```
