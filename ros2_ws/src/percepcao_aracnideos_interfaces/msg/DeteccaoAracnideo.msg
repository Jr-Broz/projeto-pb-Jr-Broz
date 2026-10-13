# Uma deteccao de aracnideo num frame.
# Campos de caixa em pixels, canto superior esquerdo (x, y) + largura e altura.

string  classe            # rotulo predito: viuva-negra, teia-dourada, ...
float32 confianca         # 0.0 a 1.0
int32   x                 # canto superior esquerdo da bbox
int32   y
int32   w                 # largura da bbox
int32   h                 # altura da bbox

int32   id_rastreio       # id estavel atribuido pelo rastreador (-1 se nao rastreado)
int32   cx_suavizado      # centroide apos o filtro de Kalman
int32   cy_suavizado
float32 velocidade_px_s   # modulo da velocidade estimada pelo filtro
