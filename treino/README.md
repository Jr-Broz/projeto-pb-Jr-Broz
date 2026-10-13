# Treino do classificador de aracnídeos — ARACNE

Produz o `classificador_aranhas.onnx` que o `deteccao_node` carrega na VM.

## Onde rodar, e por quê não na VM

| Ambiente | Treino | Inferência |
|---|---|---|
| VM Ubuntu (4 GB) | ✗ não cabe | ✓ via OpenCV DNN |
| Google Colab (GPU) | ✓ ~10 min | — |

Treinar exige PyTorch (2–3 GB) e memória para os lotes. A VM tem 4 GB
no total e ainda precisa rodar o ROS. Inferir é outra coisa: o ONNX tem
~6 MB e o OpenCV já instalado o executa sem PyTorch nenhum.

É a divisão padrão em robótica — treina-se fora, embarca-se o modelo.

## Rodando no Colab

1. `colab.research.google.com` → Novo notebook
2. **Ambiente de execução → Alterar tipo → GPU (T4)**
3. Suba `train.zip`, `treinar.py` e `aumentar.py` pelo painel de arquivos
4. Numa célula:

```python
# onnx e onnxscript NÃO vêm no Colab — sem eles o treino roda e a
# exportação falha no último passo.
!pip -q install onnx onnxscript opencv-python-headless
!unzip -qo train.zip

# baseline: sem augmentation
!python treinar.py --dados train --saida modelo_sem_aug --sem-aug

# modelo final: com augmentation
!python treinar.py --dados train --saida modelo
```

5. Baixe `modelo/classificador_aranhas.onnx` e `modelo/modelo_info.json`

Os dois treinos são o que o gate **G4.6** pede: *"comparação com/sem
augmentation e matriz de confusão"*. Rodar os dois custa ~20 min e
rende uma tabela que é difícil de contestar.

## O que o script reporta

```
validação limpa              : XX.XX%
validação impressa + webcam  : XX.XX%
queda de domínio             : XX.XX pontos
```

A segunda linha é a que vale para a defesa. A primeira é a que todo
mundo reporta — e a que some quando a webcam entra em cena.

## Arquivos

| Arquivo | Papel |
|---|---|
| `aumentar.py` | augmentation + simulação do domínio alvo |
| `treinar.py` | transfer learning em duas fases + avaliação + export ONNX |
| `exportar.py` | reexporta o `.pth` para ONNX sem retreinar |
| `modelo/checkpoint.pth` | pesos crus, salvos logo após o treino |
| `modelo/classificador_aranhas.onnx` | o produto, vai para `models/` do repo |
| `modelo/modelo_info.json` | classes, acurácias, matrizes — fonte dos números do relatório |

## Depois do treino

```bash
cp classificador_aranhas.onnx ~/projeto-pb/models/
ros2 param set /deteccao_node modelo_classificador \
  $HOME/projeto-pb/models/classificador_aranhas.onnx
```

O peso **não** vai para o git (regra da disciplina: arquivo grande em
link público). `scripts/baixar_modelo.sh` é a fonte versionada.

## Os números que já temos, medidos antes de treinar

Com o Random Forest em histograma de cor, sem nenhuma informação de
forma:

| Experimento | Resultado |
|---|---|
| Classes separáveis só por cor | **69,7%** (acaso: 20%) |
| Queda ao simular impressão + webcam | **−9,7 pontos** |
| Com augmentation de cor | queda cai para **−5,9** |
| Varredura de força (ótimo) | **0,8** → 63,2% no domínio alvo |

O primeiro número é o que justifica todo o resto: existe um atalho de
cor, e sem augmentation a rede vai pegá-lo.

## Se a exportação falhar

O `treinar.py` salva `modelo/checkpoint.pth` **antes** de avaliar e
exportar. Então uma falha na exportação não custa o treino:

```bash
pip install onnx onnxscript
python3 exportar.py --checkpoint modelo/checkpoint.pth
```

Segundos, em vez de repetir os 20 minutos de GPU.

A ordem do script é deliberada: **treinar → salvar pesos → avaliar →
salvar métricas → exportar**. O resultado caro vai para o disco assim
que existe; tudo que vem depois é barato de refazer.
