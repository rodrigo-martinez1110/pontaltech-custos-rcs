import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(page_title="Relatório de Custos", layout="wide")
st.title("Relatório de Custos por Equipe")

# --------------------------------------------------
# Funções auxiliares
# --------------------------------------------------

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto

def identificar_equipe(nome_campanha):
    texto = normalizar_texto(nome_campanha)

    if any(p in texto for p in ["iniciativaprivada", "iniciativa privada", "clt"]):
        return "CLT"
    if any(p in texto for p in ["outbound", "aquisicao", "aquisição"]):
        return "OUTBOUND"
    if any(p in texto for p in ["ativacao", "csativacao", "ativação"]):
        return "ATIVACAO"
    if any(p in texto for p in ["csapp", "app", "aplicativo"]):
        return "CSAPP"
    if any(p in texto for p in ["cp", "inss", "cscp"]):
        return "CP"

    return "OUTROS"

def custo_por_canal(canal):
    canal = str(canal).lower()
    if canal == "sms":
        return 0.047
    if canal == "rcs":
        return 0.105
    return 0.0

# --------------------------------------------------
# Upload do CSV
# --------------------------------------------------

arquivo = st.file_uploader("Faça upload do arquivo CSV", type=["csv"])

if arquivo:
    # Detecta separador automaticamente (, ou ;)
    df = pd.read_csv(arquivo, sep=None, engine="python")

    st.subheader("Prévia do arquivo")
    st.dataframe(df.head())

    # --------------------------------------------------
    # Filtrar STATUS
    # --------------------------------------------------
    df["STATUS"] = df["STATUS"].str.upper()
    df = df[df["STATUS"].isin(["LIDO", "ENTREGUE", "ENVIADO"])]

    # --------------------------------------------------
    # Criar EQUIPE
    # --------------------------------------------------
    df["EQUIPE"] = df["NOME CAMPANHA"].apply(identificar_equipe)

    # --------------------------------------------------
    # Criar CUSTO
    # --------------------------------------------------
    df["CANAL"] = df["CANAL"].str.lower()
    df["CUSTO"] = df["CANAL"].apply(custo_por_canal)

    # --------------------------------------------------
    # Agregação base
    # --------------------------------------------------
    base = (
        df.groupby(["EQUIPE", "CANAL"], as_index=False)
          .agg(
              QUANTIDADE=("CUSTO", "count"),
              CUSTO=("CUSTO", "sum")
          )
    )

    # --------------------------------------------------
    # Pivot para formato final
    # --------------------------------------------------
    tabela = base.pivot(index="EQUIPE", columns="CANAL")

    tabela.columns = [
        f"{canal.upper()} {metrica}"
        for metrica, canal in tabela.columns
    ]

    tabela = tabela.fillna(0).reset_index()

    # --------------------------------------------------
    # Garantir colunas
    # --------------------------------------------------
    for col in [
        "RCS QUANTIDADE", "RCS CUSTO",
        "SMS QUANTIDADE", "SMS CUSTO"
    ]:
        if col not in tabela.columns:
            tabela[col] = 0

    # --------------------------------------------------
    # Totais
    # --------------------------------------------------
    tabela["Quantidade Total"] = (
        tabela["RCS QUANTIDADE"] + tabela["SMS QUANTIDADE"]
    )

    tabela["Custo Total"] = (
        tabela["RCS CUSTO"] + tabela["SMS CUSTO"]
    )

    # --------------------------------------------------
    # Arredondar custos (CORREÇÃO)
    # --------------------------------------------------
    colunas_custo = ["RCS CUSTO", "SMS CUSTO", "Custo Total"]
    for col in colunas_custo:
        tabela[col] = tabela[col].round(2)

    # --------------------------------------------------
    # Ordenar colunas
    # --------------------------------------------------
    tabela = tabela[
        [
            "EQUIPE",
            "RCS QUANTIDADE", "RCS CUSTO",
            "SMS QUANTIDADE", "SMS CUSTO",
            "Quantidade Total", "Custo Total"
        ]
    ]

    st.subheader("Relatório Final")
    st.dataframe(tabela)

    # --------------------------------------------------
    # Download CSV pt-BR (CORREÇÃO)
    # --------------------------------------------------
    csv_download = tabela.to_csv(
        index=False,
        sep=";",
        decimal=","
    ).encode("utf-8")

    st.download_button(
        "📥 Baixar relatório",
        csv_download,
        file_name="relatorio_final_por_equipe.csv",
        mime="text/csv"
    )
