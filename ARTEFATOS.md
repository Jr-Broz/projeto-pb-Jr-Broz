# Artefatos do projeto ARACNE

Links de vídeos e artefatos grandes que não vão para o git.
**Teste cada link em aba anônima antes de entregar. Inacessível = inexistente.**

## Vídeos de defesa

| TP | Link | Visibilidade | Testado em aba anônima |
|---|---|---|---|
| TP1 | [COLE O LINK DO YOUTUBE] | não listado | [ ] |
| TP2 | https://www.youtube.com/watch?v=Ysj4WVNpgzs | público | [x] |
| TP3 | | | |
| TP4 | | | |
| TP5 | | | |
| Final | | | |

## Datasets

| Artefato | Como é gerado | Link |
|---|---|---|
| Dataset de aracnídeos (740 imagens, 5 classes) | `scripts/baixar_dataset.py --por-classe 150` | [COLE O LINK] |
| Atribuição das imagens | gerado junto, `dataset/atribuicao.csv` | — |

## Modelos treinados

| Artefato | Como é gerado | Link |
|---|---|---|
| `yolov8n.onnx` (detector, 13 MB) | `scripts/baixar_modelo.sh` | upstream público |
| `classificador_aranhas.onnx` (5 espécies, 6,1 MB) | `treino/treinar.py --dados train --saida modelo` | [COLE O LINK] |

Métricas do classificador em `docs/evidencias/modelo/modelo_info.json`
(classes, acurácias e matrizes de confusão). O `.json` é texto e está
versionado; o `.onnx` não.

> Todo artefato derivado tem fonte versionada. O script que gera o
> dataset/modelo fica no repositório; o arquivo pesado fica em link público.
