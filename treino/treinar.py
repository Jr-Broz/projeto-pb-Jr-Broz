#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
 treinar.py — classificador de espécies de aracnídeos do projeto ARACNE
═══════════════════════════════════════════════════════════════════════

Roda no Google Colab (GPU grátis) ou em qualquer máquina com PyTorch.
NÃO roda na VM: 4 GB de RAM não treinam CNN em tempo útil. O produto
deste script é um .onnx de ~6 MB que a VM carrega sem PyTorch nenhum.

    python3 treinar.py --dados train --saida modelo

───────────────────────────────────────────────────────────────────────
 AS DECISÕES, E O MOTIVO DE CADA UMA
───────────────────────────────────────────────────────────────────────

1. TRANSFER LEARNING, NÃO TREINO DO ZERO
   São 740 imagens em 5 classes — cerca de 150 por classe. Uma CNN
   treinada do zero precisa de ordens de grandeza mais que isso; com
   esse volume ela decora o conjunto de treino e não generaliza.
   A rede pré-treinada na ImageNet já aprendeu bordas, texturas e
   padrões que servem para qualquer imagem natural. Reaproveitar isso é
   o que torna 740 imagens suficientes.

2. MobileNetV3-Small COMO ESPINHA
   A inferência roda na VM, em CPU, dentro de um nó ROS 2 que também
   precisa de tempo para rastrear e desenhar. MobileNetV3-Small tem
   ~2,5 M de parâmetros contra ~11 M do ResNet-18 e ~5 M do
   EfficientNet-B0. Em CPU a diferença é de dezenas de milissegundos
   por frame — e a 10 Hz isso decide se o pipeline fecha o ciclo ou
   atrasa.
   Trade-off assumido: alguns pontos de acurácia a menos que um modelo
   maior. Com 5 classes visualmente distintas, sobra margem.

3. DUAS FASES: CABEÇA PRIMEIRO, DEPOIS AJUSTE FINO
   Fase 1 — backbone congelado, só a camada final treina, LR alto.
   Fase 2 — últimos blocos descongelados, LR 10x menor.
   O motivo: a cabeça começa com pesos aleatórios e produz gradientes
   enormes nas primeiras épocas. Se o backbone estiver destravado nesse
   momento, esses gradientes destroem as features pré-treinadas — é o
   fenômeno conhecido como esquecimento catastrófico. Congelar na fase
   1 deixa a cabeça estabilizar antes de mexer no que já era bom.

4. AUGMENTATION FORTE EM COR — E A MEDIÇÃO QUE MANDOU FAZER ASSIM
   Um Random Forest treinado SÓ em histograma de cor acerta 69,7%
   destas 5 classes (acaso: 20%). Ou seja: existe um atalho, e a rede
   vai pegá-lo se deixarmos.
   O atalho quebra fora do laboratório. Simulando foto impressa filmada
   por webcam, a acurácia cai 10 pontos.
   A varredura de força do augmentation, medida NO DOMÍNIO ALVO:

        força 0,0 (sem aug) → 57,8%
        força 0,4           → 62,7%
        força 0,8           → 63,2%   <- escolhida
        força 1,2           → 62,7%

   O ótimo é achatado entre 0,4 e 1,2, o que é informação útil: a
   escolha exata importa pouco, mas ter augmentation importa muito.

5. O HIPERPARÂMETRO FOI ESCOLHIDO PELO DOMÍNIO ALVO
   Não pelo conjunto de validação limpo. Escolher pela validação limpa
   premiaria o modelo que melhor decora a distribuição de treino —
   justamente a que não vamos encontrar na defesa.

6. TRÊS AVALIAÇÕES, NÃO UMA
   val limpa    — o número que todo mundo reporta
   val difícil  — impressão filmada: o número que vale para a demo
   matriz       — quais classes o modelo confunde, e com quem
   Reportar só a primeira seria o tipo de otimismo que a arguição
   desmonta em uma pergunta.
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aumentar import augmentar, simular_impressao_webcam   # noqa: E402


# Normalização da ImageNet. Usar OUTROS valores aqui com um backbone
# pré-treinado é um erro silencioso: a rede recebe entradas numa escala
# diferente da que ela viu no pré-treino, e a acurácia cai sem motivo
# aparente.
MEDIA = np.array([0.485, 0.456, 0.406], np.float32)
DESVIO = np.array([0.229, 0.224, 0.225], np.float32)


def para_tensor(im_bgr):
    """BGR uint8 HxWx3  ->  tensor float normalizado CxHxW."""
    rgb = cv2.cvtColor(im_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb = (rgb - MEDIA) / DESVIO
    return torch.from_numpy(rgb.transpose(2, 0, 1))


class DatasetAranhas(Dataset):
    """
    Carrega as imagens EM MEMÓRIA uma vez só.

    São 740 imagens de 224x224 — cerca de 110 MB como uint8. Cabe
    folgado, e evita reler do disco a cada época. No Colab, onde o disco
    é de rede, isso sozinho corta o tempo de época pela metade.
    """

    def __init__(self, caminhos, rotulos, treino, forca_aug=0.8, semente=0):
        self.ims = [cv2.imread(p) for p in caminhos]
        self.y = list(rotulos)
        self.treino = treino
        self.forca = forca_aug
        self.rng = np.random.default_rng(semente)

    def __len__(self):
        return len(self.ims)

    def __getitem__(self, i):
        im = self.ims[i]
        if self.treino:
            # Augmentation ON-THE-FLY, não pré-gerado em disco: a cada
            # época a mesma imagem vira uma variação diferente. Isso
            # multiplica a variedade efetiva sem multiplicar o disco.
            im = augmentar(im, self.rng, self.forca)
        return para_tensor(im), self.y[i]


class DatasetDificil(Dataset):
    """
    Conjunto de teste do DOMÍNIO ALVO: impressão filmada por webcam.

    A degradação é gerada com semente fixa, para que o número seja
    comparável entre execuções. Sem semente fixa, duas rodadas do mesmo
    modelo dariam acurácias diferentes e não daria para saber se a
    mudança foi do modelo ou do sorteio.
    """

    def __init__(self, caminhos, rotulos, semente=12345):
        rng = np.random.default_rng(semente)
        self.ims = [simular_impressao_webcam(cv2.imread(p), rng)
                    for p in caminhos]
        self.y = list(rotulos)

    def __len__(self):
        return len(self.ims)

    def __getitem__(self, i):
        return para_tensor(self.ims[i]), self.y[i]


# ══════════════════════════════════════════════════════════════════
def exportar_onnx(modelo, caminho):
    """
    Exporta para ONNX e CONFERE que o OpenCV consegue ler.

    Devolve True/False em vez de deixar a exceção subir: a exportação é
    a última etapa, e uma falha aqui não pode derrubar o processo e
    levar junto um treino que já terminou.

    dynamo=False força o exportador LEGADO do PyTorch. O exportador novo
    ignora opset_version=12 e exporta em opset 18, que o módulo dnn do
    OpenCV do Ubuntu 22.04 não lê. O modelo carregaria no Colab e
    falharia na VM — o pior tipo de erro, o que só aparece na máquina do
    avaliador. Opset 12 é o maior denominador comum com o OpenCV 4.5.x.
    """
    modelo.eval().cpu()
    exemplo = torch.randn(1, 3, 224, 224)
    kwargs = dict(
        input_names=['entrada'], output_names=['logits'],
        # Eixo de lote dinâmico: permite classificar vários recortes de
        # uma vez no futuro, sem reexportar o modelo.
        dynamic_axes={'entrada': {0: 'lote'}, 'logits': {0: 'lote'}},
        opset_version=12)
    try:
        try:
            torch.onnx.export(modelo, exemplo, caminho, dynamo=False, **kwargs)
        except TypeError:
            # PyTorch anterior ao dynamo: o exportador já é o legado.
            torch.onnx.export(modelo, exemplo, caminho, **kwargs)
    except Exception as e:
        print(f'\nFALHA ao exportar ONNX: {type(e).__name__}: {e}')
        if 'onnx' in str(e).lower():
            print('Provável causa: falta o pacote. No Colab:')
            print('    !pip -q install onnx onnxscript')
        return False

    # Verificação na hora: se o OpenCV não ler o arquivo aqui, não vai
    # ler na VM. Falhar agora, com o modelo em mãos, custa uma
    # reexportação; descobrir na VM custa a sessão.
    try:
        rede = cv2.dnn.readNetFromONNX(caminho)
        rede.setInput(cv2.dnn.blobFromImage(
            np.zeros((224, 224, 3), np.uint8), 1 / 255.0, (224, 224)))
        print(f'verificação OpenCV DNN: OK, saída {rede.forward().shape}')
    except cv2.error as e:
        print(f'AVISO: o OpenCV NÃO leu o ONNX ({e}). '
              'O nó ROS não vai conseguir carregá-lo.')
        return False
    return True


# ══════════════════════════════════════════════════════════════════
def construir_modelo(n_classes, arquitetura='mobilenet_v3_small'):
    import torchvision.models as M
    if arquitetura == 'mobilenet_v3_small':
        m = M.mobilenet_v3_small(weights='IMAGENET1K_V1')
        em = m.classifier[-1].in_features
        m.classifier[-1] = nn.Linear(em, n_classes)
        blocos_finais = list(m.features[-4:].parameters())
    elif arquitetura == 'resnet18':
        m = M.resnet18(weights='IMAGENET1K_V1')
        m.fc = nn.Linear(m.fc.in_features, n_classes)
        blocos_finais = list(m.layer4.parameters())
    else:
        raise ValueError(arquitetura)
    return m, blocos_finais


def avaliar(modelo, loader, dispositivo, n_classes):
    modelo.eval()
    certos = total = 0
    matriz = np.zeros((n_classes, n_classes), int)
    with torch.no_grad():
        for x, y in loader:
            x = x.to(dispositivo)
            pred = modelo(x).argmax(1).cpu().numpy()
            y = np.asarray(y)
            for v, p in zip(y, pred):
                matriz[v, p] += 1
            certos += int((pred == y).sum())
            total += len(y)
    return certos / max(total, 1), matriz


def treinar_fase(modelo, loader_tr, loader_val, dispositivo, n_classes,
                 epocas, lr, params, nome, log):
    otim = torch.optim.AdamW(params, lr=lr, weight_decay=1e-4)
    # Agendador cosseno: o LR cai suavemente até quase zero no fim.
    # Terminar com LR alto deixa o modelo oscilando em torno do mínimo
    # em vez de assentar nele.
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(otim, T_max=epocas)
    # Label smoothing 0.1: impede o modelo de ficar 100% confiante.
    # Importa aqui porque o nó ROS usa a confiança como limiar de
    # rejeição — um modelo que sempre diz 0.999 torna o limiar inútil.
    crit = nn.CrossEntropyLoss(label_smoothing=0.1)

    melhor = 0.0
    melhor_estado = None
    for ep in range(epocas):
        modelo.train()
        perda_total = n = 0
        for x, y in loader_tr:
            x = x.to(dispositivo)
            y = torch.as_tensor(y).to(dispositivo)
            otim.zero_grad()
            perda = crit(modelo(x), y)
            perda.backward()
            otim.step()
            perda_total += float(perda) * len(y)
            n += len(y)
        sched.step()
        acc, _ = avaliar(modelo, loader_val, dispositivo, n_classes)
        linha = (f'  [{nome}] época {ep+1:2d}/{epocas} | '
                 f'perda {perda_total/max(n,1):.4f} | val {acc*100:5.2f}%')
        print(linha)
        log.append(linha)
        if acc > melhor:
            melhor = acc
            melhor_estado = {k: v.detach().cpu().clone()
                             for k, v in modelo.state_dict().items()}
    if melhor_estado:
        modelo.load_state_dict(melhor_estado)
    return melhor


# ══════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dados', default='train')
    ap.add_argument('--saida', default='modelo')
    ap.add_argument('--arquitetura', default='mobilenet_v3_small')
    ap.add_argument('--epocas-cabeca', type=int, default=12)
    ap.add_argument('--epocas-ajuste', type=int, default=18)
    ap.add_argument('--lote', type=int, default=32)
    ap.add_argument('--forca-aug', type=float, default=0.8)
    ap.add_argument('--sem-aug', action='store_true',
                    help='baseline sem augmentation, para a comparação')
    ap.add_argument('--semente', type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.semente)
    np.random.seed(args.semente)
    os.makedirs(args.saida, exist_ok=True)

    dispositivo = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'dispositivo: {dispositivo}')
    if dispositivo == 'cpu':
        print('AVISO: sem GPU o treino leva muito mais tempo. '
              'No Colab: Ambiente de execução > Alterar tipo > GPU')

    # ---------- dados ----------
    classes = sorted([d for d in os.listdir(args.dados)
                      if os.path.isdir(os.path.join(args.dados, d))])
    caminhos, rotulos = [], []
    for ci, c in enumerate(classes):
        for nome in sorted(os.listdir(os.path.join(args.dados, c))):
            if nome.lower().endswith(('.jpg', '.jpeg', '.png')):
                caminhos.append(os.path.join(args.dados, c, nome))
                rotulos.append(ci)
    caminhos = np.array(caminhos)
    rotulos = np.array(rotulos)
    print(f'{len(caminhos)} imagens em {len(classes)} classes')
    for ci, c in enumerate(classes):
        print(f'  {c:<30} {(rotulos == ci).sum():4d}')

    # Split ESTRATIFICADO: cada classe mantém sua proporção no treino e
    # na validação. Com um split aleatório simples, uma classe pequena
    # pode ficar sub-representada na validação e a métrica dela vira
    # ruído.
    from sklearn.model_selection import train_test_split
    i_tr, i_val = train_test_split(np.arange(len(caminhos)), test_size=0.2,
                                   stratify=rotulos,
                                   random_state=args.semente)
    print(f'treino {len(i_tr)} | validação {len(i_val)}')

    forca = 0.0 if args.sem_aug else args.forca_aug
    ds_tr = DatasetAranhas(caminhos[i_tr], rotulos[i_tr],
                           treino=not args.sem_aug, forca_aug=forca,
                           semente=args.semente)
    ds_val = DatasetAranhas(caminhos[i_val], rotulos[i_val], treino=False)
    ds_dur = DatasetDificil(caminhos[i_val], rotulos[i_val])

    ld_tr = DataLoader(ds_tr, batch_size=args.lote, shuffle=True, num_workers=2)
    ld_val = DataLoader(ds_val, batch_size=args.lote, num_workers=2)
    ld_dur = DataLoader(ds_dur, batch_size=args.lote, num_workers=2)

    # ---------- modelo ----------
    modelo, blocos_finais = construir_modelo(len(classes), args.arquitetura)
    modelo = modelo.to(dispositivo)
    log = []

    t0 = time.time()

    # Fase 1: só a cabeça
    for p in modelo.parameters():
        p.requires_grad = False
    cabeca = (modelo.classifier[-1] if hasattr(modelo, 'classifier')
              else modelo.fc)
    for p in cabeca.parameters():
        p.requires_grad = True
    print('\n--- fase 1: backbone congelado, treinando a cabeça ---')
    treinar_fase(modelo, ld_tr, ld_val, dispositivo, len(classes),
                 args.epocas_cabeca, 1e-3, cabeca.parameters(), 'cabeça', log)

    # Fase 2: ajuste fino dos últimos blocos
    for p in blocos_finais:
        p.requires_grad = True
    treinaveis = [p for p in modelo.parameters() if p.requires_grad]
    print('\n--- fase 2: ajuste fino dos últimos blocos (LR 10x menor) ---')
    acc_val = treinar_fase(modelo, ld_tr, ld_val, dispositivo, len(classes),
                           args.epocas_ajuste, 1e-4, treinaveis, 'ajuste', log)

    tempo = time.time() - t0

    # ─────────────────────────────────────────────────────────────
    # SALVAR OS PESOS AGORA, antes de qualquer outra coisa.
    #
    # Isto é a primeira coisa depois do treino de propósito. A primeira
    # versão deste script exportava para ONNX direto e só salvava os
    # metadados no fim — e quando a exportação falhou por falta de uma
    # dependência, 20 minutos de GPU foram para o lixo porque o modelo
    # só existia na memória do processo que morreu.
    #
    # A regra geral: o resultado caro vai para o disco assim que existe.
    # Tudo que vem depois (avaliar, exportar, plotar) é barato de
    # refazer a partir do .pth; o treino não é.
    # ─────────────────────────────────────────────────────────────
    caminho_pth = os.path.join(args.saida, 'checkpoint.pth')
    torch.save({'state_dict': modelo.state_dict(),
                'classes': classes,
                'arquitetura': args.arquitetura}, caminho_pth)
    print(f'\n>>> pesos salvos em {caminho_pth} '
          f'({os.path.getsize(caminho_pth)/1e6:.1f} MB)')
    print('    se algo falhar daqui para a frente, o treino NÃO se perde:')
    print(f'    python3 exportar.py --checkpoint {caminho_pth}')

    # ---------- avaliação ----------
    acc_val, mat_val = avaliar(modelo, ld_val, dispositivo, len(classes))
    acc_dur, mat_dur = avaliar(modelo, ld_dur, dispositivo, len(classes))

    print('\n' + '═' * 66)
    print(f'  validação limpa              : {acc_val*100:5.2f}%')
    print(f'  validação impressa + webcam  : {acc_dur*100:5.2f}%')
    print(f'  queda de domínio             : {(acc_val-acc_dur)*100:5.2f} pontos')
    print(f'  tempo de treino              : {tempo/60:.1f} min')
    print('═' * 66)

    print('\nmatriz de confusão (validação limpa) — linha = verdade:')
    print(' ' * 32 + ''.join(f'{i:>6}' for i in range(len(classes))))
    for i, c in enumerate(classes):
        print(f'{i} {c:<28}' + ''.join(f'{v:>6}' for v in mat_val[i]))

    # Acurácia por classe: a média esconde a classe ruim. Se uma classe
    # tem 40% e as outras 95%, a média de 84% parece boa e o sistema não
    # é utilizável para aquela espécie.
    print('\nacurácia por classe (limpa / impressa):')
    for i, c in enumerate(classes):
        tv = mat_val[i].sum()
        td = mat_dur[i].sum()
        av = mat_val[i, i] / tv if tv else 0
        ad = mat_dur[i, i] / td if td else 0
        print(f'  {c:<30} {av*100:5.1f}% / {ad*100:5.1f}%')

    # ---------- metadados (ANTES da exportação) ----------
    # Os números do relatório não podem depender de a exportação dar
    # certo. Se o ONNX falhar, você ainda tem acurácia, matriz de
    # confusão e log de treino para escrever o relatório, e um .pth
    # para reexportar depois.
    meta = {
        'classes': classes,
        'arquitetura': args.arquitetura,
        'entrada': [1, 3, 224, 224],
        'normalizacao': {'media': MEDIA.tolist(), 'desvio': DESVIO.tolist()},
        'augmentation': 'nenhum' if args.sem_aug else f'forca {forca}',
        'acuracia_validacao_limpa': round(acc_val, 4),
        'acuracia_validacao_impressa': round(acc_dur, 4),
        'queda_de_dominio': round(acc_val - acc_dur, 4),
        'matriz_confusao_limpa': mat_val.tolist(),
        'matriz_confusao_impressa': mat_dur.tolist(),
        'acuracia_por_classe_limpa': {
            c: round(float(mat_val[i, i] / max(mat_val[i].sum(), 1)), 4)
            for i, c in enumerate(classes)},
        'acuracia_por_classe_impressa': {
            c: round(float(mat_dur[i, i] / max(mat_dur[i].sum(), 1)), 4)
            for i, c in enumerate(classes)},
        'imagens_treino': int(len(i_tr)),
        'imagens_validacao': int(len(i_val)),
        'tempo_treino_min': round(tempo / 60, 2),
        'semente': args.semente,
    }
    with open(os.path.join(args.saida, 'modelo_info.json'), 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.saida, 'treino_log.txt'), 'w') as f:
        f.write('\n'.join(log) + '\n')
    print(f'\n>>> métricas salvas em {args.saida}/modelo_info.json')

    # ---------- exportação ----------
    modelo.eval().cpu()
    caminho_onnx = os.path.join(args.saida, 'classificador_aranhas.onnx')
    if exportar_onnx(modelo, caminho_onnx):
        tam = os.path.getsize(caminho_onnx) / 1e6
        print(f'ONNX salvo: {caminho_onnx} ({tam:.1f} MB)')
    else:
        print('\n' + '!' * 66)
        print('A exportação ONNX falhou, mas o TREINO ESTÁ SALVO.')
        print(f'Instale a dependência que faltou e rode:')
        print(f'    python3 exportar.py --checkpoint {caminho_pth}')
        print('!' * 66)
