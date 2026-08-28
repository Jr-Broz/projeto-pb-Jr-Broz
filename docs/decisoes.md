# Registro de decisões

Cada mudança relevante: data, o que mudou, onde, por quê, impacto.

---

## 2026-08-28 — Escolha do domínio: percepção de aracnídeos

**O que mudou:** definição do domínio do projeto.
**Onde:** `PROJETO.md`.
**Por quê:** identificação de aranhas é um problema real de percepção visual
em ambiente não controlado, com quatro classes visualmente separáveis e
acervo público de imagens com licença aberta. Exercita o pipeline completo
(aquisição → segmentação → features → classificação) que a disciplina cobre.
**Impacto:** define as classes percebidas de todos os TPs seguintes.

---

## 2026-08-28 — Ambiente: [PREENCHA COM A ROTA QUE VOCÊ ESCOLHEU]

**O que mudou:** [ex.: adoção de container Docker `osrf/ros:humble-desktop`
em vez de VirtualBox.]
**Onde:** `TUTORIAL.md`, `scripts/setup.sh`.
**Por quê:** [ex.: host é Fedora com 8 GB de RAM; o tempo disponível para
montar o ambiente na data da entrega não comportava instalação completa de VM.
A imagem oficial do ROS 2 é Ubuntu 22.04 com Python 3.10 — mesma base das
rotas oficiais.]
**Impacto:** [ex.: perde paridade exata com o laboratório. Migração para
VirtualBox planejada antes do TP2. Declarado no relatório do TP1.]

> **APAGUE ESTA ENTRADA se você usou VirtualBox** — nesse caso não houve
> desvio nenhum e não há o que declarar.

---

## 2026-08-28 — Taxonomia resolvida por tabela, não pelo modelo

**O que mudou:** o classificador prediz apenas a espécie; a linhagem
taxonômica vem de `config/taxonomy.json`.
**Onde:** `PROJETO.md`, `ros2_ws/src/percepcao_aracnideos/config/taxonomy.json`.
**Por quê:** dada a espécie, reino/filo/subfilo/classe/ordem/família/gênero
são consequência lógica, não inferência. Uma rede com oito saídas
correlacionadas desperdiça capacidade e permite predições internamente
inconsistentes.
**Impacto:** simplifica a cabeça de classificação e garante coerência
taxonômica por construção.
