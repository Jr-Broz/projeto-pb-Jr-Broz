# Relatório TP1 — ARACNE

**Aluno:** [SEU NOME] · **Disciplina:** Projeto de Bloco — Sistemas Robóticos
**Professor:** Dácio Moreira de Souza · **Data:** 28/08/2026
**Repositório:** https://github.com/[org]/projeto-pb-[SEU-USUARIO] · **Tag:** `tp1`
**Vídeo:** [LINK YOUTUBE NÃO-LISTADO]

---

## 1. O projeto e por que ele

[Puxe do PROJETO.md, seção Domínio. 2 parágrafos. Diga qual família do
catálogo você derivou e o que a sua derivação acrescenta.]

## 2. Decisões técnicas

### 2.1 Ambiente: container em vez de VM

O professor indica três rotas (WSL2, VirtualBox, Ubuntu nativo). Optei pelo
container `osrf/ros:humble-desktop`, que é Ubuntu 22.04 com Python 3.10 — a
mesma base das rotas oficiais.

O motivo foi tempo de montagem: [DESCREVA COM HONESTIDADE — quanto tempo você
tinha, por que a VM não coube]. Migração para VirtualBox planejada antes do TP2.

**Trade-off assumido:** perco a paridade exata com o laboratório e a passagem
de USB fica mais delicada. Ganho um ambiente reprodutível por um comando, o
que ajuda no GF.0 (subir em máquina limpa).

### 2.2 Segmentação por cor, não por forma

Segmentação em HSV separa matiz de intensidade, o que a torna mais estável a
variações de iluminação do que limiarização em BGR. O alvo é vermelho, cujo
matiz cruza o zero da roda de cores — por isso são **duas** faixas de H
(0–10 e 170–180), unidas por `bitwise_or`.

Depois: abertura morfológica para remover ruído, fechamento para unir as
pernas ao corpo, e filtro por área mínima (700 px) para descartar respingos.

### 2.3 Serviço `Trigger` em vez de interface própria

`/vision/status` usa `std_srvs/srv/Trigger`. Interface própria é o G2.0/G2.1
do TP2 — antecipar aqui seria fora de escopo. O campo `message` carrega a
informação do domínio: contagem de aracnídeos candidatos, maior área e
frames processados.

### 2.4 Fonte de imagem parametrizada

`camera_node` aceita `fonte:=camera|video|sintetico`. Se a webcam não abrir,
o nó **cai automaticamente** para a fonte sintética e registra um warning.
Isso é o plano B do PROJETO.md implementado em código, não só declarado.

---

## 3. Evidências

| Gate | Evidência | Estado |
|---|---|---|
| G1.0 | `docs/evidencias/tp1/check-ambiente.txt` | [x] / [!] |
| G1.1 | `PROJETO.md` | [x] / [!] |
| G1.2 | `docs/evidencias/tp1/topic-hz.txt` | [x] / [!] |
| G1.3 | `docs/evidencias/tp1/segmentacao.png` | [x] / [!] |
| G1.4 | `docs/evidencias/tp1/rqt_graph.png` | [x] / [!] |
| G1.5 | este documento | [x] / [!] |

![Segmentação](evidencias/tp1/segmentacao.png)

![Grafo ROS 2](evidencias/tp1/rqt_graph.png)

> Confira que as duas imagens acima aparecem no PDF exportado. Referência
> quebrada no Markdown vira espaço em branco no PDF.

---

## 4. Experimento de oclusão

**Montagem:** dois alvos na cena, aproximados progressivamente até a
sobreposição parcial, monitorando `/vision/contagem`.

**Resultado observado:** [PREENCHA COM OS SEUS NÚMEROS]

| Situação | Contagem esperada | Contagem obtida |
|---|---|---|
| Dois alvos separados | 2 | |
| Sobreposição parcial | 2 | |
| Sobreposição total | 1 | |

**Análise:** a segmentação por cor com `RETR_EXTERNAL` trata regiões
conectadas como um contorno único. Quando dois alvos da mesma cor encostam,
suas máscaras se fundem e a contagem cai — o sistema não "perde" o alvo,
ele funde dois em um.

Isso é **limitação estrutural do método**, não bug de parâmetro: nenhum ajuste
de faixa HSV separa dois objetos da mesma cor em contato. A separação exige
watershed, análise de convexidade, ou detecção por instância (G3.4, TP3).

---

## 5. Limitações conhecidas

1. **Segmentação por cor não identifica espécie.** O TP1 conta objetos de uma
   faixa cromática. Reconhecimento taxonômico entra a partir do TP2.
2. **Oclusão funde alvos**, conforme a seção 4.
3. **Sensível ao fundo.** Qualquer objeto vermelho na cena é contado.
4. **Ambiente não é uma das três rotas oficiais**, conforme 2.1.
5. **Gates entregues fora das datas recomendadas** (G1.0 a G1.5), executados
   em bloco em 28/08. Registrado com honestidade conforme a regra dos três
   estados. [AJUSTE SE NÃO FOR O SEU CASO]

---

## 6. Uso de IA declarado

**Ferramenta:** Claude (Anthropic).

**Onde foi usada:**
- [LISTE COM HONESTIDADE. Ex.: estruturação do PROJETO.md; esqueleto dos nós
  `camera_node` e `vision_node`; escolha das faixas HSV; revisão do relatório.]

**O que eu fiz sozinho:**
- [LISTE. Ex.: montagem e depuração do ambiente; execução e captura das
  evidências; ajuste de `area_minima` e `s_min` para a minha cena; experimento
  de oclusão; gravação do vídeo.]

**O que eu verifiquei:** [Ex.: rodei cada comando e confirmei a saída; testei
o fallback desligando a webcam; conferi que a contagem bate com os alvos que
coloquei na cena.]

> Consulte a página "Uso de IA na disciplina" e ajuste esta seção ao formato
> que o professor pede. Declaração honesta custa pouco; omissão custa caro.

---

## 7. Próximos passos (TP2 — 25/09)

- G2.0/G2.1: pacote `aracne_interfaces` com `SpiderID.msg` e `VisionStatus.srv`
- G2.2/G2.3: action de varredura com feedback periódico e cancelamento
- G2.4: detector com métrica declarada sobre vídeo fixo
- G2.5: parametrização YAML + URDF no RViz2
- Migração do ambiente para VirtualBox
