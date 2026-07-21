# Tutorial — Workspace Colcon e o seu primeiro pacote ROS 2

**Pré-requisito:** setup WSL2 + ROS 2 Humble concluído. Tempo: ~20 min.
⚠️ **Todos os comandos deste tutorial rodam DENTRO do WSL** (terminal do Ubuntu-22.04) — nunca no PowerShell/CMD. Na dúvida sobre em qual distro você está: `lsb_release -a`.

## 0. Onde clonar o repositório (importante!)

Quando o seu repositório `projeto-pb-<usuario>` existir (a partir da aula 2), **clone-o DENTRO do filesystem do WSL**, na sua home do Ubuntu — **não** em `/mnt/c/...` (o disco do Windows):

```bash
cd ~                                      # home do Ubuntu — o lugar certo
gh repo clone Prof-Dacio-INFNET/projeto-pb-SEU-USUARIO
```

Por quê: compilar com colcon em `/mnt/c` é **muito mais lento** (o acesso ao disco do Windows pelo WSL tem alto custo) e causa problemas de permissões e fins de linha. O repositório sincroniza pelo **GitHub** (push/pull), então ele não precisa — e não deve — ficar em pasta do Windows/OneDrive. Para editar com conforto: instale o VS Code no Windows com a extensão **WSL** e, dentro da pasta do projeto no Ubuntu, rode `code .` — o editor abre no Windows operando direto nos arquivos do WSL.

*Ainda sem o repositório? Pratique este tutorial num workspace de treino: `mkdir -p ~/treino_ws/src` e use `~/treino_ws` no lugar de `ros2_ws` abaixo.*

> 💡 **Vindo do Windows/DOS?** Os tropeços clássicos: é `cd ~` (**com espaço**) e não `cd~`; `mkdir` e não `md`; `ls` e não `dir`; barras `/` e não `\`; e `cd` sozinho já leva para a home. Maiúsculas importam: `Downloads` ≠ `downloads`.

## 1. O conceito

Um **workspace** é a pasta onde seus pacotes vivem e são compilados: código em `src/`, o `colcon build` gera `build/`, `install/` e `log/` (que **nunca** vão para o git — o `.gitignore` do template já cuida). Depois de compilar, o `source install/setup.bash` "apresenta" seus pacotes ao ROS 2 **naquele terminal**.

## 2. Compilar o workspace do seu projeto

```bash
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
colcon build
source install/setup.bash
```

> Duas regras que evitam 90% das dores: (1) **compile sempre na raiz do workspace** (`ros2_ws/`), nunca dentro de `src/`; (2) **após cada build, faça o source** — terminal novo = source de novo. Dica: `colcon build --symlink-install` permite editar arquivos Python sem recompilar.

## 3. Criar o seu primeiro pacote

```bash
cd ~/projeto-pb-SEU-USUARIO/ros2_ws/src
ros2 pkg create --build-type ament_python --node-name meu_no meu_pacote
cd .. && colcon build && source install/setup.bash
ros2 run meu_pacote meu_no    # "Hi from meu_pacote."
```

Anatomia do pacote (`ament_python`): `package.xml` (metadados e dependências), `setup.py` (o `entry_points` mapeia executável → função), `meu_pacote/` (seus módulos Python). Um exemplo completo com boas práticas está no seu repositório: `exemplos/pacote_minimo/` — copie para `src/` e adapte:

```bash
cp -r ../exemplos/pacote_minimo src/
colcon build --packages-select pacote_minimo && source install/setup.bash
ros2 launch pacote_minimo exemplo.launch.py
```

## 4. Comandos do dia a dia

```bash
colcon build --packages-select meu_pacote   # compila só um pacote (mais rápido)
colcon build --symlink-install              # edita Python sem rebuild
rosdep install --from-paths src --ignore-src -r -y   # instala dependências declaradas
colcon test                                  # roda testes (mais adiante no curso)
```

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `Package 'meu_pacote' not found` | Faltou `source install/setup.bash` neste terminal (ou o build falhou) |
| Mudei o código e nada mudou | Sem `--symlink-install`, recompile; com ele, confira se salvou o arquivo |
| Build falha após renomear coisas | Nome deve bater em `package.xml`, `setup.py` e pasta do módulo; na dúvida `rm -rf build install log` e recompile |
| `colcon: command not found` | `sudo apt install python3-colcon-common-extensions` |

## Checklist

- [ ] `colcon build` limpo no `ros2_ws` do seu repositório · - [ ] `pacote_minimo` rodando via launch · - [ ] primeiro pacote próprio criado e executando · - [ ] commit + push (`git add . && git commit -m "Cria primeiro pacote" && git push`)
