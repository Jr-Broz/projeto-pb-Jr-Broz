# Tutorial do Aluno — GitHub e o Repositório do Projeto de Bloco

**Disciplina:** Projeto de Bloco: Sistemas Robóticos · **Prof.:** Dácio Moreira de Souza

> ## ⚠️ Antes de tudo: onde a entrega vale
>
> **A entrega oficial de TODO TP — e do projeto final — é feita no MOODLE**, obrigatoriamente com: **ZIP com os códigos**, **PDF do relatório**, **link do repositório**, **link do vídeo** e tudo mais que o enunciado pedir, **registrado por lá**. O Moodle é a fonte da verdade da entrega: **o que não está no Moodle não foi entregue**, mesmo que esteja no GitHub.
>
> O GitHub é **complementar e obrigatório** (não é apoio dispensável): é onde você desenvolve, versiona, sincroniza laboratório↔casa e onde o professor **corrige o seu código** (no estado da sua branch/tag de entrega) — e a **qualidade do repositório é critério de avaliação** em todos os TPs. Moodle **e** GitHub, sempre os dois.

## Parte A — Semana 1: prepare sua conta

### A1. Conta no GitHub (5 min)

1. Se ainda não tem: crie em [github.com/signup](https://github.com/signup) com um **nome de usuário profissional** — ele aparecerá no seu repositório e, um dia, no seu currículo. O professor é `dacioms`, por exemplo. Já `capitao-gambiarra`, por mais que descreva com precisão certos momentos da robótica, talvez não seja a melhor escolha (ele será nosso aluno-exemplo fictício neste tutorial).
2. Use um e-mail que você **acessa de verdade** (você vai precisar dele na Parte B) e ative a **autenticação em dois fatores** (Settings → Password and authentication).
3. (Recomendado) Solicite o [Student Developer Pack](https://education.github.com/pack) com o e-mail institucional — Copilot e outros benefícios grátis.

### A2. Git e GitHub CLI (5 min — faça no laboratório E em casa)

No terminal do Ubuntu/WSL2 (ver tutorial de setup do ambiente):

```bash
sudo apt update && sudo apt install -y git gh
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@exemplo.com"
gh auth login    # GitHub.com → HTTPS → Login with a web browser
```

Repita em **cada máquina** que usar (computador do laboratório, notebook, PC de casa).

## Parte B — Aceitar o assignment (quando o professor liberar o link)

1. Abra o **link de convite** (Moodle / projetado em aula) e faça login no GitHub.
2. **Selecione o SEU NOME na lista da turma** (roster) — é isso que vincula sua conta a você na correção. Não pule; não escolha o nome do colega.
3. Clique em **Accept this assignment**.
4. **📧 PASSO QUE A DOCUMENTAÇÃO DO GITHUB NÃO DESTACA:** abra o **e-mail** cadastrado na sua conta GitHub e **aceite o convite** ("You've been invited to Prof-Dacio-INFNET…"). **Sem aceitar o convite, o repositório dá erro 404.** Alternativa se o e-mail não chegar: [github.com/orgs/Prof-Dacio-INFNET/invitation](https://github.com/orgs/Prof-Dacio-INFNET/invitation) (e confira o spam).
5. Recarregue a página do assignment: aparecerá o link do seu repositório **privado** — ex.: `projeto-pb-capitao-gambiarra`. Só você e o professor têm acesso.

## Parte C — Clonar e conhecer o repositório

```bash
cd ~
gh repo clone Prof-Dacio-INFNET/projeto-pb-SEU-USUARIO   # ex.: projeto-pb-dacioms
cd projeto-pb-SEU-USUARIO
```

| Pasta/arquivo | O que vai aí |
|---|---|
| `README.md` | Identificação, como executar, status dos TPs — **preencha já no 1º dia** |
| `PROJETO.md` | Proposta e planejamento do seu projeto (TP1; evolui depois) |
| `ARTEFATOS.md` | **Links dos vídeos (por TP) e artefatos grandes** + como cada um é gerado |
| `scripts/` | `setup.sh` e `reproduzir.sh` — o professor corrige executando-os! |
| `ros2_ws/src/` | Seus pacotes ROS 2 |
| `docs/relatorios/` · `docs/evidencias/` | Relatórios entregues e capturas por TP |
| `docs/decisoes.md` | **Registro do que mudou no projeto, onde e por quê** (ver Parte E) |
| `docs/diario.md` | Diário de desenvolvimento (recomendado) |
| `media/` | Vídeos curtos/GIFs leves (longos → YouTube) |
| `consulta/` | Cheatsheets de git, ROS 2 e regras de entrega — não editar |
| `exemplos/` | Código-base de referência: **copie para `ros2_ws/src` e adapte** ao seu projeto |

**O que você pode e não pode mudar:** pode **adicionar** qualquer estrutura útil ao seu desenvolvimento; **não pode alterar nem remover** as estruturas de referência de entrega (README, PROJETO, ARTEFATOS, scripts/, docs/, consulta/, .github/). Um verificador automático acusa (X vermelho no commit) se algo protegido sumir. Os `exemplos/` são seus: adapte à vontade.

## Parte D — O ciclo laboratório ↔ casa e as branches

**O repositório é a sua mochila** — nada fica só na máquina do laboratório:

```bash
git pull          # AO COMEÇAR (lab ou casa)
git add . && git commit -m "Implementa publisher de câmera em /camera/image_raw"
git push          # AO TERMINAR (especialmente no fim da aula!)
```

Commits **pequenos e frequentes**, mensagens que dizem o que a mudança faz. O histórico é critério de avaliação — um commit gigante na véspera conta contra você. Trabalho perdido por falta de push no laboratório é responsabilidade sua.

**Branches:** use à vontade para desenvolver com segurança (`git checkout -b feat/deteccao-faixas`), **mas a correção e as entregas olham exclusivamente a `main`**: antes da tag do TP, faça merge de tudo que conta (`git checkout main && git merge feat/deteccao-faixas && git push`). Branch não mergeada = trabalho invisível para a correção. Mantenha a `main` sempre compilável.

## Parte E — Reprodutibilidade e evolução documentada

O professor corrige **clonando e executando**:

```bash
./scripts/setup.sh        # dependências além do padrão da disciplina
./scripts/reproduzir.sh   # compila, obtém/gera artefatos, roda a demo
```

Reproduziu de primeira? **Destaque na avaliação.** Precisou adivinhar comandos? Perde pontos de organização. Regras:

- **Todo artefato derivado tem fonte:** o script que gera o modelo/dataset/mapa fica versionado. Treino demorado? O `reproduzir.sh` **baixa** do seu link público e o comando de treino fica documentado ao lado.
- **Arquivo grande não entra no git:** Google Drive/OneDrive com **link público**, registrado em `ARTEFATOS.md`.
- **Seu projeto vai mudar — e tudo bem.** Escopo, sensores e arquitetura podem ser refinados ao longo dos TPs. O que a disciplina espera é o que se espera de um engenheiro: **rastreabilidade**. Cada mudança relevante ganha uma entrada no `docs/decisoes.md` (data, o que mudou, onde, por quê, impacto) e o `PROJETO.md` reflete o plano atual. Refatorar com registro é sinal de maturidade; mudar silenciosamente parece improviso.

## Parte F — Como entregar cada TP

**1) Entrega oficial — MOODLE (obrigatória, é o que vale).** O Moodle aceita **até 4 arquivos de 20 MB cada**. O desejável: **1 PDF** com o relatório completo e detalhado + **ZIPs pertinentes** com os códigos (+ os links de repo e vídeo registrados no envio).

*E se não couber?* Priorize nos ZIPs: código-fonte, launch/config e evidências-chave. O que exceder (datasets, modelos treinados, vídeos) fica no GitHub/links públicos, referenciado no `ARTEFATOS.md` e citado no relatório — **use essa divisão apenas quando realmente necessário**; o padrão é caber no Moodle.

**Confira duas vezes:** arquivo errado, corrompido ou incompleto enviado é responsabilidade sua. Depois do upload, **baixe e abra** o próprio ZIP/PDF para conferir o que de fato subiu.

**Uma dica de quem já corrigiu muito TP:** commits no GitHub e envios no Moodle têm carimbo de data e hora — eles contam a sua linha do tempo por você. Links "vivos" de drive não registram quando o arquivo ficou disponível. Prefira deixar o que é da entrega commitado ou anexado até o prazo: isso **protege você** de qualquer dúvida sobre datas, sem depender da memória de ninguém.

**2) Fotografia no repositório — branch + tag (complementar, obrigatória p/ correção do código):**

No 1º dia, rode uma vez `./scripts/init-branches.sh` (cria `dev` e as branches `entrega-*`). Você trabalha na **`dev`**; a **`main`** guarda o estado estável. Na entrega:

```bash
git checkout main && git merge dev && git push              # 1) main completa
git checkout entrega-tpN && git merge --ff-only main && git push   # 2) branch = main
git tag tpN && git push origin tpN                          # 3) tag imutável
git checkout dev                                            # 4) volte a trabalhar
```

| TP | Branch / Tag | Prazo (sexta, 23h59) |
|---|---|---|
| TP1 | `entrega-tp1` / `tp1` | 28/08 |
| TP2 | `entrega-tp2` / `tp2` | 25/09 |
| TP3 | `entrega-tp3` / `tp3` | 23/10 |
| TP4 | `entrega-tp4` / `tp4` | **21/11 (sáb) 12h00** (20/11 é feriado) |
| TP5 | `entrega-tp5` / `tp5` | 27/11 |
| Final | `entrega-final` / `final` | 04/12 |

> ⚠️ **Depois de entregar, NÃO altere a branch `entrega-tpN` nem a tag `tpN`** — elas são a fotografia da entrega e **vale a data da última alteração**. Continue evoluindo o projeto na `dev`/`main`.

**Checklist antes de fechar:** dev→main mergeado → entrega-tpN == main + tag → front-matter do README atualizado (entregue/branch/tag/video/data) → `ARTEFATOS.md` com vídeo e artefatos (links testados em aba anônima) → `reproduzir.sh` roda num clone limpo → `docs/decisoes.md` atualizado → **Moodle enviado e conferido**.

> Errou a tag? `git tag -d tp1 && git push origin :refs/tags/tp1`, corrija e recrie (antes do prazo).

## Problemas comuns

| Sintoma | Causa/solução |
|---|---|
| **Aceitei, mas o repositório dá 404** | **Convite pendente no e-mail** (Parte B, passo 4). Aceite pelo link do e-mail ou em `github.com/orgs/Prof-Dacio-INFNET/invitation`; confira o spam |
| Aceitei sem escolher meu nome na lista | Avise o professor — ele vincula sua conta ao roster |
| `Permission denied` no clone/push | `gh auth login` nesta máquina; confirme que é o **seu** `projeto-pb-…` |
| `rejected: fetch first` no push | Você editou em outra máquina sem pull. `git pull`, resolva, `git push` |
| "Meu trabalho não apareceu na correção" | Estava numa branch não mergeada na `main` — merge antes da tag |
| Trabalho do lab não está em casa | Faltou `git push` no lab. Crie o hábito da Parte D |
| X vermelho no commit (estrutura) | Você alterou/removeu algo protegido — restaure (Parte C) |
| Professor disse que meu link/vídeo "não existe" | Estava privado/restrito. Teste em aba anônima; corrija o compartilhamento |
| Não acho meu repositório | github.com → seu avatar → *Your organizations* → `Prof-Dacio-INFNET` |

## Regras importantes

- **Moodle é a entrega oficial** — sem exceção. GitHub sem Moodle = não entregue.
- **Vídeos: YouTube "público" OU "não listado" — nunca "privado".** Drives: "qualquer pessoa com o link". **Links são responsabilidade sua: inacessível = inexistente.**
- Correção e entrega olham a **`main`**; estruturas protegidas do repositório não se alteram nem removem.
- O repositório é **privado**: não torne público nem copie de colegas — commits têm autor, data e hora.
- Uso de IA generativa: siga a orientação da disciplina (declaração de uso no relatório; a arguição valida a autoria).
- Dúvidas de git **não são vergonha** — traga na aula ou no Infnet.Online.
