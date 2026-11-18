# Remove Matrículas

Ferramenta tipo remove.bg, mas para **matrículas de aeronaves** (ex.: `PT-ABC`, `PP-XYZ`, `G-ABCD`, `N123AB`).
Você envia uma foto de avião; ela encontra o texto da matrícula, apaga e devolve a imagem preenchida no lugar.
Tudo roda localmente na sua máquina — nenhuma imagem é enviada para fora.

## Como funciona

1. **OCR** (RapidOCR, modelos ONNX, sem GPU) lê todos os textos da imagem.
2. **Filtro por padrão**: `remover/patterns.py` decide quais textos têm cara de matrícula (Brasil, Europa, EUA etc.).
3. **Máscara**: a área de cada matrícula é marcada e expandida um pouco, para cobrir sombras e bordas.
4. **Preenchimento**: a área é reconstruída a partir do fundo ao redor.
   - `lama` (recomendado): modelo LaMa via PyTorch — resultado bem mais natural em fuselagem e cauda.
   - `opencv`: algoritmo Telea — leve e sem download, mas borra em áreas grandes.
5. Só os pixels da máscara são trocados; o resto da foto fica idêntico.

## Instalação

Requer Python 3.10–3.12.

```bash
cd "/Users/fabiosiqueira/Documents/Claude/Remove MT"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para o motor LaMa (qualidade alta, instala PyTorch e baixa ~200 MB de pesos na 1ª vez):

```bash
pip install -r requirements-lama.txt
```

## Uso: interface web

```bash
uvicorn app:app --reload
```

Abra http://127.0.0.1:8000, escolha a foto e clique em **Remover matrícula**.

Para forçar um motor: `REMOVER_ENGINE=opencv uvicorn app:app` (ou `lama`).

### API

- `POST /api/remove` — `multipart/form-data` com `file` (imagem) e, opcionalmente, `boxes` (regiões extras em JSON, ex.: `[[100,200,380,260]]`). Responde a imagem PNG; o cabeçalho `X-Regions-Removed` diz quantas regiões foram apagadas.
- `POST /api/detect` — só lista as matrículas encontradas (texto e caixa), sem alterar a imagem.

```bash
curl -F "file=@foto.jpg" http://127.0.0.1:8000/api/remove -o foto_sem_matricula.png
```

## Uso: linha de comando

```bash
python -m remover.cli foto.jpg                       # gera saida/foto_sem_matricula.png
python -m remover.cli fotos/*.jpg -o resultado/      # várias imagens
python -m remover.cli foto.jpg --apenas-detectar     # só lista o que encontrou
python -m remover.cli foto.jpg --box 100,200,380,260 # apaga também uma região manual
python -m remover.cli foto.jpg --engine opencv       # motor sem PyTorch
```

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes cobrem só os padrões de matrícula (não precisam de OCR).

## Limitações

- **OCR precisa enxergar o texto.** Matrículas muito pequenas, borradas, em ângulo forte ou com pouco contraste podem passar despercebidas. Nesse caso use `--box` (CLI) ou o parâmetro `boxes` (API) com as coordenadas da região.
- **Falsos positivos são possíveis**: qualquer texto que siga o padrão (ex.: `XL-XXL`) será apagado. Confira o resultado; use `--apenas-detectar` para ver o que foi pego.
- **Formatos fora da lista** não são detectados automaticamente. Ajuste `DASHED_PATTERN` / `US_PATTERN` em `remover/patterns.py`.
- Matrículas em outros lugares (ex.: pintadas sobre a asa em perspectiva forte) podem ficar com um pouco de textura borrada após o preenchimento, sobretudo com o motor `opencv`.

## Estrutura

```
app.py                 interface web (FastAPI) + API
static/index.html      página de upload
remover/
  patterns.py          padrões de matrícula
  ocr.py               leitura de texto e agrupamento de pedaços
  mask.py              regiões e máscara
  inpaint.py           motores de preenchimento (LaMa / OpenCV)
  pipeline.py          fluxo completo
  cli.py               linha de comando
tests/test_patterns.py testes dos padrões
requirements.txt       dependências do núcleo
requirements-lama.txt  dependência opcional (LaMa)
```
