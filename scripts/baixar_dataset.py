#!/usr/bin/env python3
"""
Baixador de dataset para o projeto ARACNE.

Coleta fotos de observacoes do iNaturalist com licenca aberta,
organiza em pastas por classe e gera um CSV de atribuicao.

Uso:
    python3 baixar_dataset.py                    # baixa tudo (padrao: 150 por classe)
    python3 baixar_dataset.py --por-classe 300   # mais imagens
    python3 baixar_dataset.py --classe viuva-negra
    python3 baixar_dataset.py --listar

Requer: pip install requests
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Falta a biblioteca requests. Rode:  pip install requests")

API = "https://api.inaturalist.org/v1"
UA = "ARACNE-dataset-academico/1.0 (projeto de graduacao)"

# Pausa entre requisicoes. O iNaturalist limita a 100 req/min e recomenda
# ficar em 60 ou menos. 1.2s deixa a gente em ~50 req/min, bem dentro.
PAUSA_API = 1.2
PAUSA_FOTO = 0.4

# Licencas que permitem uso academico. Fotos sem licenca (todos os direitos
# reservados) ficam de fora de proposito.
LICENCAS = ["cc0", "cc-by", "cc-by-nc", "cc-by-sa", "cc-by-nc-sa"]

CLASSES = {
    "viuva-negra": {
        "taxon": "Latrodectus curacaviensis",
        "rank": "species",
    },
    "teia-dourada": {
        "taxon": "Trichonephila clavipes",
        "rank": "species",
    },
    "aranha-de-grama": {
        "taxon": "Lycosa erythrognatha",
        "rank": "species",
    },
    "caranguejeira": {
        "taxon": "Avicularia avicularia",
        "rank": "species",
    },
    # Classe negativa: outros artropodes que NAO sao as quatro especies.
    # Ensina o modelo a dizer "nao sei" em vez de chutar.
    "negativo": {
        "taxon": "Coleoptera",
        "rank": "order",
    },
}


def get(url, params=None):
    for tentativa in range(3):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 429:
                print("    limite de taxa atingido, esperando 60s...")
                time.sleep(60)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if tentativa == 2:
                print(f"    falhou: {e}")
                return None
            time.sleep(3 * (tentativa + 1))
    return None


def resolver_taxon(nome, rank):
    """Descobre o ID numerico do taxon a partir do nome cientifico."""
    dados = get(f"{API}/taxa", {"q": nome, "rank": rank, "per_page": 5})
    time.sleep(PAUSA_API)
    if not dados or not dados.get("results"):
        return None
    for r in dados["results"]:
        if r.get("name", "").lower() == nome.lower():
            return r["id"]
    return dados["results"][0]["id"]


def buscar_fotos(taxon_id, alvo):
    """Pagina as observacoes e junta as URLs das fotos."""
    fotos = []
    pagina = 1
    vistas = set()

    while len(fotos) < alvo and pagina <= 25:
        dados = get(f"{API}/observations", {
            "taxon_id": taxon_id,
            "quality_grade": "research",
            "photo_license": ",".join(LICENCAS),
            "photos": "true",
            "per_page": 200,
            "page": pagina,
            "order_by": "votes",
        })
        time.sleep(PAUSA_API)

        if not dados or not dados.get("results"):
            break

        for obs in dados["results"]:
            # Uma foto por observacao. Varias fotos do mesmo bicho, no mesmo
            # lugar e na mesma luz sao quase duplicatas e enviesam o treino.
            for foto in obs.get("photos", [])[:1]:
                url = foto.get("url")
                if not url or not foto.get("license_code"):
                    continue
                if "inaturalist-open-data" not in url:
                    continue
                url = url.replace("/square.", "/medium.")
                if url in vistas:
                    continue
                vistas.add(url)
                fotos.append({
                    "url": url,
                    "obs_id": obs["id"],
                    "obs_url": f"https://www.inaturalist.org/observations/{obs['id']}",
                    "licenca": foto["license_code"],
                    "autor": (foto.get("attribution") or "").replace(",", ";")[:120],
                    "taxon": obs.get("taxon", {}).get("name", ""),
                })
                if len(fotos) >= alvo:
                    break
            if len(fotos) >= alvo:
                break

        if len(dados["results"]) < 200:
            break
        pagina += 1

    return fotos


def baixar(fotos, destino, nome_classe):
    destino.mkdir(parents=True, exist_ok=True)
    linhas = []
    ok = 0

    for i, f in enumerate(fotos, 1):
        ext = os.path.splitext(f["url"].split("?")[0])[1] or ".jpg"
        arquivo = destino / f"{nome_classe}_{i:04d}{ext}"

        if arquivo.exists():
            ok += 1
            linhas.append({**f, "arquivo": arquivo.name})
            continue

        try:
            r = requests.get(f["url"], headers={"User-Agent": UA}, timeout=30)
            r.raise_for_status()
            if len(r.content) < 4000:
                continue
            arquivo.write_bytes(r.content)
            ok += 1
            linhas.append({**f, "arquivo": arquivo.name})
        except requests.RequestException:
            pass

        time.sleep(PAUSA_FOTO)
        if i % 25 == 0:
            print(f"    {i}/{len(fotos)}")

    return ok, linhas


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--por-classe", type=int, default=150)
    p.add_argument("--classe", help="baixa so uma classe")
    p.add_argument("--saida", default="dataset")
    p.add_argument("--listar", action="store_true")
    args = p.parse_args()

    if args.listar:
        for k, v in CLASSES.items():
            print(f"  {k:18s} -> {v['taxon']}")
        return

    alvos = {args.classe: CLASSES[args.classe]} if args.classe else CLASSES
    if args.classe and args.classe not in CLASSES:
        sys.exit(f"Classe desconhecida: {args.classe}. Use --listar.")

    raiz = Path(args.saida)
    raiz.mkdir(exist_ok=True)
    todas_linhas = []
    resumo = {}

    for nome, cfg in alvos.items():
        print(f"\n[{nome}] {cfg['taxon']}")

        tid = resolver_taxon(cfg["taxon"], cfg["rank"])
        if not tid:
            print("    taxon nao encontrado, pulando")
            continue
        print(f"    taxon id {tid}")

        fotos = buscar_fotos(tid, args.por_classe)
        print(f"    {len(fotos)} fotos com licenca aberta")
        if not fotos:
            continue

        ok, linhas = baixar(fotos, raiz / nome, nome)
        for l in linhas:
            l["classe"] = nome
        todas_linhas.extend(linhas)
        resumo[nome] = ok
        print(f"    {ok} salvas em {raiz / nome}")

    if todas_linhas:
        csv_path = raiz / "atribuicao.csv"
        modo = "a" if csv_path.exists() and args.classe else "w"
        with open(csv_path, modo, newline="", encoding="utf-8") as fh:
            campos = ["classe", "arquivo", "taxon", "licenca", "autor", "obs_id", "obs_url", "url"]
            w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
            if modo == "w":
                w.writeheader()
            w.writerows(todas_linhas)
        print(f"\nAtribuicao gravada em {csv_path}")

    print("\nResumo:")
    for k, v in resumo.items():
        print(f"  {k:18s} {v:4d} imagens")
    total = sum(resumo.values())
    print(f"  {'TOTAL':18s} {total:4d}")

    if total and min(resumo.values()) < max(resumo.values()) * 0.6:
        print("\nAviso: as classes estao desbalanceadas. Use class_weight")
        print("no treino ou reduza as classes maiores.")


if __name__ == "__main__":
    main()
