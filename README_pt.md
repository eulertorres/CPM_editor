<div align="right">
  <a href="./README.md"><button>English</button></a>
  <a href="./README_pt.md"><button>Português</button></a>
</div>

# CPM_Editor

O CPM_Editor é um assistente desktop para inspecionar e manipular arquivos **Custom Player Model (.cpmproject)**. Ele abre dois projetos lado a lado (Projeto 1 e Projeto 2), permite copiar ou reendereçar partes do modelo e animações e automatiza tarefas repetitivas como montar a hierarquia +Movment ou interpolar frames.

## Primeiros passos
- **Requisitos:** Python 3 com PyQt6 instalado.
- **Como rodar:**
  ```bash
  python main.py
  ```
- **Projetos:** Use os botões da barra superior para carregar `Projeto 1` e `Projeto 2`. O Projeto 2 é o alvo editável; `Salvar Projeto 2` sobrescreve o arquivo aberto e `Salvar como...` permite escolher outro destino (com extensão `.cpmproject`).
- **Opções & tema:** Clique em **Opções** para alternar *Mostrar apenas elementos* (padrão ativado), *Modo escuro* (paleta global) e *Colorir elementos pelo config.json* (aplica `nameColor` ao texto da árvore). A barra superior também traz um atalho para o repositório GitHub.

## Principais recursos
### Aba Modelos
- **Filtro e estilo de elementos:** Elementos e atributos aparecem em cores distintas; o toggle "apenas elementos" reduz a árvore ao root e aos nós de elemento. Os rótulos podem usar o `nameColor` do projeto (quando habilitado em Opções).
- **Notificações na barra de status:** Mensagens de sucesso/erro/info ficam fixas na barra inferior, com fonte maior, sem pop-ups.
- **Copiar/colar e pesquisa:** Duplique rapidamente elementos entre projetos e localize nós pelo diálogo de busca.
- **Gerador +Movment:**
  - Detecta nomes padrões de membros ou deixa você escolher manualmente 8 partes.
  - Duplica cada membro com prefixo `Anti_`, monta as hierarquias de braço/perna, e mantém `children` após `DisableVanillaAnim` e antes de `v`.
  - Normaliza tamanhos/posições (tamanho Y = 7 para primários, 6 para Anti_; posição Y = 6 para anti braços/pernas) e preserva `u`/`v` mesmo aplicando face UV.
  - Tratamento de UV por face desloca V em +6 (considerando `Tex scale 2` e o multiplicador **skin x128**), mantém Down em Anti_ braços/pernas, remove Down em calças e aplica os deslocamentos pedidos.
  - **Checkbox de DEBUG** chama "Salvar como..." a cada etapa interna (clonar, mover, ajustar tamanho/posição, aplicar UV).
- **Mover textura:** Exibe o `skin.png`, desenhando o retângulo UV atual e o deslocado após `dU`/`dV` para pré-visualizar offsets.
- **Ferramenta de colorir hierarquia:** Grava `nameColor` no Projeto 2 conforme a profundidade usando a paleta `24FFFF`, `00FF00`, `FFFF00`, `00FF89` (repetindo por nível) e reconstrói a árvore.
- **Renomear com prefixo/sufixo:** Escolha um elemento, adicione prefixo/sufixo, remova qualquer "(N)" no final do nome e, se desejar, aplique a todos os filhos.
- **Aplicar frame ao modelo:** Selecione uma animação e um frame; as transformações do frame são **somadas** à pose do modelo, enquanto os mesmos deslocamentos são subtraídos de todos os frames dessa animação para manter o movimento relativo.

### Aba Animações
- **Lista estruturada:** As animações são lidas da pasta `animations/` dentro do `.cpmproject`, com nomes derivados dos arquivos (Pose começa com `v_`, Value/Layer com `g_`).
- **Copiar & colar entre projetos:** Copie animações do Projeto 1 para a área de transferência e cole no Projeto 2. StoreIDs continuam sendo o mapa oficial, mas a interface mostra nomes de elementos e IDs curtos; os combos de mapeamento quebram em colunas para evitar janelas muito altas.
- **Interpolação de frames:** Insere frames intermediários entre dois frames escolhidos, interpolando posição e rotação para todos os componentes envolvidos. Salve na mesma animação ou em um novo arquivo.
- **Aplicar frame ao modelo:** (Fluxo compartilhado) permite reaproveitar poses diretamente na estrutura do modelo.

## Modo escuro
Ative em **Opções** para aplicar uma paleta escura consistente (fundos escuros, texto claro e destaques) em todos os widgets.

## Change log
### alpha-0.1.0 (main)
+ Abrir dois arquivos `.cpmproject`, navegar/editar a árvore do `config.json` e salvar alterações no Projeto 2.
+ Copiar/colar elementos do modelo e ajustar UV/posições pelas ferramentas existentes e diálogo de busca.

### beta-0.2.0 (esta branch)
+ Adicionado "Salvar como..." com caminhos padrão, extensão forçada e ganchos de depuração.
+ Adicionada distinção visual entre elementos e atributos na árvore e visão apenas de elementos (padrão ativado).
+ Adicionado gerador +Movment: escolhe membros, clona com `Anti_`, monta hierarquias de braço/perna, reordena `children`, redimensiona/reposiciona partes e preserva `u`/`v` aplicando UV por face (incluindo regras de Down e o multiplicador **skin x128**).
+ Adicionadas gravações de depuração por etapa no +Movment e correções de deslocamento de UV considerando Tex scale e offset em V.
+ Adicionadas mensagens na barra de status em vez de pop-ups.
+ Adicionado modo escuro global e reorganizado o toggle de apenas elementos na janela de Opções.
+ Adicionada opção de pintar os itens da árvore pelo `nameColor` do `config.json` e ferramenta de colorir hierarquia com a nova paleta.
+ Adicionado rótulo de toolbar "-by Sushi_nucelar" com atalho para o GitHub.
+ Adicionada prévia no mover textura que sobrepõe UV atual e deslocado no `skin.png`.
+ Adicionada ferramenta de renomear com prefixo/sufixo, removendo sufixos numéricos e podendo recursar em filhos.
+ Adicionada aba Animações para carregar JSONs da pasta `animations/`, interpretar nomes e listar Projeto 1/2 separadamente.
+ Adicionado copiar/colar animações entre projetos com mapeamento por StoreID, interface mostrando nomes, combos compactos e mapeamentos em colunas.
+ Adicionada ferramenta de aplicar frame que soma transformações ao modelo e subtrai deslocamentos de todos os frames da animação origem.
+ Adicionada interpolação de frames para gerar quadros intermediários com blend de posição/rotação, salvando na mesma ou em nova animação.
+ Adicionado multiplicador "skin x128" e refinado o tratamento da face Down (mantida para Anti_ braços/pernas, removida para calças).

