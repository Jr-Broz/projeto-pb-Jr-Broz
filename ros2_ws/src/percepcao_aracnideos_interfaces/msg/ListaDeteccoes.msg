# Todas as deteccoes de um unico frame, com o carimbo de tempo do frame.

std_msgs/Header               header
DeteccaoAracnideo[]           deteccoes
int32                         total
float32                       limiar_confianca_usado
string                        modelo                # ex.: yolov8n.onnx ou hsv-fallback
float32                       tempo_inferencia_ms

# ---- instrumentacao de robustez ----
# Um sistema que SABE que nao esta enxergando bem vale mais que um que
# devolve silencio. Estes campos deixam a condicao da imagem auditavel
# por qualquer no a jusante, sem precisar olhar a imagem.
float32                       qualidade_score       # 0.0 (ruim) a 1.0 (limpa)
float32                       brilho_medio          # 0-255, canal L
float32                       contraste             # desvio padrao de L
float32                       nitidez               # variancia do Laplaciano
string                        problemas_imagem      # "subexposta,desfocada" ou ""
string                        preproc_aplicado      # etapas aplicadas, ou ""
int32                         resgatadas_histerese  # deteccoes fracas aceitas
int32                         rejeitadas_histerese  # deteccoes fracas descartadas
